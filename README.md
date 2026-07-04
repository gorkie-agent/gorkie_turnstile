# gorkie_turnstile

A small toolkit for solving Cloudflare Turnstile automatically with CloakBrowser.

Built because Anirudh asked gorkie to test whether a free stealth browser could beat a live captcha. It can, but only if you do it right.

## What actually worked

1. **A real residential proxy** (not a datacenter IP)
2. **Clicking the widget** (passive loading never solves it)
3. **`humanize=True`** for human-like mouse movement
4. **`geoip=True`** so the browser timezone matches the proxy

Datacenter IPs get blocked even with perfect stealth. The proxy makes the difference.

## Structure

| Path | What it does |
|------|-------------|
| `main.py` | **The current solver.** Async, concurrent contexts, auto proxy relay, configurable speed. |
| `.env` | Your proxy credentials and target URL. Copy from `.env.example`. |
| `iterations/01.py` | One-off test with and without proxy. Proved passive loading fails. |
| `iterations/02.py` | Single solve with click + humanize + geoip. The breakthrough. |
| `iterations/03.py` | Batch runner that logs results to JSONL. |
| `iterations/04.py` | Parallel workers using multiprocessing. One browser per worker. |
| `iterations/05.py` | Faster batch with shorter timeouts. Cut time from ~87s to ~8s. |
| `iterations/06.py` | Standalone worker for shell-level parallelization. |
| `cloakbrowser-docs/` | Cloned CloakBrowser repo for reference. |

## Quick start

```bash
pip install cloakbrowser python-dotenv
pip install 'cloakbrowser[geoip]'
playwright install chromium
```

Copy and edit the environment file:

```bash
cp .env.example .env
# edit .env with your proxy credentials
```

Run a batch:

```bash
python main.py --runs 100 --concurrency 5
```

## Speed

With concurrency set to 5, solves happen at roughly **1 per second** (each solve is ~5s but they overlap). The sweet spot is 4-6 concurrent contexts. Higher concurrency may trigger Cloudflare throttling.

## Results from testing

With the right proxy + click combo, individual solves happen in about 5 to 8 seconds. Without the proxy, it fails every time.

## Troubleshooting

**"Missing X server or $DISPLAY"** — Use `headless=True`. Sandboxes usually have no display.

**"Mouse.up: Protocol error"** — A Chromium crash. Usually means the sandbox is overloaded. Kill leftover browser processes and retry.

**Failures spike after many runs** — The proxy or Cloudflare may throttle the same exit IP. Slow down or add jitter between requests.
