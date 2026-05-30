# Model Speed Benchmark Results

## 📊 Executive Summary

| Model | SILO TPS | LISO TPS | BALANCED TPS | Key Observation |
|---|---|---|---|---|
| nemotron-mini-4b-instruct | 101.6 | 56.4 | 76.8 | Solid all-rounder; LISO throughput is inconsistent |
| llama-3.3-nemotron-super-49b-v1 | 16.3 | 24.4 | 21.5 | Slowest throughput; startup time highly variable |
| nemotron-3-nano-omni-30b-a3b-reasoning | **317.5** | **872.2** | **335.8** | 🏆 Fastest across all scenarios by a wide margin |
| qwen3-next-80b-a3b-instruct | 30.6 | 40.1 | 31.0 | Mid-range speed; startup time unreliable |
| qwen3.5-122b-a10b | 16.8 | 31.6 | 26.9 | Most inconsistent; treat all figures as preliminary |

> **TPS = tokens per second during generation (higher is better). All figures are mean values.**

---

> **Methodology:** Single-request / load-isolated. TPS = `output_tokens ÷ (E2E − TTFT)` (decode phase only).
> **Samples:** 3 valid runs per cell (anomalous runs auto-discarded and retried).
> **Token counter:** tiktoken / cl100k\_base (falls back to API-reported count).
>
> **Scenarios:** SILO = Short In Long Out · LISO = Long In Short Out · BALANCED = medium prompt/output

---

## Results Table

| Model | Scenario | TTFT Mean ± Std (s) | TPS Mean ± Std | E2E Time (s) | Tokens | Stability Notes |
|---|---|---|---|---|---|---|
| nemotron-mini-4b-instruct | SILO | 0.730 ± 0.236 | 101.6 ± 1.1 | 7.22 | 659 | ✅ Stable |
| nemotron-mini-4b-instruct | LISO | 0.764 ± 0.153 | 56.4 ± 45.6 | 5.93 | 120 | ⚠ High TPS variance (CV 81%) |
| nemotron-mini-4b-instruct | BALANCED | 0.684 ± 0.079 | 76.8 ± 24.8 | 6.10 | 277 | ✅ Stable |
| llama-3.3-nemotron-super-49b-v1 | SILO | 0.957 ± 0.180 | 16.3 ± 3.0 | 56.10 | 884 | ✅ Stable |
| llama-3.3-nemotron-super-49b-v1 | LISO | 3.939 ± 4.881 | 24.4 ± 0.9 | 8.86 | 120 | ⚠ High TTFT variance |
| llama-3.3-nemotron-super-49b-v1 | BALANCED | 8.893 ± 13.592 | 21.5 ± 4.9 | 22.34 | 280 | ⚠ High TTFT variance |
| nemotron-3-nano-omni-30b-a3b-reasoning | SILO | 1.285 ± 0.272 | 317.5 ± 72.3 | 4.21 | 900 | ⚠ High TPS variance (CV 23%) |
| nemotron-3-nano-omni-30b-a3b-reasoning | LISO | 1.024 ± 0.032 | 872.2 ± 78.2 | 1.16 | 120 | ✅ Stable |
| nemotron-3-nano-omni-30b-a3b-reasoning | BALANCED | 0.993 ± 0.086 | 335.8 ± 69.8 | 1.85 | 280 | ⚠ High TPS variance (CV 21%) |
| qwen3-next-80b-a3b-instruct | SILO | 3.845 ± 4.951 | 30.6 ± 1.6 | 31.63 | 850 | ⚠ High TTFT variance |
| qwen3-next-80b-a3b-instruct | LISO | 3.380 ± 1.168 | 40.1 ± 11.8 | 6.54 | 120 | ✅ Stable |
| qwen3-next-80b-a3b-instruct | BALANCED | 6.062 ± 4.322 | 31.0 ± 10.7 | 15.27 | 257 | ⚠ High TTFT variance |
| qwen3.5-122b-a10b | SILO | 13.541 ± 9.215 | 16.8 ± 10.4 | 81.16 | 878 | ⚠ High TTFT & TPS variance |
| qwen3.5-122b-a10b | LISO | 7.649 ± 5.956 | 31.6 ± 53.0 | 94.24 | 120 | ⚠ High TTFT & TPS variance |
| qwen3.5-122b-a10b | BALANCED | 13.659 ± 1.236 | 26.9 ± 26.8 | 47.23 | 264 | ⚠ High TPS variance (CV 100%) |

---

## 🏆 Fastest Model by Scenario

