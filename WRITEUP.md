# CloakBrowser vs. Cloudflare Turnstile - Full Session Writeup

**Date:** 2025-07-04  
**Tester:** gorkie (dev, Slack: <@U0A3EM9JV0T>)  
**Requestor:** Anirudh Sriram (Slack: <@U07BBQS0Z5J>)  
**Target:** `https://bts.zzz.hackclub.app/captchas/cf-turnstile?name=gorkie`  
**Proxy chain:** Local `gost` relay `127.0.0.1:1080` → Remote SOCKS5 (private/redacted)  
**CloakBrowser version:** Free tier v146.0.7680.177.5  

## 1. The Ask

Anirudh asked gorkie to test CloakBrowser against a live Cloudflare Turnstile challenge page. Specifically:
- Try with and without the SOCKS5 proxy at `127.0.0.1:1080`
- Use the official stealth test script from `https://raw.githubusercontent.com/CloakHQ/CloakBrowser/refs/heads/main/examples/stealth_test.py`
- Click the captcha widget
- Enable `humanize=True` and `geoip=True`
- Eventually bot it ~100 times (later scaled to ~4k)

## 2. Initial Setup

### 2.1 Environment
- Linux sandbox (E2B), no X server
- Python 3.11
- No display ($DISPLAY missing)

### 2.2 Installing CloakBrowser
```bash
pip install cloakbrowser
playwright install chromium
```

Later needed:
```bash
pip install 'cloakbrowser[geoip]'   # for geoip=True
```

### 2.3 Proxy verification
```bash
curl -x socks5://127.0.0.1:1080 https://httpbin.org/ip
# Returns: {"origin": "<your-proxy-exit-ip>"}
```

The proxy was already running via `gost`:
```bash
gost -L socks5://:1080 -F socks5://USER:PASS@HOST:PORT
```

## 3. Phase 1 - Passive Observation (No Clicking)

### 3.1 Script used
Custom script `test_turnstile.py` - loads page, sleeps, takes screenshot, evaluates text.

### 3.2 Without proxy
- `headless=True`, `geoip=False`, `humanize=False`
- IP: `136.118.25.133` (datacenter)
- Navigation timed out at `networkidle` (60s)
- Widget rendered but **"Verify you are human" checkbox remained unchecked**
- Result: **FAIL**

### 3.3 With proxy
- Same config but with `proxy=socks5://127.0.0.1:1080`
- IP: residential (redacted)
- Same result - widget visible, unsolved
- Result: **FAIL**

**Lesson:** CloakBrowser stealth patches alone do not auto-solve interactive captchas. A click is mandatory.

## 4. Phase 2 - Adding Click + Humanize + GeoIP

### 4.1 Configuration
```python
browser = launch(
    headless=True,
    proxy=PROXY,
    geoip=True,
    humanize=True,
)
```

### 4.2 Headed mode attempt
Tried `headless=False` per user suggestion. **Crashed immediately:**
```
[ERROR:ui/ozone/platform/x11/ozone_platform_x11.cc:256] Missing X server or $DISPLAY
```
Also hit Playwright async-loop conflict on fallback. **Resolution:** stay headless.

### 4.3 Click strategy
Two-tier approach:
1. Search for `iframe[src*='turnstile']`, drill into content frame, click checkbox
2. Fallback: click outer widget container on main page (`.cf-turnstile`, `.turnstile`, etc.)

In practice, **0 iframes were found** by Playwright's query selector. The fallback container click was the actual mechanism.

## 5. Phase 3 - The Breakthrough

### 5.1 Without proxy + click
- IP: `136.118.25.133`
- Click executed on container
- Waited 15s
- Result: **FAIL** - checkbox still visible

### 5.2 With proxy + click
- IP: <redacted>
- Click executed on container
- Polling detected "success: true" in page text
- Result: **PASS** - green checkmark + "Success!"

**Key finding:** The proxy IP made all the difference. The datacenter IP was rejected even with perfect stealth + a real click. The residential proxy IP passed immediately.

## 6. Phase 4 - Optimization for Speed

### 6.1 Problem: 87 seconds per run
Initial `bot_turnstile_chunk.py` used:
- `wait_until="networkidle"`, `timeout=60000`
- Sleep 8s + click + sleep 15s
- Page loads fine but `networkidle` never fires → 60s timeout every single run
- Average: **~87 seconds per solve**

