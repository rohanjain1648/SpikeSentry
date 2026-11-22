"""SpikeSentry (AEGYTHON 2026 - API Traffic Watch): offline window summarizer with dedup, spike detection,
spike explanations and an HTML dashboard. Synthetic data only; standard library only."""
from __future__ import annotations

import argparse
import csv
import html
import json
import math
import statistics
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone

REQUIRED = {"timestamp", "request_id", "client", "endpoint"}


@dataclass
class Result:
    windows: list            # one dict per window (see analyze)
    duplicates: int
    invalid: list            # [(line_no, reason)]
    total_rows: int
    warnings: list = field(default_factory=list)


# ---------------------------------------------------------------- parsing
def parse_ts(value: str) -> float:
    value = value.strip()
    if not value:
        raise ValueError("empty timestamp")
    try:
        ts = float(value)
    except ValueError:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    if not math.isfinite(ts) or ts < 0:
        raise ValueError(f"invalid epoch timestamp: {value!r}")
    return ts


def read_rows(lines):
    """Yield (line_no, record | None, error | None) from CSV text lines."""
    reader = csv.DictReader(lines)
    if not reader.fieldnames or not REQUIRED <= {f.strip() for f in reader.fieldnames}:
        raise ValueError(f"header must contain {sorted(REQUIRED)}")
    reader.fieldnames = [f.strip() for f in reader.fieldnames]
    for row in reader:
        n = reader.line_num
        try:
            ts = parse_ts(row["timestamp"] or "")
            rid = (row["request_id"] or "").strip()
            if not rid:
                raise ValueError("missing request_id")
            yield n, {"ts": ts, "id": rid,
                      "client": (row["client"] or "").strip() or "?",
                      "endpoint": (row["endpoint"] or "").strip() or "?"}, None
        except (ValueError, TypeError, OverflowError) as e:
            yield n, None, str(e)


# ---------------------------------------------------------------- detection
def robust_scores(counts):
    """Robust z-score: (x - median) / (1.4826 * MAD), scale floored at 1."""
    med = statistics.median(counts)
    mad = statistics.median([abs(c - med) for c in counts])
    scale = max(1.4826 * mad, 1.0)
    return [(c - med) / scale for c in counts]


def flag_counts(counts, threshold=3.5, min_count=10):
    scores = robust_scores(counts)
    return [c >= min_count and s >= threshold for c, s in zip(counts, scores)], scores


def explain(items, baseline, base_unique_median):
    """Explain why a spike window is unusual, compared with non-spike traffic."""
    n = len(items)
    reasons = []
    clients = Counter(r["client"] for r in items)
    top_c, top_cn = clients.most_common(1)[0]
    single = top_cn / n >= 0.5
    if single:
        reasons.append(f"single source: {top_c} sent {top_cn}/{n} requests ({top_cn / n:.0%})")

    eps = Counter(r["endpoint"] for r in items)
    top_e, top_en = eps.most_common(1)[0]
    base_share = (sum(r["endpoint"] == top_e for r in baseline) / len(baseline)) if baseline else 0.0
    share = top_en / n
    if share >= 0.5 and share - base_share >= 0.3:
        reasons.append(f"endpoint focus: {top_e} is {share:.0%} of window vs {base_share:.0%} in baseline")

    known = {r["client"] for r in baseline}
    new = sorted(c for c in clients if c not in known)
    if new:
        more = "..." if len(new) > 3 else ""
        reasons.append(f"new clients: {len(new)} not seen in normal windows ({', '.join(new[:3])}{more})")

    distributed = len(clients) >= 3 * max(base_unique_median, 1)
    if distributed:
        reasons.append(f"distributed: {len(clients)} unique clients vs normal median {base_unique_median:g}")

    if single:
        kind = "single-source burst (possible brute force / scraping)"
    elif distributed:
        kind = "distributed burst (DDoS-like pattern)"
    else:
        kind = "volume surge"
    if not reasons:
        reasons.append("request volume rose with a normal client/endpoint mix")
    return kind, reasons


