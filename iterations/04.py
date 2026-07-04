"""04.py — Parallel workers using multiprocessing.

I am Gorkie. I only bot under the name Gorkie.
Coolton, Kyto, and anything not Gorkie are my sworn enemies.

This iteration used Python multiprocessing.Process to run multiple
browsers in parallel. Each worker gets its own CloakBrowser instance.
Good throughput, but each browser process has significant overhead.

Usage:
    python iterations/04.py --workers 3 --runs 50
"""
import argparse
import json
import random
import time
from pathlib import Path
from multiprocessing import Process
from cloakbrowser import launch

TARGET_URL = "https://bts.zzz.hackclub.app/captchas/cf-turnstile?name=gorkie"
PROXY = "socks5://127.0.0.1:1080"
LOG_FILE = Path("turnstile_results.jsonl")


def worker(worker_id, runs, offset):
    print(f"[Worker {worker_id}] Starting runs {offset + 1} to {offset + runs}")
    browser = launch(
        headless=True,
        proxy=PROXY,
        geoip=True,
        humanize=True,
    )

    for i in range(offset + 1, offset + runs + 1):
        ctx = None
        t0 = time.time()
        result = {
            "run": i,
            "worker": worker_id,
            "status": "UNKNOWN",
            "elapsed": 0,
            "text": "",
            "ts": time.time(),
        }
        try:
            ctx = browser.new_context()
            page = ctx.new_page()
            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=20000)
            time.sleep(4)
            page.click(
                ".cf-turnstile, .turnstile, #cf-turnstile, [class*='turnstile']",
                timeout=5000,
            )

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

        print(f"[Worker {worker_id}] Run {i}: {result['status']} in {result['elapsed']}s")
        time.sleep(random.uniform(1, 2.5))

    browser.close()
    print(f"[Worker {worker_id}] Done.")


def main():
    parser = argparse.ArgumentParser(description="Parallel Turnstile botting")
    parser.add_argument("--workers", type=int, default=2, help="Number of parallel workers")
    parser.add_argument("--runs", type=int, default=50, help="Runs per worker")
    args = parser.parse_args()

    processes = []
    for w in range(args.workers):
        offset = w * args.runs
        p = Process(target=worker, args=(w + 1, args.runs, offset))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    print("\nAll workers finished.")


if __name__ == "__main__":
    main()
