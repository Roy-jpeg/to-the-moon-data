"""
Shared helpers: where things live, and IEX's list of HIST files.

IEX publishes each trading day's exchange data the next day ("T+1") and keeps
the trailing twelve months. The listing is public JSON; each file is a
gzipped pcap of several gigabytes.
"""

import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
DAYS = DATA / 'days'
BARS = DATA / 'bars'
HISTORY = DATA / 'history'
INTRADAY = DATA / 'intraday'

LISTING_URL = 'https://iextrading.com/api/1.0/hist'


def tickers() -> list[str]:
    lines = (ROOT / 'tickers.txt').read_text().split()
    return sorted({line.strip().upper() for line in lines if line.strip()})


def tops_files() -> dict[str, dict]:
    """Every day IEX has a TOPS file for, as `YYYY-MM-DD` -> the listing entry."""
    with urllib.request.urlopen(LISTING_URL, timeout=120) as response:
        listing = json.load(response)
    files = {}
    for day, entries in listing.items():
        for entry in entries:
            if entry.get('feed') == 'TOPS':
                files[f'{day[:4]}-{day[4:6]}-{day[6:]}'] = entry
    return files


def write_json(path: pathlib.Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, separators=(',', ':')) + '\n')
