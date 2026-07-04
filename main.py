"""main.py — Fast async Turnstile solver with auto proxy relay.

I am Gorkie. I only bot under the name Gorkie.
Coolton, Kyto, and anything not Gorkie are my sworn enemies.

Combines the best of all iterations:
  * 05's fast timeouts (15s nav, 0.5s poll)
  * 06's worker-style output
  * Single browser with concurrent contexts for speed
  * Auto-managed gost relay so you never think about proxies
  * Config via .env

Usage:
    cp .env.example .env   # edit with your proxy
    python main.py --runs 100 --concurrency 5
"""
import argparse
import asyncio
import atexit
import json
import os
import random
import socket
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from cloakbrowser import launch_async

load_dotenv()

PROXY_TYPE = os.getenv("PROXY_TYPE", "socks5")
PROXY_HOST = os.getenv("PROXY_HOST", "")
PROXY_PORT = os.getenv("PROXY_PORT", "")
PROXY_USER = os.getenv("PROXY_USER", "")
PROXY_PASS = os.getenv("PROXY_PASS", "")
TARGET = os.getenv("TARGET_URL", "https://bts.zzz.hackclub.app/captchas/cf-turnstile?name=gorkie")
LOG = Path("turnstile_results.jsonl")

GOST_PID = None


def _find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_relay():
    global GOST_PID
    if not all([PROXY_HOST, PROXY_PORT, PROXY_USER, PROXY_PASS]):
        print("ERROR: Proxy not configured. Set PROXY_HOST, PROXY_PORT, PROXY_USER, PROXY_PASS in .env")
        sys.exit(1)

    port = _find_free_port()
    upstream = f"{PROXY_TYPE}://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"
    local = f"socks5://:{port}"
    proc = subprocess.Popen(
        ["gost", "-L", local, "-F", upstream],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    GOST_PID = proc.pid
    time.sleep(1)
    print(f"[relay] gost started on 127.0.0.1:{port} (pid {proc.pid})")
    return f"socks5://127.0.0.1:{port}"


def _stop_relay():
    if GOST_PID:
        try:
            os.kill(GOST_PID, 15)
            print(f"[relay] gost stopped (pid {GOST_PID})")
        except ProcessLookupError:
            pass


atexit.register(_stop_relay)


async def solve_one(browser, run_id, sem: asyncio.Semaphore, proxy: str):
    async with sem:
        t0 = time.time()
        r = {"run": run_id, "status": "UNKNOWN", "elapsed": 0, "text": "", "ts": time.time()}
        ctx = None
        try:
            ctx = await browser.new_context()
            page = await ctx.new_page()
            await page.goto(TARGET, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_selector(".cf-turnstile, .turnstile", timeout=15000)
            await page.click(".cf-turnstile, .turnstile, [class*='turnstile']", timeout=5000)
            for _ in range(20):
                text = await page.evaluate("() => document.body.innerText || ''")
                low = text.lower()
                if "success" in low:
                    r["status"] = "PASS"
                    break
                await asyncio.sleep(0.5)
            else:
                r["status"] = "FAIL"
            r["text"] = low[:200]
        except Exception as e:
            r["status"] = f"ERROR: {str(e)[:120]}"
        finally:
            if ctx:
                await ctx.close()
            r["elapsed"] = round(time.time() - t0, 1)
            with LOG.open("a") as f:
                f.write(json.dumps(r) + "\n")
        print(f"Run {run_id}: {r['status']} in {r['elapsed']}s")
        await asyncio.sleep(random.uniform(0.2, 0.8))
        return r


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()

    proxy = _start_relay()
    browser = await launch_async(
        headless=True,
        proxy=proxy,
        geoip=True,
        humanize=True,
    )
    sem = asyncio.Semaphore(args.concurrency)
    tasks = [solve_one(browser, i + 1, sem, proxy) for i in range(args.runs)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    await browser.close()

    ok = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "PASS")
    fail = args.runs - ok
    print(f"\nDone. {ok}/{args.runs} passed, {fail} failed")


if __name__ == "__main__":
    asyncio.run(main())