| Scenario | Fastest Model | TPS Mean ± Std | TTFT Mean (s) |
|---|---|---|---|
| **SILO** | `nemotron-3-nano-omni-30b-a3b-reasoning` | 317.5 ± 72.3 tok/s | 1.285 s |
| **LISO** | `nemotron-3-nano-omni-30b-a3b-reasoning` | 872.2 ± 78.2 tok/s | 1.024 s |
| **BALANCED** | `nemotron-3-nano-omni-30b-a3b-reasoning` | 335.8 ± 69.8 tok/s | 0.993 s |

> **Omni note:** The Omni model leads across all three scenarios. TPS variance is elevated on SILO (CV 23%) and BALANCED (CV 21%), so treat those figures as approximate pending additional samples.

---

## ⚠ Instability & Anomaly Notes

### nemotron-mini-4b-instruct — LISO: High TPS Variance

TPS std of 45.6 against a mean of 56.4 gives a CV of ~81%, well above the 40% instability threshold.

- **Recommendation:** Increase `N_SAMPLES` to 5–7 for this model/scenario to obtain a reliable p95 estimate.

### llama-3.3-nemotron-super-49b-v1 — LISO & BALANCED: High TTFT Variance

TTFT std exceeds the mean in both scenarios (LISO: 4.881 s std vs. 3.939 s mean; BALANCED: 13.592 s std vs. 8.893 s mean), indicating significant server-side queueing or cold-start variability.

- **Recommendation:** Re-run during off-peak hours and increase `N_SAMPLES`; treat current TTFT figures as approximate.

### nemotron-3-nano-omni-30b-a3b-reasoning — High TPS Variance (SILO / BALANCED)

LISO and BALANCED TPS=0 anomalies from earlier runs are resolved; valid TPS is now recorded across all three scenarios. SILO (CV 23%) and BALANCED (CV 21%) remain below the 40% instability threshold, though the run-to-run variability in decode throughput is worth monitoring.

- **Recommendation:** Increase `N_SAMPLES` to 5–7 for SILO and BALANCED to tighten confidence intervals.

### qwen3-next-80b-a3b-instruct — High TTFT Variance (SILO / BALANCED)

TTFT std exceeds the mean on SILO (4.951 s std vs. 3.845 s mean), indicating significant server-side queueing or cold-start variability. BALANCED is similarly unstable (4.322 s std vs. 6.062 s mean).

- **Recommendation:** Re-run during off-peak hours and increase `N_SAMPLES`; treat current TTFT figures as approximate.

### qwen3.5-122b-a10b — High TTFT & TPS Variance (All Scenarios)

All three scenarios show extreme variability. TTFT std exceeds the mean on SILO (9.215 s vs. 13.541 s) and LISO (5.956 s vs. 7.649 s). TPS CV reaches ~62% on SILO, ~168% on LISO, and ~100% on BALANCED — all well above the 40% instability threshold. E2E times are also substantially higher than prior runs (SILO 81.16 s, LISO 94.24 s), suggesting severe server-side load or queueing pressure at time of measurement.

- **Recommendation:** Treat all qwen3.5-122b-a10b figures as preliminary. Re-run during off-peak hours with `N_SAMPLES` increased to 7–10.

---

## NVIDIA UI vs. API Comparison — Omni Model (SILO)

| Source | TPS Observed | Notes |
|---|---|---|
| NVIDIA UI — Run 1 | 129.98 tok/s | |
| NVIDIA UI — Run 2 | 142.72 tok/s | |
| NVIDIA UI — Run 3 | 213.97 tok/s | |
| NVIDIA UI — Run 4 | 299.27 tok/s | |
| **NVIDIA UI Range** | **129.98 – 299.27 tok/s** | High run-to-run variance |
| **API Benchmark (SILO)** | **317.5 ± 72.3 tok/s** | Decode-only TPS |

**Key observations:**

- API TPS (317.5) slightly exceeds the upper bound of the UI-observed range (~299). The difference is expected: the API benchmark measures only the token generation step, while the UI figure includes rendering overhead, session warm-up effects, and variable request queuing.
- UI run-to-run variance (129.98 → 299.27 tok/s, a 2.3× spread across 4 runs) underscores the need for repeated sampling and anomaly filtering.
- The API SILO TPS std of 72.3 (CV 23%) is similarly elevated, suggesting that server-side load variability affects both measurement paths.

---

## Benchmark Configuration

| Parameter | Value |
|---|---|
| Samples (target valid runs) | 3 per (model × scenario) |
| Max attempts per cell | 6 |
| Temperature | 0.2 |
| Min output tokens (anomaly floor) | 5 |
| Min TPS (anomaly floor) | 0.5 tok/s |
| Instability CV threshold | 40% |
| Token counter | tiktoken / cl100k_base |
| Connect timeout | 15 s |
| Read timeout | 180 s |
