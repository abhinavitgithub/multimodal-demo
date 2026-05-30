"""
benchmark_models.py
───────────────────
Production-grade streaming benchmark for NVIDIA NIM / OpenAI-compatible APIs.

Scenarios:
  • SILO     — Short In  → Long Out
  • LISO     — Long In   → Short Out
  • BALANCED — Medium In → Medium Out

Metrics per run:
  • TTFB  — Time To First Byte   (request send → HTTP 200 header)
  • TTFT  — Time To First Token  (request send → first non-empty content chunk)
  • TPS   — Output Tokens / (E2E - TTFT)  ← decode-phase speed only
  • E2E   — End-to-End latency   (request send → [DONE])
  • Tokens — API-reported or estimated output token count

Methodology: Single-request / Load-Isolated (one in-flight request at a time).

Anomaly handling:
  • Runs with zero output tokens are detected and retried automatically.
  • Runs where TPS=0 (non-positive decode time) are detected and retried.
  • After all retries, invalid runs are filtered before statistics.
  • CV (coeff. of variation) > INSTABILITY_CV_THRESHOLD triggers a warning.
  • Mean ± StdDev reported for TTFT and TPS alongside percentiles.

Usage:
    pip install requests tabulate tenacity tiktoken
    python benchmark_models.py
"""

from __future__ import annotations

import json
import math
import statistics
import time
import traceback
from dataclasses import dataclass, asdict, field
from typing import Optional

import requests
from tabulate import tabulate
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError

# ──────────────────────────────────────────────────────────────────────────────
# TOKEN COUNTER  (best available)
# ──────────────────────────────────────────────────────────────────────────────

try:
    import tiktoken
    _enc = tiktoken.get_encoding("cl100k_base")

    def count_tokens(text: str) -> int:
        return len(_enc.encode(text))

    TOKEN_COUNTER = "tiktoken/cl100k_base"

except ImportError:
    import re

    def count_tokens(text: str) -> int:  # type: ignore[misc]
        return len(re.findall(r"\w+|[^\w\s]", text))

    TOKEN_COUNTER = "regex-fallback"


# ──────────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────────

NVIDIA_API_KEY  = "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"
NVIDIA_API_URL  = "https://integrate.api.nvidia.com/v1/chat/completions"

MODELS_TO_TEST: list[str] = [
    "nvidia/nemotron-mini-4b-instruct",
    "nvidia/llama-3.3-nemotron-super-49b-v1",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    "qwen/qwen3-next-80b-a3b-instruct",
    "qwen/qwen3.5-122b-a10b",
]

# ── Scenario definitions ──────────────────────────────────────────────────────

_LISO_BASE = (
    "Artificial intelligence (AI) refers to the simulation of human intelligence "
    "in machines that are programmed to think and learn. Machine learning, a subset "
    "of AI, enables systems to automatically learn and improve from experience without "
    "being explicitly programmed. Deep learning uses neural networks with many layers "
    "to analyse various factors of data. Natural language processing allows computers "
    "to understand, interpret and generate human language. Computer vision enables "
    "machines to derive meaningful information from images and videos. Robotics combines "
    "AI with mechanical engineering to create autonomous systems. Reinforcement learning "
    "trains agents to make sequences of decisions by rewarding desired behaviours. "
    "Transfer learning allows knowledge gained in one domain to be applied to another. "
    "AI is already transforming industries such as healthcare, finance, transportation, "
    "education and entertainment. Ethical considerations around bias, privacy and "
    "accountability remain active areas of research and policy debate. "
)

_LISO_REPEATS  = 7
_LISO_LONG_TEXT = (_LISO_BASE.strip() + " ") * _LISO_REPEATS

SCENARIOS: dict[str, dict] = {
    "SILO": {
        "prompt": (
            "Explain artificial intelligence in around 700 words with examples, "
            "future scope and applications."
        ),
        "max_tokens": 900,
    },
    "LISO": {
        "prompt": (
            f"{_LISO_LONG_TEXT.strip()}\n\n"
            "Summarize the above into 3 bullet points."
        ),
        "max_tokens": 120,
    },
    "BALANCED": {
        "prompt": (
            "Explain multimodal AI with examples and future scope in around 200 words."
        ),
        "max_tokens": 280,
    },
}

