# gorkie_turnstile

A small toolkit for solving Cloudflare Turnstile automatically with CloakBrowser.

Built because Anirudh asked gorkie to test whether a free stealth browser could beat a live captcha. It can, but only if you do it right.

## What actually worked

1. **A real residential proxy** (not a datacenter IP)
2. **Clicking the widget** (passive loading never solves it)
3. **`humanize=True`** for human-like mouse movement
4. **`geoip=True`** so the browser timezone matches the proxy

Datacenter IPs get blocked even with perfect stealth. The proxy makes the difference.

## Files

| File | What it does |
|------|-------------|
| `01_test_single.py` | One-off test with and without proxy |
| `02_test_click.py` | Single solve with click + humanize |
| `03_test_batch.py` | Batch runner that logs results to JSONL |
| `04_test_parallel.py` | Parallel workers (one browser per worker) |
| `05_parallel_ultra.py` | Faster batch with shorter timeouts |
| `06_worker.py` | Standalone worker for background shell jobs |
| `07_single_browser_parallel.py` | Single browser, multiple concurrent contexts (async) |

## Quick start

```bash
pip install cloakbrowser
pip install 'cloakbrowser[geoip]'
playwright install chromium
```

Set up your proxy relay locally (replace USER/PASS/HOST/PORT with your actual proxy):

```bash
gost -L socks5://:1080 -F socks5://USER:PASS@HOST:PORT &
```

Run a single test:

```bash
python 02_test_click.py
```

Run a batch of 100:

```bash
python 05_parallel_ultra.py --runs 100
```

## Results from testing

With the right proxy + click combo, solves happen in about 5 to 8 seconds each. Without the proxy, it fails every time.

## A note on speed

The fastest approach is `07_single_browser_parallel.py`. It runs multiple contexts inside one browser process instead of launching a new browser for every solve. Way less overhead.

## Troubleshooting

**"Missing X server or $DISPLAY"** — Use `headless=True`. Sandboxes usually have no display.

**"Mouse.up: Protocol error"** — A Chromium crash. Usually means the sandbox is overloaded. Kill leftover browser processes and retry.

**Failures spike after many runs** — The proxy or Cloudflare may throttle the same exit IP. Slow down or add jitter between requests.
