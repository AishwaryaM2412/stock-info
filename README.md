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

### On a Mac with VS Code (what I used)
1. Check Python: open Terminal and run `python3 --version`.
   If it is missing, install it from python.org (or `brew install python`).
2. Open the project: in VS Code choose File > Open Folder and pick the `stock`
   folder. Install the "Python" extension from Microsoft if VS Code asks.
3. Open the VS Code terminal (Terminal > New Terminal). It opens in the `stock`
   folder. Run these one at a time:

       python3 -m venv .venv
       source .venv/bin/activate
       pip install -r requirements.txt

   The prompt should now start with `(.venv)`.
4. Make VS Code use that environment: press Cmd+Shift+P, choose
   "Python: Select Interpreter", and pick the one that shows `.venv`.
   (This matters if you use the Run button.)
5. Run the program:

       python stockinfo.py

   or click the Play button at the top right of `stockinfo.py`. Type a symbol
   such as `ADBE` in the terminal and press Enter. Type `q` to quit.

Shortcut: `./run.sh` does steps 3 and 5 for you (use `bash run.sh` if you get
"permission denied").

### On Windows
Run `run.bat`, or do the same steps by hand but activate with
`.venv\Scripts\activate`.

### Tests
No internet needed (the network is faked):

    python test_stockinfo.py

It should end with `Ran 28 tests ... OK`.

### If something goes wrong
| What you see | Why | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'requests'` | The virtual environment is not active, so Python can't find `requests` | Run `source .venv/bin/activate` then `pip install -r requirements.txt`. With the Play button, select the `.venv` interpreter (step 4) |
| `No such file or directory: venv/bin/activate` | The folder is called `.venv` (with a dot) | Use `source .venv/bin/activate` |
| `command not found: python` | Not inside the virtual environment | Use `python3`, or activate `.venv` first |
| `permission denied: ./run.sh` | The script is not marked as runnable | Use `bash run.sh` |
| `Error: 'XYZ' is not a valid symbol.` | The symbol doesn't exist (check spelling, for example ADBE not ABDE) | Try another symbol |
| `Error: No network connection ...` | No internet, or a firewall is blocking it | Check your connection and try again |
| `Error: Too many requests ...` | Yahoo is rate-limiting you | Wait a minute and try again |

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
- `test_stockinfo.py` - 28 offline tests
- `requirements.txt` - just `requests`
- `run.sh`, `run.bat` - run scripts

## Notes
- The company name comes from Yahoo, so it may differ from the example (it says
  "Adobe Inc." now, not "Adobe Systems Incorporated").
- Numbers can be delayed. This is for homework, not for trading.