N_SAMPLES            = 3      # valid runs collected per (model × scenario)
MAX_ATTEMPTS_PER_RUN = 6      # hard cap on single-run retries (incl. anomalies)
TEMPERATURE          = 0.2
CONNECT_TIMEOUT      = 15     # seconds
READ_TIMEOUT         = 180    # seconds — generous for large models / long outputs
OUTPUT_JSON          = "results.json"

# Anomaly / instability thresholds
MIN_OUTPUT_TOKENS          = 5     # fewer tokens → treat as empty/failed output
MIN_TPS                    = 0.5   # tok/s — below this TPS is suspiciously low
INSTABILITY_CV_THRESHOLD   = 0.40  # CV > 40 % triggers a ⚠ warning


# ──────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class RunResult:
    model:         str
    scenario:      str
    ttfb:          float
    ttft:          float
    e2e:           float
    tps:           float
    output_tokens: int
    token_source:  str
    error:         Optional[str]  = None
    anomaly:       Optional[str]  = None   # populated when run is flagged


@dataclass
class ScenarioSummary:
    model:        str
    scenario:     str
    n:            int            # valid runs used for stats
    ttft_mean:    float
    ttft_std:     float
    ttft_p50:     float
    ttft_p95:     float
    tps_mean:     float
    tps_std:      float
    tps_p50:      float
    e2e_mean:     float
    tokens_mean:  float
    failures:     int            # hard errors
    anomalies:    int            # discarded anomalous runs
    warnings:     list[str] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    s  = sorted(data)
    k  = (len(s) - 1) * p / 100
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def _safe_stdev(data: list[float]) -> float:
    """Population std-dev; returns 0.0 for single-element lists."""
    if len(data) < 2:
        return 0.0
    return statistics.stdev(data)


def _cv(data: list[float]) -> float:
    """Coefficient of variation (σ/μ).  Returns 0 when mean ≈ 0."""
    if not data:
        return 0.0
    mu = statistics.mean(data)
    if mu < 1e-9:
        return 0.0
    return _safe_stdev(data) / mu


def _is_anomalous(result: RunResult) -> Optional[str]:
    """
    Return a short anomaly description if the run should be discarded,
    or None if it looks valid.
    """
    if result.error:
        return f"error: {result.error[:60]}"
    if result.output_tokens < MIN_OUTPUT_TOKENS:
        return f"empty_output: tokens={result.output_tokens}"
    if result.tps < MIN_TPS and result.output_tokens >= MIN_OUTPUT_TOKENS:
        # TPS=0 or near-zero despite real output → decode timing broken
        return f"zero_tps: tps={result.tps}, tokens={result.output_tokens}"
    return None


