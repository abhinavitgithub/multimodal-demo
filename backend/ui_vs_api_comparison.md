# NVIDIA UI vs API Benchmark Comparison

## Omni (nemotron-3-nano-omni-30b-a3b-reasoning)

### NVIDIA UI repeated observations

| Run | TPS | TTFT | Total Time |
|------|------|------|-------------|
| 1 | 299.27 | 33 ms | 27.43 s |
| 2 | 129.98 | 40 ms | 11.99 s |
| 3 | 142.72 | 43 ms | 11.15 s |
| 4 | 213.97 | 39 ms | 7.62 s |

**Observed UI variance**

- TPS varies significantly across executions (~130 → ~299 TPS)
- TTFT remains relatively stable (~33–43 ms)
- End-to-end time varies considerably between runs

### API benchmark comparison (SILO)

| Metric | NVIDIA UI (observed range) | API benchmark |
|--------|------------------------------|----------------|
| TPS | ~130–299 | ~317.5 |
| TTFT | ~33–43 ms | ~1.285 s |
| Total time | ~7–27 s | ~4.21 s |

### Observation

API benchmark throughput is in a broadly comparable range to NVIDIA UI throughput, but methodology differences remain.

Potential reasons:

- UI may report throughput differently (decode-only / post-warmup)
- reasoning mode behavior may vary across runs
- stream lifecycle and prompt handling differ between UI and API
- request overhead and token accounting differ

Repeated UI testing also shows runtime variance, reinforcing the need for repeated measurements, averaging, and anomaly filtering for reliable benchmarking.