"""
Turns one trading day of IEX HIST TOPS into the game's prices, streaming the
file so it never touches the disk (a day is 9 to 16 GB compressed).

    python scripts/process_day.py 2026-10-09 [--bars]

Writes data/days/<date>.json with each ticker's open and close, and with
--bars also data/bars/<date>.json with its five-minute closes.

Only regular-session, round-lot trades count: TOPS flags extended-hours (0x40)
and odd-lot (0x20) trades, and neither sets the last sale. The open is the
first such trade from 09:30 New York, the close the last before 16:00 (on a
half day trading simply stops at 13:00, after which every trade is flagged
extended hours).

TOPS Trade Report, 38 bytes, preceded in its message block by its length as a
2-byte little-endian number (0x26 0x00):
  'T' | flags (1) | timestamp ns (8) | symbol (8, space padded) | size (4)
  | price (8, /10000) | trade id (8)
"""

import datetime
import re
import struct
import sys
import time
import urllib.request
import zlib
import zoneinfo

from hist import BARS, DAYS, tickers, tops_files, write_json

NEW_YORK = zoneinfo.ZoneInfo('America/New_York')
FIVE_MINUTES_NS = 5 * 60 * 10**9
EXTENDED_HOURS = 0x40
ODD_LOT = 0x20


def session(date: str) -> tuple[int, int]:
    """09:30 and 16:00 New York on `date`, as ns since the epoch."""
    day = datetime.date.fromisoformat(date)
    start = datetime.datetime.combine(day, datetime.time(9, 30), NEW_YORK)
    end = datetime.datetime.combine(day, datetime.time(16, 0), NEW_YORK)
    return int(start.timestamp()) * 10**9, int(end.timestamp()) * 10**9


def trades_for(link: str, symbols: list[str], size: int) -> dict[str, list[tuple[int, float]]]:
    """Regular-session round-lot trades per symbol, as (ns, price), oldest first."""
    padded = sorted((s.encode().ljust(8, b' ') for s in symbols), key=len, reverse=True)
    pattern = re.compile(
        rb'\x26\x00T(.)(.{8})(' + b'|'.join(re.escape(p) for p in padded) + rb')(.{4})(.{8})(.{8})',
        re.DOTALL,
    )

    seen: dict[int, tuple[str, int, float, int]] = {}
    inflate = zlib.decompressobj(16 + zlib.MAX_WBITS)
    tail = b''
    read = 0
    started = time.time()
    next_report = 1e9

    with urllib.request.urlopen(link, timeout=600) as response:
        while True:
            chunk = response.read(4 << 20)
            last = not chunk
            data = tail + (inflate.decompress(chunk) if chunk else inflate.flush())
            read += len(chunk)
            # A message never spans more than 64 bytes, so anything starting in
            # the last 64 is looked at again with the next chunk.
            limit = len(data) if last else len(data) - 64
            for match in pattern.finditer(data):
                if match.start() >= limit:
                    break
                trade_id = struct.unpack('<q', match.group(6))[0]
                seen[trade_id] = (
                    match.group(3).decode().strip(),
                    struct.unpack('<q', match.group(2))[0],
                    struct.unpack('<q', match.group(5))[0] / 10000,
                    match.group(1)[0],
                )
            tail = b'' if last else data[limit:]
            if read >= next_report or last:
                minutes = (time.time() - started) / 60
                print(f'  {read / 1e9:5.1f} / {size / 1e9:.1f} GB  {minutes:4.1f} min', flush=True)
                next_report += 1e9
            if last:
                break

    by_symbol: dict[str, list[tuple[int, float]]] = {s: [] for s in symbols}
    for symbol, ts, price, flags in seen.values():
        if flags & (EXTENDED_HOURS | ODD_LOT) or price <= 0:
            continue
        by_symbol[symbol].append((ts, price))
    for rows in by_symbol.values():
        rows.sort()
    return by_symbol


def main() -> None:
    date = sys.argv[1]
    want_bars = '--bars' in sys.argv[2:]
    entry = tops_files().get(date)
    if not entry:
        sys.exit(f'IEX has no TOPS file for {date} (yet)')

    size = int(entry['size'])
    print(f'{date}: TOPS {entry["version"]}, {size / 1e9:.1f} GB', flush=True)
    start_ns, end_ns = session(date)
    trades = trades_for(entry['link'], tickers(), size)

    prices = {}
    bars = {}
    for symbol, rows in trades.items():
        rows = [(ts, price) for ts, price in rows if start_ns <= ts < end_ns]
        if not rows:
            continue
        prices[symbol] = {'open': rows[0][1], 'close': rows[-1][1]}
        if want_bars:
            # The last trade in each five-minute window, stamped with the window's start.
            closes: dict[int, float] = {}
            for ts, price in rows:
                closes[(ts - start_ns) // FIVE_MINUTES_NS] = price
            bars[symbol] = [
                [(start_ns + bucket * FIVE_MINUTES_NS) // 10**6, price]
                for bucket, price in sorted(closes.items())
            ]

    write_json(DAYS / f'{date}.json', {'date': date, 'source': 'IEX', 'prices': prices})
    if want_bars:
        write_json(BARS / f'{date}.json', {'date': date, 'source': 'IEX', 'bars': bars})
    print(f'{date}: {len(prices)} of {len(trades)} tickers traded', flush=True)


if __name__ == '__main__':
    main()