# ──────────────────────────────────────────────────────────────────────────────
# SINGLE-RUN BENCHMARK (inner — one HTTP request, no retry here)
# ──────────────────────────────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _http_run(model: str, scenario: str) -> RunResult:
    """
    Executes exactly one streaming request and returns a RunResult.
    Tenacity retries on *transport* failures (connection errors, HTTP 5xx).
    Anomaly detection (token=0, TPS=0) happens in the caller.
    """
    cfg        = SCENARIOS[scenario]
    prompt     = cfg["prompt"]
    max_tokens = cfg["max_tokens"]

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type":  "application/json",
        "Accept":        "text/event-stream",
    }
    payload = {
        "model":       model,
        "messages":    [{"role": "user", "content": prompt}],
        "stream":      True,
        "max_tokens":  max_tokens,
        "temperature": TEMPERATURE,
        "stream_options": {"include_usage": True},
    }

    t_send                        = time.perf_counter()
    t_first_byte: Optional[float] = None
    t_first_token: Optional[float] = None
    t_end:  Optional[float]       = None

    full_text                      = ""
    api_completion_tokens: Optional[int] = None
    token_source                   = TOKEN_COUNTER

    response = requests.post(
        NVIDIA_API_URL,
        headers=headers,
        json=payload,
        stream=True,
        timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
    )
    t_first_byte = time.perf_counter()

    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")

    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line:
            continue
        if not raw_line.startswith("data: "):
            continue

        data_str = raw_line[6:].strip()

        if data_str == "[DONE]":
            t_end = time.perf_counter()
            break

        try:
            chunk = json.loads(data_str)
        except json.JSONDecodeError:
            continue

        # Harvest usage block (may arrive mid-stream or on final chunk)
        usage = chunk.get("usage")
        if usage and isinstance(usage, dict):
            ct = usage.get("completion_tokens")
            if isinstance(ct, int) and ct > 0:
                api_completion_tokens = ct
                token_source          = "api_usage"

        try:
            choices = chunk.get("choices") or []
            if not choices:
                continue
            delta   = choices[0].get("delta") or {}
            content = delta.get("content") or ""
        except (KeyError, IndexError):
            continue

        if not content or not isinstance(content, str):
            continue

        now = time.perf_counter()
        if t_first_token is None:
            t_first_token = now
        full_text += content

    t_end = t_end or time.perf_counter()

    # ── Timing ────────────────────────────────────────────────────────────────
    ttfb        = (t_first_byte  - t_send) if t_first_byte  else 0.0
    ttft        = (t_first_token - t_send) if t_first_token else (t_end - t_send)
    e2e         = t_end - t_send
    decode_time = e2e - ttft

    # ── Token count ───────────────────────────────────────────────────────────
    # Prefer the API's reported count; fall back to local estimator.
    # If the API gave us 0 (a known qwen bug) but we received text,
    # use the local estimator so TPS isn't silently zeroed.
    local_count = count_tokens(full_text) if full_text else 0

    if api_completion_tokens and api_completion_tokens > 0:
        output_tokens = api_completion_tokens
    elif local_count > 0:
        output_tokens = local_count
        token_source  = f"{TOKEN_COUNTER}(api_reported_zero)"
    else:
        output_tokens = 0

    tps = output_tokens / decode_time if decode_time > 0.001 else 0.0

    return RunResult(
        model=model,
        scenario=scenario,
        ttfb=round(ttfb, 4),
        ttft=round(ttft, 4),
        e2e=round(e2e, 4),
        tps=round(tps, 2),
        output_tokens=output_tokens,
        token_source=token_source,
    )


# ──────────────────────────────────────────────────────────────────────────────
# OUTER LOOP — collects N_SAMPLES *valid* runs, retries anomalies
# ──────────────────────────────────────────────────────────────────────────────

def _collect_runs(model: str, scenario: str) -> list[RunResult]:
    """
    Keep attempting until we have N_SAMPLES anomaly-free runs OR we hit
    MAX_ATTEMPTS_PER_RUN total attempts.  Returns all attempts (valid + bad)
    so the caller can report counts accurately.
    """
    all_results: list[RunResult] = []
    valid_count = 0
    attempt     = 0

    while valid_count < N_SAMPLES and attempt < MAX_ATTEMPTS_PER_RUN:
        attempt += 1
        label = f"     run {attempt} (need {N_SAMPLES - valid_count} more valid)"
        try:
            result = _http_run(model, scenario)
        except RetryError as exc:
            err_msg = str(exc.last_attempt.exception())[:80]
            print(f"{label}  ❌  RetryError: {err_msg}")
            result = RunResult(
                model=model, scenario=scenario,
                ttfb=0, ttft=0, e2e=0, tps=0,
                output_tokens=0, token_source="n/a",
                error=err_msg,
            )
        except Exception as exc:
            err_msg = str(exc)[:80]
            print(f"{label}  ❌  {err_msg}")
            traceback.print_exc()
            result = RunResult(
                model=model, scenario=scenario,
                ttfb=0, ttft=0, e2e=0, tps=0,
                output_tokens=0, token_source="n/a",
                error=err_msg,
            )

        anomaly_desc = _is_anomalous(result)
        if anomaly_desc:
            result.anomaly = anomaly_desc
            print(
                f"{label}  ⚠  ANOMALY ({anomaly_desc}) — "
                f"TTFT={result.ttft:.3f}s  TPS={result.tps:.1f}  "
                f"tokens={result.output_tokens}  → discarding, will retry"
            )
        else:
            valid_count += 1
            print(
                f"{label}  ✅  TTFT={result.ttft:.3f}s  "
                f"TPS={result.tps:.1f}  E2E={result.e2e:.2f}s  "
                f"tokens={result.output_tokens}({result.token_source})"
            )

        all_results.append(result)

    if valid_count < N_SAMPLES:
        shortfall = N_SAMPLES - valid_count
        print(
            f"     ⚠  Reached attempt cap ({MAX_ATTEMPTS_PER_RUN}); "
            f"only {valid_count}/{N_SAMPLES} valid runs collected "
            f"({shortfall} missing)."
        )

    return all_results


