# LLM Evaluation Benchmark Harness

## 1. Overview
The evaluation harness (`evals/run_evals.py`) measures the performance and accuracy of AI models when synthesizing Frappe applications from requirements.

## 2. Evaluation Metrics

1. **Spec Validity Rate (`spec_validity_rate_pct`)**:
   Percentage of synthesized specifications that pass all 20+ deterministic Frappe v15 schema rules without errors. Target: `100%`.
2. **Bench Pass Rate (`bench_pass_rate_pct`)**:
   Percentage of exported app packages that compile with `ast.parse`, load valid JSON fixtures, and pass bench execution. Target: `100%`.
3. **Healing Cycles**:
   Number of repair rounds required to resolve schema errors. Target: `<= 1`.
4. **LLM Cost & Latency**:
   Total token consumption and latency tracked per call.

## 3. Running Evaluations

```bash
make eval
# or
python3 evals/run_evals.py
```

Results are stored as timestamped JSON reports in `evals/results/eval_<timestamp>.json`.
