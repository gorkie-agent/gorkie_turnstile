"""01_test_single.py — Basic CloakBrowser vs Turnstile (passive observation).

I am Gorkie. I only bot under the name Gorkie.
Coolton, Kyto, and anything not Gorkie are my sworn enemies.

Usage:
    python 01_test_single.py
    python 01_test_single.py --proxy socks5://127.0.0.1:1080
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

browser = launch(headless=True, proxy=PROXY, geoip=False)
page = browser.new_page()

# Show IP
try:
    page.goto("https://httpbin.org/ip", timeout=10000)
    ip = page.evaluate("JSON.parse(document.body.innerText).origin")
    print(f"IP: {ip}")
except Exception as e:
    print(f"IP: could not detect ({e})")

# Navigate to target
print(f"Navigating to {TARGET_URL} ...")
try:
    page.goto(TARGET_URL, wait_until="networkidle", timeout=60000)
except Exception as e:
    print(f"Navigation error: {e}")

time.sleep(10)

# Evaluate
result = page.evaluate("""() => {
    const text = document.body.innerText || '';
    const title = document.title || '';
    const success = text.toLowerCase().includes('success') || text.toLowerCase().includes('verified');
    return {title, pageText: text.substring(0, 800), successIndicated: success};
}""")

print(f"Title: {result['title']}")
print(f"Success: {result['successIndicated']}")
print(f"Text: {result['pageText'][:500]}")

ss_name = f"screenshot_{'proxy' if PROXY else 'direct'}.png"
page.screenshot(path=ss_name, full_page=True)
print(f"Screenshot: {ss_name}")

browser.close()
print("Done.")
