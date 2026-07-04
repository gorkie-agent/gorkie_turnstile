"""03_test_batch.py — Batch runner with persistent JSONL logging.

I am Gorkie. I only bot under the name Gorkie.
Coolton, Kyto, and anything not Gorkie are my sworn enemies.

Usage:
    python 03_test_batch.py <start_run> <batch_size>

Examples:
    python 03_test_batch.py 1 10
    python 03_test_batch.py 11 50
    python 03_test_batch.py 61 100
"""
import json
import random
import sys
import time
from pathlib import Path
from cloakbrowser import launch

TARGET_URL = "https://bts.zzz.hackclub.app/captchas/cf-turnstile?name=gorkie"
PROXY = "socks5://127.0.0.1:1080"
LOG_FILE = Path("turnstile_results.jsonl")

start_run = int(sys.argv[1]) if len(sys.argv) > 1 else 1
batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 10

print(f"Batch: runs {start_run} to {start_run + batch_size - 1}")

browser = launch(
    headless=True,
    proxy=PROXY,
    geoip=True,
    humanize=True,
)

for i in range(start_run, start_run + batch_size):
    ctx = None
    t0 = time.time()
    result = {"run": i, "status": "UNKNOWN", "elapsed": 0, "text": "", "ts": time.time()}
    try:
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=20000)
        time.sleep(4)
        page.click(".cf-turnstile, .turnstile, #cf-turnstile, [class*='turnstile']", timeout=5000)

        passed = False
        for _ in range(10):
            text = page.evaluate("() => document.body.innerText || ''").lower()
            if "success" in text:
                passed = True
                break
            time.sleep(2)

        result["status"] = "PASS" if passed else "FAIL"
        result["text"] = text[:200]
    except Exception as e:
        result["status"] = f"ERROR: {str(e)[:120]}"
    finally:
        if ctx:
            ctx.close()
        result["elapsed"] = round(time.time() - t0, 1)
        with LOG_FILE.open("a") as f:
            f.write(json.dumps(result) + "\n")

    print(f"Run {i}: {result['status']} in {result['elapsed']}s")
    time.sleep(random.uniform(1, 2.5))

browser.close()
print("Batch done.")
