# 2-minute demo video script

Record your screen in a terminal with a large font. Narrate, or add captions. No webcam is needed.

| time | show | say / caption |
|---|---|---|
| 0:00–0:12 | README title | "API Traffic Watch, AEGYTHON Challenge 03. It finds unusual synthetic API traffic and explains why, fully offline." |
| 0:12–0:25 | `type data\sample.csv` (scroll briefly) | "The input is synthetic request logs: timestamp, request ID, client, endpoint. This file also has a duplicate and two broken rows." |
| 0:25–0:55 | `python traffic_watch.py data\sample.csv` | "Requests are deduplicated and grouped into 1-minute windows. Each window gets a robust z-score based on the median and MAD. At 12:09 one window is flagged. The explanation says bot-1 sent 82% of requests, all to /login, and bot-1 never appears in normal traffic. That looks like a brute-force burst. The bad rows are skipped and reported by line number." |
| 0:55–1:15 | `python traffic_watch.py data\sample.csv --html report.html`, then open the file | "The same analysis as an offline dashboard: a chart with the spike in red, explanation cards and the window table." |
| 1:15–1:35 | `python -m unittest discover -s tests -t .` | "17 tests cover normal, edge and invalid input." |
| 1:35–1:55 | `python evaluate.py` | "Validation on 500 labeled synthetic series. The robust method gets F1 0.96 against 0.71 for a standard mean/stddev z-score, because spikes can't hide themselves by inflating the baseline." |
| 1:55–2:00 | README limitations section | "Limitations and setup are in the README. Thanks." |
