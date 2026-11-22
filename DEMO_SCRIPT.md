# Demo video script (target 1:50, hard limit 2:00)

The official page asks for a video of **at most 2 minutes**, and the form field says "3 min max". Stay under **2:00** to satisfy both.

## Before you record (5 minutes)
1. Close notifications, chat apps and browser tabs that show personal data. The submission must be sanitized.
2. Open a terminal in the project folder. Set the font to 18 pt or larger and use a dark theme with the window maximised.
3. Rehearse once: `powershell -ExecutionPolicy Bypass -File run_demo.ps1`. Press ENTER to advance each step. Delete `report.html` afterwards (it is git-ignored).
4. Have the README open in a browser tab at https://github.com/rohanjain1648/SpikeSentry, scrolled to **Known limitations** (§13).

## How to record on Windows
- **Easiest: Xbox Game Bar.** Press `Win+G`, click Capture, then Record (or `Win+Alt+R`). It records one app window at a time, so record the terminal. Videos save to `Videos\Captures`.
- **Better: OBS Studio** (free). Add "Display Capture" and your microphone, then Start Recording.
- Speak slowly and clearly. Narrated recordings and silent captioned ones are both accepted, and webcam footage isn't needed.

## Shot list and narration (about 245 words, about 1:50)

| Time | On screen | Narration |
|---|---|---|
| 0:00–0:10 | Terminal. Run `run_demo.ps1`; the title shows. | "This is SpikeSentry, my entry for AEGYTHON Challenge 03, API Traffic Watch. It finds unusual traffic in synthetic API logs and explains why, fully offline." |
| 0:10–0:25 | **Step 1.** Input rows: header, normal rows, then `bot-1` rows. | "The input is a synthetic request log: timestamp, request ID, client and endpoint. It contains normal traffic, and a burst from one client called bot-1." |
| 0:25–1:00 | **Step 2.** Table, then explanation. Pause on the `SPIKE` row and the explanation lines. | "SpikeSentry removes duplicates, groups requests into one-minute windows, and scores each window with a median and MAD robust score. At 12:09, 68 requests are scored 38 against a normal of about 11, so it's flagged as a spike. Then it explains it: bot-1 sent 82 percent of requests, the traffic all went to /login against zero percent normally, and bot-1 is a new client. That is a brute-force-style burst. The duplicate and the two bad rows were counted and skipped, not crashed on." |
| 1:00–1:12 | **Step 3.** The HTML dashboard opens. | "The same results as an offline dashboard: requests per window with the spike in red, and the explanation card." |
| 1:12–1:22 | **Step 4.** Invalid input run. | "Invalid input is reported with line numbers and the run continues." |
| 1:22–1:32 | **Step 5.** Tests, ending "OK". | "Seventeen tests cover normal, edge and invalid input, and they pass." |
| 1:32–1:52 | **Step 6.** Evaluation table. Pause on the F1 and recall rows. | "For validation I injected spikes of known size into 500 synthetic series. The robust method reaches F1 0.96, against 0.71 for a standard mean and standard deviation score, because a big spike inflates its own baseline and hides itself. The cost is slightly more false alarms." |
| 1:52–2:00 | README, Known limitations (§13). | "Limitations are documented: fixed windows, one global baseline, synthetic validation. Setup is in the README. Thanks for watching." |

If you run long, shorten Step 4 or Step 5 first. Never cut Step 2.

## After recording: upload and get the URL
1. **YouTube (recommended):** go to studio.youtube.com, click Create, then Upload video. Set visibility to **Unlisted** (anyone with the link can watch, and it isn't searchable). Choose "No, it's not made for kids". Copy the link, e.g. `https://youtu.be/xxxxxxxxxxx`.
2. **Alternative:** Google Drive. Upload, then Share, then "Anyone with the link: Viewer". Copy the link.
3. **Check the link in a private/incognito window** while signed out. Confirm it plays, and check that the length shows **under 2:00**.
4. Put the URL into the README header (`<VIDEO-URL>`) and the form. Then commit, push and move the tag:
```
git add -A
git commit -m "Add demo video URL"
git push origin main
git tag -f -a v1.0-review -m "Frozen review commit"
git push -f origin v1.0-review
```

## Checklist before you submit the form
- [ ] Video is under 2:00 and plays when signed out
- [ ] No personal data on screen (email, tabs, notifications, file paths with your name)
- [ ] The spike explanation and the evaluation table were readable (paused long enough)
- [ ] The video URL is in the form, and the README and tag are pushed
