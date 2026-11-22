import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

from traffic_watch import analyze, flag_counts, main, render, render_html

H = "timestamp,request_id,client,endpoint\n"


def mk(counts, window=60, bot_window=None):
    """Synthetic CSV lines: counts[w] requests in window w (epoch seconds from 0)."""
    rows, i = [], 0
    for w, c in enumerate(counts):
        for k in range(c):
            i += 1
            client = "bot-9" if w == bot_window else f"c{k % 3}"
            ep = "/login" if w == bot_window else "/items"
            rows.append(f"{w * window + k % window},r{i},{client},{ep}")
    return (H + "\n".join(rows) + "\n").splitlines(True)


def lines(body):
    return (H + body).splitlines(True)


class Normal(unittest.TestCase):
    def test_steady_traffic_no_spike(self):
        r = analyze(mk([10, 11, 9, 10, 12, 10]))
        self.assertEqual(len(r.windows), 6)
        self.assertFalse(any(w["spike"] for w in r.windows))

    def test_spike_flagged_once(self):
        r = analyze(mk([10, 11, 9, 80, 10, 10]))
        self.assertEqual([w["spike"] for w in r.windows], [False, False, False, True, False, False])

    def test_spike_explained_single_source(self):
        r = analyze(mk([10, 11, 9, 80, 10, 10], bot_window=3))
        w = r.windows[3]
        self.assertIn("single-source", w["kind"])
        text = " ".join(w["reasons"])
        self.assertIn("bot-9", text)
        self.assertIn("/login", text)
        self.assertIn("new clients", text)
        self.assertEqual(w["severity"], "high")

    def test_iso_timestamps(self):
        r = analyze(lines("2026-11-01T12:00:05Z,a,c,/x\n2026-11-01T12:01:05+00:00,b,c,/x\n"))
        self.assertEqual(r.windows[0]["start"], "2026-11-01T12:00:00Z")
        self.assertEqual(len(r.windows), 2)

    def test_html_dashboard(self):
        out = render_html(analyze(mk([10, 11, 9, 80, 10, 10], bot_window=3)), "x.csv")
        self.assertIn("<svg", out)
        self.assertIn("single source", out)


class Edge(unittest.TestCase):
    def test_duplicates_dropped(self):
        r = analyze(lines("1000,a,c,/x\n1001,a,c,/x\n"))
        self.assertEqual(r.duplicates, 1)
        self.assertEqual(r.windows[0]["count"], 1)

    def test_header_only(self):
        r = analyze([H])
        self.assertEqual(r.windows, [])
        self.assertIn("no valid requests", r.warnings)

    def test_empty_gap_windows_included(self):
        r = analyze(lines("0,a,c,/x\n300,b,c,/x\n"))
        self.assertEqual([w["count"] for w in r.windows], [1, 0, 0, 0, 0, 1])

    def test_flat_traffic_no_divide_by_zero(self):
        flags, scores = flag_counts([20] * 10)
        self.assertEqual(flags, [False] * 10)
        self.assertEqual(scores, [0.0] * 10)

    def test_small_spike_below_min_count_ignored(self):
        flags, _ = flag_counts([0, 0, 0, 0, 5], min_count=10)
        self.assertFalse(flags[-1])

    def test_few_windows_warning(self):
        r = analyze(lines("0,a,c,/x\n"))
        self.assertTrue(any("unreliable" in m for m in r.warnings))

    def test_html_escapes_input(self):
        r = analyze(lines('0,a,c,"<script>x</script>"\n'))
        self.assertNotIn("<script>x", render_html(r))


class Invalid(unittest.TestCase):
    def test_invalid_rows_skipped(self):
        r = analyze(lines("bad,a,c,/x\n1000,,c,/x\n-5,b,c,/x\nnan,d,c,/x\n1000,ok,c,/x\n"))
        self.assertEqual(len(r.invalid), 4)
        self.assertEqual(r.windows[0]["count"], 1)
        self.assertIn("skipped line", render(r))

    def test_bad_header(self):
        with self.assertRaises(ValueError):
            analyze(["a,b\n", "1,2\n"])

    def test_bad_window(self):
        with self.assertRaises(ValueError):
            analyze([H], window=0)

    def test_cli_missing_file(self):
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main(["does-not-exist.csv"]), 2)

    def test_cli_json_and_html(self):
        with tempfile.TemporaryDirectory() as d:
            src, rep = os.path.join(d, "in.csv"), os.path.join(d, "r.html")
            with open(src, "w", encoding="utf-8") as f:
                f.writelines(mk([10, 11, 9, 80, 10, 10]))
            buf = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(io.StringIO()):
                self.assertEqual(main([src, "--json", "--html", rep]), 0)
            data = json.loads(buf.getvalue())
            self.assertEqual(sum(w["spike"] for w in data["windows"]), 1)
            self.assertTrue(os.path.getsize(rep) > 0)


if __name__ == "__main__":
    unittest.main()