# ──────────────────────────────────────────────────────────────────────────────
# SUMMARISE
# ──────────────────────────────────────────────────────────────────────────────

def _summarise(model: str, scenario: str, runs: list[RunResult]) -> ScenarioSummary:
    # Only use clean runs for statistics
    ok        = [r for r in runs if r.error is None and r.anomaly is None]
    anomalous = [r for r in runs if r.anomaly is not None]
    failed    = [r for r in runs if r.error   is not None]
    n         = len(ok)
    warnings: list[str] = []

    if n == 0:
        return ScenarioSummary(
            model=model, scenario=scenario, n=0,
            ttft_mean=0, ttft_std=0, ttft_p50=0, ttft_p95=0,
            tps_mean=0,  tps_std=0,  tps_p50=0,
            e2e_mean=0,  tokens_mean=0,
            failures=len(failed), anomalies=len(anomalous),
            warnings=["ALL_RUNS_INVALID"],
        )

    ttfts = [r.ttft for r in ok]
    tpss  = [r.tps  for r in ok]
    e2es  = [r.e2e  for r in ok]
    toks  = [r.output_tokens for r in ok]

    # ── Instability checks ────────────────────────────────────────────────────
    cv_ttft = _cv(ttfts)
    cv_tps  = _cv(tpss)
    if cv_ttft > INSTABILITY_CV_THRESHOLD:
        warnings.append(
            f"HIGH_TTFT_VARIANCE: CV={cv_ttft:.0%} "
            f"(min={min(ttfts):.3f}s max={max(ttfts):.3f}s)"
        )
    if cv_tps > INSTABILITY_CV_THRESHOLD:
        warnings.append(
            f"HIGH_TPS_VARIANCE: CV={cv_tps:.0%} "
            f"(min={min(tpss):.1f} max={max(tpss):.1f})"
        )
    if len(anomalous) > 0:
        reasons = list({r.anomaly for r in anomalous})
        warnings.append(
            f"ANOMALIES_DISCARDED: {len(anomalous)} run(s) — {'; '.join(reasons)}"
        )

    return ScenarioSummary(
        model=model,
        scenario=scenario,
        n=n,
        ttft_mean=round(statistics.mean(ttfts), 3),
        ttft_std=round(_safe_stdev(ttfts), 3),
        ttft_p50=round(_percentile(ttfts, 50), 3),
        ttft_p95=round(_percentile(ttfts, 95), 3),
        tps_mean=round(statistics.mean(tpss), 1),
        tps_std=round(_safe_stdev(tpss), 1),
        tps_p50=round(_percentile(tpss, 50), 1),
        e2e_mean=round(statistics.mean(e2es), 2),
        tokens_mean=round(statistics.mean(toks), 1),
        failures=len(failed),
        anomalies=len(anomalous),
        warnings=warnings,
    )


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    scenario_names = list(SCENARIOS.keys())

    print(f"\n{'═'*84}")
    print(f"  LLM STREAMING BENCHMARK")
    print(f"  Models       : {len(MODELS_TO_TEST)}")
    print(f"  Scenarios    : {', '.join(scenario_names)}")
    print(f"  Target runs  : {N_SAMPLES} valid per (model × scenario)")
    print(f"  Max attempts : {MAX_ATTEMPTS_PER_RUN} per (model × scenario)")
    print(f"  Token ctr    : {TOKEN_COUNTER}")
    print(f"  TPS def      : output_tokens / (E2E − TTFT)  [decode phase only]")
    print(f"  Anomaly rules: tokens < {MIN_OUTPUT_TOKENS} OR tps < {MIN_TPS}")
    print(f"  Instability  : CV > {INSTABILITY_CV_THRESHOLD:.0%} triggers warning")
    print(f"{'═'*84}\n")

    all_runs: dict[tuple[str, str], list[RunResult]] = {
        (m, sc): [] for m in MODELS_TO_TEST for sc in scenario_names
    }

    for model in MODELS_TO_TEST:
        print(f"▶  {model}")
        for scenario in scenario_names:
            print(f"   [{scenario}]")
            runs = _collect_runs(model, scenario)
            all_runs[(model, scenario)] = runs
        print()

    # ── Build summary objects ─────────────────────────────────────────────────
    summaries: list[ScenarioSummary] = []
    for model in MODELS_TO_TEST:
        for scenario in scenario_names:
            s = _summarise(model, scenario, all_runs[(model, scenario)])
            summaries.append(s)

    # ── Terminal table ────────────────────────────────────────────────────────
    rows = []
    for s in summaries:
        model_short = s.model.split("/")[-1]
        if s.n == 0:
            rows.append([model_short, s.scenario, "FAILED", "—", "—", "—", "—", "—"])
        else:
            notes = []
            if s.failures:  notes.append(f"❌{s.failures}err")
            if s.anomalies: notes.append(f"⚠{s.anomalies}anm")
            note_str = "  " + " ".join(notes) if notes else ""
            rows.append([
                model_short,
                s.scenario,
                f"{s.ttft_mean:.3f} ±{s.ttft_std:.3f}",
                f"{s.ttft_p50:.3f}",
                f"{s.tps_mean:.1f} ±{s.tps_std:.1f}",
                f"{s.tps_p50:.1f}",
                f"{s.e2e_mean:.2f}",
                f"{int(s.tokens_mean)}{note_str}",
            ])

    headers = [
        "Model", "Scenario",
        "TTFT mean±σ(s)", "TTFT p50",
        "TPS mean±σ", "TPS p50",
        "E2E(s)", "Tokens",
    ]

    print("\n" + "═" * 84)
    print("  RESULTS  (decode-only TPS, single-request / load-isolated)")
    print("═" * 84)
    print(tabulate(rows, headers=headers, tablefmt="grid"))
    print(f"\n  Token counter : {TOKEN_COUNTER}")
    print("  TPS = output_tokens / (E2E − TTFT)  [decode phase only]")

    # ── Warnings block ────────────────────────────────────────────────────────
    any_warnings = any(s.warnings for s in summaries)
    if any_warnings:
        print("\n" + "─" * 84)
        print("  ⚠  WARNINGS")
        print("─" * 84)
        for s in summaries:
            for w in s.warnings:
                model_short = s.model.split("/")[-1]
                print(f"  [{s.scenario}] {model_short}: {w}")
    print()

    # ── Per-scenario rankings ─────────────────────────────────────────────────
    for scenario in scenario_names:
        sc_sums = [s for s in summaries if s.scenario == scenario and s.n > 0]
        if not sc_sums:
            continue
        ranked = sorted(sc_sums, key=lambda s: s.tps_mean, reverse=True)
        print(f"  🏆  [{scenario}] Fastest by mean TPS:")
        for i, s in enumerate(ranked, 1):
            model_short = s.model.split("/")[-1]
            print(
                f"      {i}. {model_short:<45}  "
                f"{s.tps_mean:.1f} ±{s.tps_std:.1f} tok/s  "
                f"TTFT={s.ttft_mean:.3f} ±{s.ttft_std:.3f}s"
            )
        print()

    # ── Save JSON ─────────────────────────────────────────────────────────────
    output = {
        "config": {
            "models": MODELS_TO_TEST,
            "scenarios": {k: {"max_tokens": v["max_tokens"]} for k, v in SCENARIOS.items()},
            "n_samples_target": N_SAMPLES,
            "max_attempts_per_run": MAX_ATTEMPTS_PER_RUN,
            "temperature": TEMPERATURE,
            "token_counter": TOKEN_COUNTER,
            "anomaly_thresholds": {
                "min_output_tokens": MIN_OUTPUT_TOKENS,
                "min_tps": MIN_TPS,
                "instability_cv": INSTABILITY_CV_THRESHOLD,
            },
        },
        "summaries": [asdict(s) for s in summaries],
        "runs": {
            f"{m}::{sc}": [asdict(r) for r in runs]
            for (m, sc), runs in all_runs.items()
        },
    }
    with open(OUTPUT_JSON, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Full results saved → {OUTPUT_JSON}\n")


if __name__ == "__main__":
    main()
