import random, datetime
random.seed(7)
base = datetime.datetime(2026, 11, 1, 12, 0, 0)
rows = ["timestamp,request_id,client,endpoint"]
rid = 0
for minute in range(15):
    n = random.randint(8, 12) + (60 if minute == 9 else 0)
    for _ in range(n):
        rid += 1
        t = base + datetime.timedelta(minutes=minute, seconds=random.randint(0, 59))
        c = "bot-1" if minute == 9 and random.random() < .8 else f"client-{random.randint(1,6)}"
        ep = "/login" if minute == 9 else random.choice(["/items", "/search", "/profile"])
        rows.append(f"{t.isoformat()}Z,r{rid},{c},{ep}")
rows.append(rows[3])                      # duplicate
rows.append("not-a-date,rX,c,/x")         # invalid
rows.append("2026-11-01T12:01:00Z,,c,/x") # missing id
open("data/sample.csv", "w").write("\n".join(rows) + "\n")
