# Python Finance Info (homework)

Type a stock symbol, get the time, company name, price, and how much it changed.

    Please enter a symbol:
    ADBE
    Mon Oct 10 17:23:48 PDT 2016
    Adobe Inc. (ADBE)
    109.24 +0.60 (+0.55%)

    Please enter a symbol:

It keeps asking for symbols until you type `q` (or press Ctrl+D).

## How to run
Needs Python 3.8 or newer and an internet connection.

    ./run.sh          (macOS)

or manually:

    pip install -r requirements.txt
    python stockinfo.py

Tests (no internet needed, the network is faked):

    python test_stockinfo.py

## Which API I picked, and why
I looked at a few options for getting stock data from Python:

| Option | Key needed? | Notes |
|---|---|---|
| Yahoo Finance chart endpoint (via `requests`) | No | One request gives name, price and recent closes. Not an official, supported API, so it can change or rate-limit |
| `yfinance` package | No | Popular wrapper around Yahoo. Handy, but adds a big dependency and hides the network part this homework is about |
| Alpha Vantage | Yes (free key) | Official and documented, but the free plan allows only a few requests per day |
| Finnhub / Twelve Data | Yes (free key) | Good docs, need sign-up and key handling |

I used the Yahoo chart endpoint directly with `requests`, because the lab is about
network programming and it needs no sign-up. The price source is isolated in
`fetch_quote()`, so switching to another provider only means rewriting that
function and `parse_chart()`.

## How the numbers are worked out
- Price: Yahoo's latest regular-market price.
- Change: price minus the previous trading day's close.
- Percent: change divided by the previous close, times 100.
- `+` for an increase, `-` for a decrease (zero shows `+0.00`).

## Errors it handles (it never crashes)
| Situation | What the user sees |
|---|---|
| No internet / server unreachable | `Error: No network connection ...` |
| Request takes too long (10 s) | `Error: The request timed out ...` |
| Symbol does not exist | `Error: 'ZZZZ' is not a valid symbol.` |
| Empty or strange input (`AD BE`, `!!!`, blank) | Asks again, does not call the network |
| Too many requests (HTTP 429) | `Error: Too many requests ... try again` |
| Other HTTP errors | `Error: The data service returned HTTP nnn.` |
| Answer is not JSON or has no price | `Error: ... could not understand/read ...` |
| Anything else unexpected | `Unexpected error: ...` and the program keeps running |
| Ctrl+C / Ctrl+D | Exits quietly |

## Files
- `stockinfo.py` - the program
- `test_stockinfo.py` - 20 offline tests
- `requirements.txt` - just `requests`
- `run.sh`, `run.bat` - run scripts

## Notes
- The company name comes from Yahoo, so it may differ from the example (it says
  "Adobe Inc." now, not "Adobe Systems Incorporated").
- Numbers can be delayed. This is for homework, not for trading.
