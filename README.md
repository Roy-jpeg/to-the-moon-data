# To The Moon: price data

Daily stock prices for **To The Moon**, a stock-picking game on Reddit. A
GitHub Action turns IEX's free historical exchange data into small JSON files
that the game reads.

**Data provided for free by IEX. By accessing or using IEX Historical Data, you
agree to the [IEX Historical Data Terms of Use](https://www.iex.io/legal/hist-data-terms).**

Prices are trades on the IEX exchange only (a few percent of US volume), so
they can differ slightly from the consolidated prices quoted elsewhere. They are
a reference for a game, not a basis for trading decisions.

## Files

All under `data/`:

| File | Contents |
|---|---|
| `days/<YYYY-MM-DD>.json` | Each ticker's open and close that day: the first and last regular-session round-lot trade on IEX |
| `history/<TICKER>.json` | Daily closes, oldest first, up to 400 trading days |
| `intraday/<TICKER>.json` | Five-minute closes for the last six sessions (`t` is the start of the five minutes, epoch ms) |
| `index.json` | The latest day processed |

## How it runs

- **Daily** (`.github/workflows/daily.yml`): every hour Tuesday to Saturday it
  checks IEX for the previous trading day's file, which usually appears
  overnight New York time, streams it (9 to 16 GB) without saving it, and
  commits the results.
- **Backfill** (`.github/workflows/backfill.yml`): run once by hand to fill in
  the trailing year that IEX keeps.

The tickers are listed in `tickers.txt`. Add a ticker there when the game adds
one to a theme; run the backfill again to give it history.

## Running it yourself

Python 3.11 or later, no packages needed:

```bash
python scripts/process_day.py 2026-10-09 --bars
python scripts/build.py
```
