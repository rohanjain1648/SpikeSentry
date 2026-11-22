# API Traffic Watch

**AEGYTHON 2026, Challenge 03 (API Traffic Watch, beginner-friendly)**
Team ID: `<TEAM-ID>` · Demo video (2 min or less): `<VIDEO-URL>` · Review tag: `v1.0-review`

API Traffic Watch is an offline Python tool. It finds unusual **synthetic** API request traffic and explains why each flagged window looks unusual. It never touches a real API, and it uses only the Python standard library.

```
CSV requests -> Traffic monitor -> Spike detection -> Explanation -> Dashboard
(synthetic)     (parse, dedup,     (robust z-score)   (who / what /    (terminal table,
                 time windows)                         new clients)      HTML report, JSON)
```

## Quick start (about 1 minute)
Requires Python 3.9 or newer. No installs, no network.
```
git clone <REPO-URL> && cd api-traffic-watch
python traffic_watch.py data/sample.csv                       # readable table + spike explanations
python traffic_watch.py data/sample.csv --html report.html    # offline HTML dashboard
python traffic_watch.py data/sample.csv --json                # machine-readable output
python -m unittest discover -s tests -t . -v                  # 17 normal/edge/invalid tests
python evaluate.py                                            # labeled-synthetic validation
python data/make_sample.py                                    # regenerate the sample (seeded)
```
Options: `--window SECONDS` (default 60), `--threshold Z` (default 3.5), `--min-count N` (default 10). Use `-` as the input to read from stdin.

## Input
A CSV file with the header `timestamp,request_id,client,endpoint`. Extra columns are ignored.
- `timestamp`: ISO-8601 (`2026-11-01T12:00:05Z`) or epoch seconds. Times without a timezone are treated as UTC.
- `request_id`: used for deduplication, so retries and replays are counted once.
- `client`, `endpoint`: free text. Blank values become `?`.

Invalid rows (bad, negative or NaN timestamps, missing `request_id`) are **skipped and reported with their line number**. They do not stop the run. A missing file, wrong header or bad option makes the tool exit with code 2 and print a clear `error:` message.

## Output
- A table of fixed, aligned time windows: requests, unique clients, top endpoint, robust score, `SPIKE` flag and a bar. Empty windows are included, so quiet gaps stay visible.
- For each spike: a **severity** (`high` when score ≥ 2× threshold), a **pattern type**, and the **reasons** it was flagged.
- Counts of dropped duplicates and skipped rows, plus a warning when there are too few windows for a reliable baseline.
- `--html`: a self-contained dashboard with a bar chart, explanation cards and the full table. It loads no external resources.

Example (from `data/sample.csv`):
```
Spikes flagged: 1
  2026-11-01T12:09:00Z [high] single-source burst (possible brute force / scraping)
    - single source: bot-1 sent 56/68 requests (82%)
    - endpoint focus: /login is 100% of window vs 0% in baseline
    - new clients: 1 not seen in normal windows (bot-1)
```

## Intelligent technique
1. **Robust anomaly scoring.** For each window, `score = (count - median) / max(1.4826 × MAD, 1)`, where MAD is the median absolute deviation. A window is flagged when `score ≥ threshold` **and** `count ≥ min-count`. The median and MAD are not pulled up by the spikes they are trying to find. The classic mean/stddev z-score suffers from this problem, called *masking*: a large spike inflates the stddev and hides itself and other spikes. The floor of 1 prevents division by zero on perfectly flat traffic. `min-count` stops near-empty windows from being flagged.
2. **Explanation by comparison with the baseline.** Each spike window is compared with all non-spike windows:
   - *single source*: one client sent at least 50% of the window's requests
   - *endpoint focus*: the top endpoint's share is at least 50% and at least 30 percentage points above its normal share
   - *new clients*: clients that never appear in normal windows
   - *distributed*: unique clients ≥ 3× the normal median

   These signals give a pattern type: single-source burst (brute force or scraping), distributed burst (DDoS-like) or volume surge.

This is a transparent statistical and rule-based technique, not a trained ML model. Every flag can be traced to numbers in the output.

## Test and validation evidence
- **Unit tests** (`tests/test_traffic_watch.py`, 17 tests):
  - *normal*: steady traffic, a single spike, explanation content, ISO timestamps, the HTML dashboard
  - *edge*: duplicates, header-only input, empty gap windows, flat traffic, below-min-count windows, the few-windows warning, HTML escaping
  - *invalid*: bad, negative or NaN timestamps, missing ID, bad header, bad window, missing file, the CLI JSON/HTML path
- **Synthetic validation** (`evaluate.py`): 500 seeded series × 30 windows with Poisson-like counts. 0 to 3 spikes of known size (2×, 3×, 4× or 6× the normal rate) are injected into each series.

| method | precision | recall | F1 | false positives per 1k normal windows |
|---|---|---|---|---|
| **robust (this tool)** | 0.971 | **0.954** | **0.962** | 1.62 |
| mean/stddev z ≥ 3 | 0.989 | 0.547 | 0.705 | 0.35 |

| spike size | robust recall | mean/stddev recall |
|---|---|---|
| 2× | 0.83 | 0.19 |
| 3× | 0.98 | 0.38 |
| 4× | 1.00 | 0.63 |
| 6× | 1.00 | 0.96 |

The robust method catches far more spikes, especially when a series has more than one spike, where masking hurts mean/stddev. The cost is a small rise in false positives.
- Saved evidence is in [`evidence/`](evidence/): the test run, the validation output, the sample output and the sample HTML dashboard.

## Data, model attribution and licensing
- All data is **synthetic**. `data/make_sample.py` generates it with a fixed seed. No real traffic, personal data or third-party datasets are used.
- No pretrained models and no third-party libraries. The MAD scale constant 1.4826 is the standard normal-consistency factor.
- Code license: MIT (see [`LICENSE`](LICENSE)).

## Known limitations
- Fixed (non-sliding) windows can split a burst across two windows and weaken its score. A smaller `--window` reduces this.
- The whole file forms one baseline. There is no seasonality, trend or per-endpoint baseline, so a spike on one endpoint can be hidden inside large total traffic.
- At least about 5 windows are needed for a meaningful baseline (the tool warns below this). If more than half of all windows are spikes, the median itself shifts.
- Deduplication uses `request_id` only. Identical requests with different IDs are counted separately.
- The whole input is held in memory. It is not a streaming or real-time monitor.
- Explanation thresholds (50%, 30 pp, 3×) are hand-set heuristics validated only on synthetic data.
- Synthetic evaluation shows behaviour under controlled assumptions (Poisson-like counts), not performance on real traffic.

## Project layout
```
traffic_watch.py            CLI entrypoint: parse, dedup, window, detect, explain, render
evaluate.py                 labeled synthetic validation (robust vs mean/stddev)
data/make_sample.py         seeded synthetic data generator
data/sample.csv             sample input (includes 1 duplicate and 2 invalid rows)
tests/test_traffic_watch.py unit tests
evidence/                   saved test, validation and sample outputs
DEMO_SCRIPT.md              2-minute demo video plan
```
