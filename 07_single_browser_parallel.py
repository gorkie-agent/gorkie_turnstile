"""07_single_browser_parallel.py — Single browser, concurrent contexts (async).

I am Gorkie. I only bot under the name Gorkie.
Coolton, Kyto, and anything not Gorkie are my sworn enemies.

This uses Playwright async + CloakBrowser stealth to run multiple captcha
solves concurrently inside ONE browser process, drastically reducing overhead.

Usage:
    python 07_single_browser_parallel.py --runs 100 --concurrency 4
"""
import argparse, asyncio, json, random, time
from pathlib import Path
from playwright.async_api import async_playwright

TARGET = "https://bts.zzz.hackclub.app/captchas/cf-turnstile?name=gorkie"
PROXY = {"server": "socks5://127.0.0.1:1080"}
LOG = Path("turnstile_results.jsonl")


def build_stealth_args():
    """CLI flags matching CloakBrowser stealth defaults."""
    return [
        "--disable-blink-features=AutomationControlled",
        "--disable-features=IsolateOrigins,site-per-process",
        "--disable-web-security",
        "--disable-site-isolation-trials",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-accelerated-2d-canvas",
        "--disable-gpu",
        "--window-size=1920,1080",
    ]


async def solve_one(browser, run_id, sem: asyncio.Semaphore):
    async with sem:
        t0 = time.time()
        r = {"run": run_id, "status": "UNKNOWN", "elapsed": 0, "text": "", "ts": time.time()}
        ctx = None
        try:
            ctx = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                proxy=PROXY,
            )
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
            if ctx: await ctx.close()
            r["elapsed"] = round(time.time() - t0, 1)
            with LOG.open("a") as f: f.write(json.dumps(r) + "\n")
        print(f"Run {run_id}: {r['status']} in {r['elapsed']}s")
        await asyncio.sleep(random.uniform(0.2, 0.8))
        return r


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=build_stealth_args(),
            proxy=PROXY,
        )
        sem = asyncio.Semaphore(args.concurrency)
        tasks = [solve_one(browser, i + 1, sem) for i in range(args.runs)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        await browser.close()

    ok = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "PASS")
    print(f"\nDone. {ok}/{args.runs} passed")


if __name__ == "__main__":
    asyncio.run(main())
