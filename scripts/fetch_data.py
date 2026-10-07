"""Re-fetch the small public-data extract under data/ from Binance's free public archive.

Source: https://data.binance.vision (Binance public market data, no key needed). Files used:
  spot hourly klines   https://data.binance.vision/data/spot/monthly/klines/{SYM}/1h/{SYM}-1h-{YYYY-MM}.zip
  spot daily klines    https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1d/BTCUSDT-1d-{YYYY-MM}.zip
  quarterly futures    https://data.binance.vision/data/futures/um/monthly/klines/{SYM}_{YYMMDD}/1h/...zip
  perpetual funding    https://data.binance.vision/data/futures/um/monthly/fundingRate/{SYM}/...zip

Writes three CSVs and data/MANIFEST.json (SHA-256, bytes, rows, fetch date). The experiments read only the
committed extract and check it against the manifest, so they run offline; this script needs the network.

    python scripts/fetch_data.py
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BASE = "https://data.binance.vision/data"
YEAR = 2025
DAILY_FROM = 2018
COINS = ("BTC", "ETH")
# USD-M quarterly contracts covering YEAR. A contract expires at 08:00 UTC on its date.
QUARTERLIES = ("250328", "250627", "250926", "251226", "260327")
ROLL_DAYS = 14  # use the nearest quarterly with at least this many days left (annualised basis is noisy near expiry)
H_MS = 3_600_000


def _get_zip_rows(url: str) -> list[list[str]] | None:
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            blob = r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        text = z.read(z.namelist()[0]).decode()
    rows = [line.split(",") for line in text.strip().splitlines()]
    return [r for r in rows if r[0].strip().lstrip("-").isdigit()]  # drop a header row if present


def _ms(x: str) -> int:
    v = int(x)
    return v // 1000 if v > 10**14 else v  # spot files switched to microseconds in 2025


def _months(y0: int, y1: int):
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            yield f"{y}-{m:02d}"


def _expiry_ms(code: str) -> int:
    d = dt.datetime.strptime(code, "%y%m%d").replace(hour=8, tzinfo=dt.timezone.utc)
    return int(d.timestamp() * 1000)


def _closes(url_fmt: str, months) -> dict[int, float]:
    """Kline close price keyed by the bar's close time (open time + 1 h, the repo's bar convention)."""
    out: dict[int, float] = {}
    for m in months:
        rows = _get_zip_rows(url_fmt.format(m=m))
        for r in rows or []:
            out[_ms(r[0]) + H_MS] = float(r[4])
    return out


def fetch_hourly() -> tuple[list[list], list[str]]:
    months = list(_months(YEAR, YEAR))
    t0 = int(dt.datetime(YEAR, 1, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
    grid = list(range(t0, t0 + 365 * 24 * H_MS, H_MS))
    cols, series = ["close_time_ms"], []
    for c in COINS:
        sym = f"{c}USDT"
        spot = _closes(f"{BASE}/spot/monthly/klines/{sym}/1h/{sym}-1h-{{m}}.zip", months)
        futs = {q: _closes(f"{BASE}/futures/um/monthly/klines/{sym}_{q}/1h/{sym}_{q}-1h-{{m}}.zip", months)
                for q in QUARTERLIES}
        fut_px, fut_code = [], []
        for t in grid:
            code = next(q for q in QUARTERLIES if _expiry_ms(q) - t >= ROLL_DAYS * 24 * H_MS)
            fut_px.append(futs[code].get(t))
            fut_code.append(code)
        series += [[spot.get(t) for t in grid], fut_px, fut_code]
        cols += [f"{c.lower()}_spot", f"{c.lower()}_quarterly", f"{c.lower()}_quarterly_expiry"]
    rows = [[t] + [s[i] if s[i] is not None else "" for s in series] for i, t in enumerate(grid)]
    return rows, cols


def fetch_funding() -> list[list]:
    rows = []
    for c in COINS:
        sym = f"{c}USDT"
        for m in _months(YEAR, YEAR):
            for r in _get_zip_rows(f"{BASE}/futures/um/monthly/fundingRate/{sym}/{sym}-fundingRate-{m}.zip") or []:
                # columns: calc_time, funding_interval_hours, last_funding_rate
                ms = _ms(r[0])  # calc_time carries a few ms of jitter; funding is on the hour
                rows.append([round(ms / H_MS) * H_MS, ms, sym, int(r[1]), float(r[2])])
    return sorted(rows)


def fetch_daily() -> list[list]:
    closes = _closes(f"{BASE}/spot/monthly/klines/BTCUSDT/1d/BTCUSDT-1d-{{m}}.zip", _months(DAILY_FROM, YEAR))
    return [[t - H_MS + 24 * H_MS, closes[t]] for t in sorted(closes)]  # key by day close


def _write(name: str, header: list[str], rows: list[list]) -> dict:
    path = DATA / name
    with path.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
    blob = path.read_bytes()
    return {"file": name, "sha256": hashlib.sha256(blob).hexdigest(), "bytes": len(blob), "rows": len(rows)}


def main() -> int:
    DATA.mkdir(exist_ok=True)
    hourly, cols = fetch_hourly()
    files = [
        _write(f"binance_hourly_{YEAR}.csv", cols, hourly),
        _write(f"binance_funding_{YEAR}.csv", ["funding_time_ms", "calc_time_ms", "symbol", "interval_hours", "rate"],
               fetch_funding()),
        _write("binance_btcusdt_daily.csv", ["close_time_ms", "close"], fetch_daily()),
    ]
    manifest = {
        "source": BASE,
        "fetched_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"),
        "fetched_by": "scripts/fetch_data.py",
        "notes": (f"Hourly closes for {YEAR} (bar close time, UTC ms). Quarterly column = nearest USD-M "
                  f"quarterly with >= {ROLL_DAYS} days to expiry (expiry 08:00 UTC). Funding = last_funding_rate "
                  "per interval. Daily = BTCUSDT spot close."),
        "files": files,
    }
    (DATA / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    total = sum(f["bytes"] for f in files)
    print(f"fetch_data: wrote {len(files)} files, {total / 1e6:.2f} MB")
    return 0 if total <= 2_000_000 else 1


if __name__ == "__main__":
    sys.exit(main())
