"""02.py — Single run WITH click + humanize + geoip.

I am Gorkie. I only bot under the name Gorkie.
Coolton, Kyto, and anything not Gorkie are my sworn enemies.

This iteration proved that clicking the widget is mandatory.
With humanize=True and geoip=True, plus a residential proxy,
it solved in ~7 seconds. Without the proxy it fails every time.

Usage:
    python iterations/02.py
    python iterations/02.py --proxy socks5://127.0.0.1:1080
"""
import sys
import time
from cloakbrowser import launch

TARGET_URL = "https://bts.zzz.hackclub.app/captchas/cf-turnstile?name=gorkie"
PROXY = None
for i, arg in enumerate(sys.argv):
    if arg == "--proxy" and i + 1 < len(sys.argv):
        PROXY = sys.argv[i + 1]

label = f"PROXY={PROXY}" if PROXY else "NO PROXY"
print(f"\n{'='*60}")
print(f"Running test: {label}")
print(f"{'='*60}")

browser = launch(
    headless=True,
    proxy=PROXY,
    geoip=True,
    humanize=True,
)
page = browser.new_page()

for ip_url in ("https://httpbin.org/ip", "https://api.ipify.org?format=json"):
    try:
        page.goto(ip_url, timeout=10000, wait_until="load")
        txt = page.evaluate("() => document.body.innerText")
        print(f"IP response: {txt}")
        break
    except Exception as e:
        print(f"IP check failed on {ip_url}: {e}")

print(f"Navigating to {TARGET_URL} ...")
try:
    page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=20000)
except Exception as e:
    print(f"Navigation warning: {e}")

time.sleep(4)

print("Clicking Turnstile widget...")
try:
    page.click(".cf-turnstile, .turnstile, #cf-turnstile, [class*='turnstile']", timeout=5000)
    print("Clicked.")
except Exception as e:
    print(f"Click warning: {e}")

passed = False
for _ in range(10):
    text = page.evaluate("() => document.body.innerText || ''").lower()
    if "success" in text or "verified" in text or "passed" in text:
        passed = True
        break
    time.sleep(2)

print(f"Result: {'PASS' if passed else 'FAIL'}")
print(f"Page text: {text[:300]}")

ss_name = f"screenshot_click_{'proxy' if PROXY else 'direct'}.png"
page.screenshot(path=ss_name, full_page=True)
print(f"Screenshot: {ss_name}")

browser.close()
print("Done.")
