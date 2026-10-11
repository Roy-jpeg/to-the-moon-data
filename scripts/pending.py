"""
Trading days IEX has published that are not processed yet, newest first.

    python scripts/pending.py --recent 10 --limit 3   # the daily run
    python scripts/pending.py --chunks 20             # the backfill, as a JSON matrix

Only the trailing year: older days are gone from IEX, and the game's longest
chart is one year.
"""

import argparse
import datetime
import json

from hist import DAYS, tops_files


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--recent', type=int, default=366, help='only days within this many calendar days')
    parser.add_argument('--limit', type=int, default=0, help='at most this many days')
    parser.add_argument('--chunks', type=int, default=0, help='print a JSON list of this many space-separated groups')
    args = parser.parse_args()

    since = (datetime.date.today() - datetime.timedelta(days=args.recent)).isoformat()
    done = {path.stem for path in DAYS.glob('*.json')}
    missing = sorted((day for day in tops_files() if day >= since and day not in done), reverse=True)
    if args.limit:
        missing = missing[: args.limit]

    if args.chunks:
        groups = [' '.join(missing[i :: args.chunks]) for i in range(args.chunks)]
        print(json.dumps([group for group in groups if group]))
    else:
        print(' '.join(missing))


if __name__ == '__main__':
    main()
