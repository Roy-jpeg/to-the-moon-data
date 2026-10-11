"""
Builds what the game reads from the per-day files:

    data/history/<TICKER>.json   daily closes, oldest first, the last 400 days
    data/intraday/<TICKER>.json  five-minute closes for the last six sessions
    data/index.json              the latest day and how many there are

and keeps only the last seven days of five-minute bars, which are the bulk.
"""

import datetime
import json

from hist import BARS, DAYS, HISTORY, INTRADAY, DATA, tickers, write_json

KEEP_DAYS = 400
INTRADAY_SESSIONS = 6
KEEP_BAR_FILES = 7


def main() -> None:
    days = sorted(DAYS.glob('*.json'))
    history: dict[str, list[dict]] = {t: [] for t in tickers()}
    for path in days[-KEEP_DAYS:]:
        day = json.loads(path.read_text())
        for ticker, price in day['prices'].items():
            if ticker in history:
                history[ticker].append({'date': day['date'], 'close': price['close']})

    bar_files = sorted(BARS.glob('*.json'))
    for old in bar_files[:-KEEP_BAR_FILES]:
        old.unlink()
    bar_files = bar_files[-KEEP_BAR_FILES:]

    intraday: dict[str, list[dict]] = {t: [] for t in tickers()}
    for path in bar_files[-INTRADAY_SESSIONS:]:
        day = json.loads(path.read_text())
        for ticker, rows in day['bars'].items():
            if ticker in intraday:
                intraday[ticker].extend({'t': t, 'date': day['date'], 'close': close} for t, close in rows)

    for ticker in tickers():
        write_json(HISTORY / f'{ticker}.json', history[ticker])
        write_json(INTRADAY / f'{ticker}.json', intraday[ticker])

    write_json(
        DATA / 'index.json',
        {
            'source': 'Data provided for free by IEX. By accessing or using IEX Historical Data, '
            'you agree to the IEX Historical Data Terms of Use.',
            'latest': days[-1].stem if days else None,
            'days': len(days),
            'built': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
        },
    )
    print(f'built {len(tickers())} tickers from {len(days)} days, latest {days[-1].stem if days else "none"}')


if __name__ == '__main__':
    main()