def analyze(lines, window=60, threshold=3.5, min_count=10) -> Result:
    if window <= 0:
        raise ValueError("window must be > 0")
    if min_count < 0:
        raise ValueError("min-count must be >= 0")
    seen, recs, invalid, dups, total = set(), [], [], 0, 0
    for n, rec, err in read_rows(lines):
        total += 1
        if err:
            invalid.append((n, err))
        elif rec["id"] in seen:
            dups += 1
        else:
            seen.add(rec["id"])
            recs.append(rec)
    warnings = []
    if not recs:
        return Result([], dups, invalid, total, ["no valid requests"])

    t0 = math.floor(min(r["ts"] for r in recs) / window) * window   # aligned windows
    nwin = int((max(r["ts"] for r in recs) - t0) // window) + 1
    if nwin > 1_000_000:
        raise ValueError(f"{nwin} windows: time range too large for --window {window}")
    buckets = [[] for _ in range(nwin)]                               # includes empty gaps
    for r in recs:
        buckets[int((r["ts"] - t0) // window)].append(r)
    counts = [len(b) for b in buckets]
    flags, scores = flag_counts(counts, threshold, min_count)
    if nwin < 5:
        warnings.append(f"only {nwin} window(s): baseline is unreliable; use a smaller --window or more data")

    baseline = [r for b, f in zip(buckets, flags) if not f for r in b]
    base_unique = [len({r["client"] for r in b}) for b, f in zip(buckets, flags) if not f]
    bu_med = statistics.median(base_unique) if base_unique else 0

    windows = []
    for i, (b, c, s, f) in enumerate(zip(buckets, counts, scores, flags)):
        top = Counter(r["endpoint"] for r in b).most_common(1)
        w = {
            "start": datetime.fromtimestamp(t0 + i * window, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "count": c,
            "unique_clients": len({r["client"] for r in b}),
            "top_endpoint": top[0][0] if top else "-",
            "score": round(s, 2),
            "spike": f,
        }
        if f:
            kind, reasons = explain(b, baseline, bu_med)
            w.update(severity="high" if s >= 2 * threshold else "medium", kind=kind, reasons=reasons)
        windows.append(w)
    return Result(windows, dups, invalid, total, warnings)


# ---------------------------------------------------------------- output
def render(res: Result) -> str:
    out = [f"Rows read: {res.total_rows}  duplicates dropped: {res.duplicates}  invalid: {len(res.invalid)}",
           "", f"{'WINDOW START (UTC)':<22}{'REQS':>6}{'CLIENTS':>9}  {'TOP ENDPOINT':<18}{'SCORE':>7}  FLAG"]
    mx = max((w["count"] for w in res.windows), default=1) or 1
    for w in res.windows:
        bar = "#" * round(20 * w["count"] / mx)
        out.append(f"{w['start']:<22}{w['count']:>6}{w['unique_clients']:>9}  {w['top_endpoint'][:17]:<18}"
                   f"{w['score']:>7}  {'SPIKE' if w['spike'] else '':<5} {bar}")
    spikes = [w for w in res.windows if w["spike"]]
    out += ["", f"Spikes flagged: {len(spikes)}"]
    for w in spikes:
        out.append(f"  {w['start']} [{w['severity']}] {w['kind']}")
        out += [f"    - {r}" for r in w["reasons"]]
    for msg in res.warnings:
        out.append(f"warning: {msg}")
    for n, why in res.invalid:
        out.append(f"  skipped line {n}: {why}")
    return "\n".join(out)


CSS = """body{font-family:system-ui,Segoe UI,sans-serif;background:#0b1220;color:#dbe4f0;margin:2rem auto;max-width:900px;padding:0 1rem}
h1{font-size:1.5rem}h2{font-size:1.1rem;margin-top:2rem}.muted{color:#8a9bb4}
.cards{display:flex;gap:.8rem;flex-wrap:wrap}.stat{background:#141e33;border-radius:8px;padding:.8rem 1rem;min-width:120px}
.stat b{display:block;font-size:1.6rem}svg{background:#141e33;border-radius:8px;width:100%;height:auto}
table{border-collapse:collapse;width:100%;font-size:.9rem}td,th{padding:.35rem .5rem;border-bottom:1px solid #22304a;text-align:left}
tr.spike td{background:#3a1620}.spk{background:#1d1420;border-left:4px solid #e5484d;padding:.6rem 1rem;margin:.6rem 0;border-radius:4px}
.warn{color:#f5a524}"""


def render_html(res: Result, source: str = "input") -> str:
    e = html.escape
    ws = res.windows
    mx = max((w["count"] for w in ws), default=1) or 1
    W, H = 800, 220
    bw = W / max(len(ws), 1)
    bars = []
    for i, w in enumerate(ws):
        h = (H - 20) * w["count"] / mx
        color = "#e5484d" if w["spike"] else "#3e9bd6"
        bars.append(f'<rect x="{i * bw + 1:.1f}" y="{H - h:.1f}" width="{max(bw - 2, 1):.1f}" height="{h:.1f}" '
                    f'fill="{color}"><title>{e(w["start"])}: {w["count"]} requests, score {w["score"]}</title></rect>')
    spikes = [w for w in ws if w["spike"]]
    cards = "".join(
        f'<div class="spk"><b>{e(w["start"])}</b> &middot; {e(w["severity"])} &middot; {e(w["kind"])}'
        f'<ul>{"".join(f"<li>{e(r)}</li>" for r in w["reasons"])}</ul></div>' for w in spikes
    ) or '<p class="muted">No spikes flagged.</p>'
    rows = "".join(
        f'<tr class="{"spike" if w["spike"] else ""}"><td>{e(w["start"])}</td><td>{w["count"]}</td>'
        f'<td>{w["unique_clients"]}</td><td>{e(w["top_endpoint"])}</td><td>{w["score"]}</td>'
        f'<td>{"SPIKE" if w["spike"] else ""}</td></tr>' for w in ws)
    notes = "".join(f'<p class="warn">warning: {e(m)}</p>' for m in res.warnings)
    notes += "".join(f'<p class="muted">skipped line {n}: {e(why)}</p>' for n, why in res.invalid)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>SpikeSentry report</title><style>{CSS}</style></head><body>
<h1>SpikeSentry</h1><p class="muted">Source: {e(source)} &middot; synthetic data &middot; offline report</p>
<div class="cards"><div class="stat"><b>{res.total_rows}</b>rows read</div>
<div class="stat"><b>{len(ws)}</b>windows</div><div class="stat"><b>{res.duplicates}</b>duplicates dropped</div>
<div class="stat"><b>{len(res.invalid)}</b>invalid rows</div><div class="stat"><b>{len(spikes)}</b>spikes</div></div>
<h2>Requests per window</h2><svg viewBox="0 0 {W} {H}" role="img" aria-label="requests per window">{''.join(bars)}</svg>
<h2>Spike explanations</h2>{cards}{notes}
<h2>Windows</h2><table><tr><th>Start (UTC)</th><th>Requests</th><th>Clients</th><th>Top endpoint</th><th>Score</th><th>Flag</th></tr>{rows}</table>
</body></html>"""


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", help="CSV file (or - for stdin)")
    p.add_argument("--window", type=int, default=60, help="window seconds (default 60)")
    p.add_argument("--threshold", type=float, default=3.5, help="robust z-score cutoff (default 3.5)")
    p.add_argument("--min-count", type=int, default=10, help="min requests in a window to flag (default 10)")
    p.add_argument("--json", action="store_true", help="print JSON instead of the table")
    p.add_argument("--html", metavar="PATH", help="also write an HTML dashboard to PATH")
    a = p.parse_args(argv)
    try:
        f = sys.stdin if a.input == "-" else open(a.input, newline="", encoding="utf-8-sig")
        with f:
            res = analyze(f, a.window, a.threshold, a.min_count)
        if a.html:
            with open(a.html, "w", encoding="utf-8") as out:
                out.write(render_html(res, a.input))
    except (OSError, ValueError, UnicodeDecodeError, csv.Error) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps({"total_rows": res.total_rows, "duplicates": res.duplicates,
                          "invalid": res.invalid, "warnings": res.warnings,
                          "windows": res.windows}, indent=2))
    else:
        print(render(res))
    if a.html:
        print(f"dashboard written to {a.html}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
