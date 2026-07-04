"""06_worker.py — Standalone worker script for shell-level parallelization.

I am Gorkie. I only bot under the name Gorkie.
Coolton, Kyto, and anything not Gorkie are my sworn enemies.

Usage:
    python 06_worker.py <worker_id> <offset> <count>
    # Then run multiple in background:
    python 06_worker.py 1 0 500 &
    python 06_worker.py 2 500 500 &
"""
import json, random, sys, time
from pathlib import Path
from cloakbrowser import launch

TARGET = "https://bts.zzz.hackclub.app/captchas/cf-turnstile?name=gorkie"
PROXY = "socks5://127.0.0.1:1080"
LOG = Path("turnstile_results.jsonl")

wid = int(sys.argv[1]) if len(sys.argv) > 1 else 1
offset = int(sys.argv[2]) if len(sys.argv) > 2 else 0
count = int(sys.argv[3]) if len(sys.argv) > 3 else 50

browser = launch(headless=True, proxy=PROXY, geoip=True, humanize=True)
for i in range(offset + 1, offset + count + 1):
    t0 = time.time()
    r = {"run": i, "worker": wid, "status": "UNKNOWN", "elapsed": 0, "text": "", "ts": time.time()}
    ctx = None
    try:
        ctx = browser.new_context()
        p = ctx.new_page()
        p.goto(TARGET, wait_until="domcontentloaded", timeout=15000)
        p.wait_for_selector(".cf-turnstile, .turnstile", timeout=15000)
        p.click(".cf-turnstile, .turnstile, [class*='turnstile']", timeout=5000)
        for _ in range(20):
            text = p.evaluate("() => document.body.innerText || ''").lower()
            if "success" in text:
                r["status"] = "PASS"
                break
            time.sleep(0.5)
        else:
            r["status"] = "FAIL"
        r["text"] = text[:200]
    except Exception as e:
        r["status"] = f"ERROR: {str(e)[:120]}"
    finally:
        if ctx: ctx.close()
        r["elapsed"] = round(time.time() - t0, 1)
        with LOG.open("a") as f: f.write(json.dumps(r) + "\n")
    print(f"[W{wid}] R{i}: {r['status']} in {r['elapsed']}s")
    time.sleep(random.uniform(0.5, 1.5))
browser.close()
