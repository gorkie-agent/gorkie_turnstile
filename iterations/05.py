"""05.py — Optimized batch with shortened timeouts.

I am Gorkie. I only bot under the name Gorkie.
Coolton, Kyto, and anything not Gorkie are my sworn enemies.

This iteration cut solve time from ~87s to ~8s by switching from
networkidle to domcontentloaded, reducing timeouts to 15s, and
using tight 0.5s polling instead of 2s sleeps.

Usage:
    python iterations/05.py --runs 100
"""
import argparse, json, random, time
from pathlib import Path
from cloakbrowser import launch

TARGET = "https://bts.zzz.hackclub.app/captchas/cf-turnstile?name=gorkie"
PROXY = "socks5://127.0.0.1:1080"
LOG = Path("turnstile_results.jsonl")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=100)
    args = parser.parse_args()
    browser = launch(headless=True, proxy=PROXY, geoip=True, humanize=True)
    for i in range(1, args.runs + 1):
        t0 = time.time()
        r = {"run": i, "status": "UNKNOWN", "elapsed": 0, "text": "", "ts": time.time()}
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
        print(f"Run {i}: {r['status']} in {r['elapsed']}s")
        time.sleep(random.uniform(0.5, 1.5))
    browser.close()


if __name__ == "__main__":
    main()