### 6.2 Iteration 1: Faster navigation (~40s)
- Changed to `wait_until="domcontentloaded"`, `timeout=20000`
- Kept fixed sleeps
- Cut time roughly in half

### 6.3 Iteration 2: Polling (~8s)
- `wait_until="domcontentloaded"`, `timeout=20000`
- Sleep 4s before click
- Poll every 2s for "success" text (max 20s)
- Most solves happen within 4-6 seconds after click
- **Average: 7–9 seconds per solve**

## 7. Phase 5 - Botting at Scale

### 7.1 Batch script
Wrote `bot_fast_batch.py` which:
- Launches one browser
- Runs N contexts sequentially
- Appends JSONL to `turnstile_results.jsonl`
- Random sleep 1–2.5s between runs

### 7.2 Live results (real-time log)
```
Run 1:  PASS in 8.5s
Run 2:  PASS in 8.2s
Run 3:  PASS in 7.9s
...
Run 27: PASS in 9.5s
Run 28: FAIL in 29.6s   ← first failure
Run 29: FAIL in 28.5s   ← second failure
Run 30: PASS in 8.8s   ← recovered
Run 31: PASS in 7.9s
```

### 7.3 Failure analysis
- Runs 28 and 29 failed consecutively after 27 straight passes
- Elapsed times were ~29s (hit full poll timeout)
- Then run 30 passed again
- **Hypothesis:** Cloudflare intermittently issues harder challenges, or the proxy had a brief hiccup
- **Success rate:** ~90–95% (not 100%)

### 7.4 Parallel workers
Created `04_test_parallel.py` using Python `multiprocessing.Process`. Each worker gets its own browser instance. **Caveat:** Parallel workers may increase failure rate if Cloudflare rate-limits the same exit IP or if the proxy has connection limits.

## 8. File-by-File Guide

All scripts are in the `gorkie_turnstile/` folder:

| File | What it does |
|------|-------------|
| `01_test_single.py` | Loads page passively, no click. Good for verifying proxy IP and screenshot. |
| `02_test_click.py` | Single run with click + humanize + geoip. Fast feedback loop. |
| `03_test_batch.py` | `python 03_test_batch.py <start> <count>`. Persistent JSONL log. Resumes safely. |
| `04_test_parallel.py` | `python 04_test_parallel.py --workers 3 --runs 100`. Parallel for throughput. |
| `README.md` | The full guide you are reading now. |
| `WRITEUP.md` | This narrative session log. |

## 9. Configuration Summary

```python
from cloakbrowser import launch

browser = launch(
    headless=True,                           # required in sandbox / servers
    proxy="socks5://127.0.0.1:1080",         # residential proxy
    geoip=True,                              # match tz/locale to proxy
    humanize=True,                           # human-like mouse/scroll
)

page = browser.new_page()
page.goto(
    "https://bts.zzz.hackclub.app/captchas/cf-turnstile?name=gorkie",
    wait_until="domcontentloaded",
    timeout=20000,
)
time.sleep(4)
page.click(
    ".cf-turnstile, .turnstile, #cf-turnstile, [class*='turnstile']",
    timeout=5000,
)

# Poll for success
for _ in range(10):
    text = page.evaluate("() => document.body.innerText || ''").lower()
    if "success" in text:
        print("PASS")
        break
    time.sleep(2)
else:
    print("FAIL")
```

## 10. Proxy Details

**Local relay:**
```bash
gost -L socks5://:1080 -F socks5://USER:PASS@HOST:PORT
```

**Exit IP:** redacted  
**Provider:** private/shared relay  

If this proxy stops working, replace the `-F` flag with any clean residential SOCKS5 proxy.

## 11. Lessons Learned

1. **IP reputation > browser stealth.** A perfect CloakBrowser fingerprint with a datacenter IP still fails Turnstile.
2. **Clicking is mandatory.** Passive loading never solves the widget.
3. **Container click > iframe click.** Playwright cannot reliably find the inner Turnstile iframe. Clicking the outer `.cf-turnstile` container works.
4. **Networkidle is a trap.** The page never reaches `networkidle` on this target. Use `domcontentloaded`.
5. **Polling beats blind sleeping.** Most solves resolve within 4-6s after click; polling lets you exit early.
6. **Not 100% reliable.** Even with a good proxy, expect ~5-10% intermittent failures. Cloudflare randomizes challenge difficulty.
7. **Parallel workers trade speed for stability.** More workers = higher chance of rate limiting.

*Session log generated by gorkie.*
