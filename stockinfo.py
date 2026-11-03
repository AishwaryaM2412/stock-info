#!/usr/bin/env python3
"""
stockinfo.py - look up a stock symbol and print its current quote.

Output (example):
    Mon Oct 10 17:23:48 PDT 2016
    Adobe Systems Incorporated (ADBE)
    109.24 +0.60 (+0.55%)

Data source: Yahoo Finance "chart" web endpoint (no API key needed), called with
the `requests` library. Everything that talks to the network lives in
fetch_quote(); everything that interprets the answer lives in parse_chart(),
so the logic can be tested without a network connection.
"""

import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import requests

API_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; stockinfo-homework/1.0)"}
TIMEOUT_SECONDS = 10
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9.\-^=]{1,15}$")
QUIT_WORDS = {"q", "quit", "exit"}


#errors
class StockError(Exception):
    """Base class: every error we expect has a message that is safe to show."""


class InvalidSymbolError(StockError):
    pass


class NetworkError(StockError):
    pass


class DataError(StockError):
    pass


#model
@dataclass
class Quote:
    symbol: str
    name: str
    price: float
    change: float
    percent: float


#parse
def parse_chart(payload, symbol):
    """Turn Yahoo's chart JSON (already decoded) into a Quote."""
    try:
        chart = payload["chart"]
    except (KeyError, TypeError):
        raise DataError("The data service sent an answer we could not understand.")

    error = chart.get("error")
    if error:
        code = str(error.get("code", "")).lower()
        if "not found" in code:
            raise InvalidSymbolError(f"'{symbol}' is not a valid symbol.")
        raise DataError(f"The data service reported an error: {error.get('description', code)}")

    results = chart.get("result")
    if not results:
        raise InvalidSymbolError(f"'{symbol}' is not a valid symbol.")

    try:
        result = results[0]
        meta = result["meta"]
        timestamps = result.get("timestamp") or []
        closes = result["indicators"]["quote"][0].get("close") or []
    except (KeyError, IndexError, TypeError):
        raise DataError("The data service sent an answer we could not understand.")

    # Keep only the days that have a real closing price, oldest to newest.
    offset = meta.get("gmtoffset", 0) or 0
    bars = []
    for ts, close in zip(timestamps, closes):
        if close is not None:
            day = datetime.fromtimestamp(ts + offset, timezone.utc).date()
            bars.append((day, close))

    price = meta.get("regularMarketPrice")
    if price is None and bars:
        price = bars[-1][1]
    if price is None:
        raise DataError(f"No price is available for '{symbol}' right now.")

    #Previous close: if the newest daily bar is the same day as the quote, yesterday's close is the bar before it; otherwise the newest bar is it.
    prev = None
    quote_time = meta.get("regularMarketTime")
    if len(bars) >= 2 and quote_time is not None:
        quote_day = datetime.fromtimestamp(quote_time + offset, timezone.utc).date()
        prev = bars[-2][1] if bars[-1][0] == quote_day else bars[-1][1]
    elif len(bars) >= 2:
        prev = bars[-2][1]
    if prev is None:
        prev = meta.get("previousClose") or meta.get("chartPreviousClose")
    if not prev:
        raise DataError(f"Could not work out the previous close for '{symbol}'.")

    change = price - prev
    percent = change / prev * 100.0
    name = meta.get("longName") or meta.get("shortName") or symbol
    return Quote(symbol=symbol, name=name, price=price, change=change, percent=percent)


#network
def fetch_quote(symbol):
    """Download and parse one quote. Raises StockError subclasses only."""
    url = API_URL.format(symbol=symbol)
    params = {"range": "5d", "interval": "1d"}
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT_SECONDS)
    except requests.exceptions.Timeout:
        raise NetworkError("The request timed out. Check your connection and try again.")
    except requests.exceptions.ConnectionError:
        raise NetworkError("No network connection (or the server could not be reached).")
    except requests.exceptions.RequestException as exc:
        raise NetworkError(f"Network problem: {exc}")

    if response.status_code == 404:
        raise InvalidSymbolError(f"'{symbol}' is not a valid symbol.")
    if response.status_code == 429:
        raise NetworkError("Too many requests to the data service. Wait a minute and try again.")
    if response.status_code >= 400:
        raise NetworkError(f"The data service returned HTTP {response.status_code}.")

    try:
        payload = response.json()
    except ValueError:
        raise DataError("The data service sent an answer we could not read.")
    return parse_chart(payload, symbol)


#formatting
def format_now():
    """Current local date/time, like: Mon Oct 10 17:23:48 PDT 2016"""
    return time.strftime("%a %b %d %H:%M:%S %Z %Y")


def format_quote(q):
    """Two lines: 'Name (SYMBOL)' and '109.24 +0.60 (+0.55%)'."""
    return f"{q.name} ({q.symbol})\n{q.price:.2f} {q.change:+.2f} ({q.percent:+.2f}%)"


def clean_symbol(text):
    """Return an upper-case symbol, or None if the text cannot be a symbol."""
    symbol = text.strip().upper()
    return symbol if SYMBOL_PATTERN.match(symbol) else None


#main
def main():
    while True:
        print("Please enter a symbol:")
        try:
            text = input()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if text.strip().lower() in QUIT_WORDS:
            break
        symbol = clean_symbol(text)
        if symbol is None:
            print("That doesn't look like a stock symbol. Use letters and numbers, "
                  "for example ADBE (or type q to quit).\n")
            continue

        try:
            quote = fetch_quote(symbol)
        except StockError as err:
            print(f"Error: {err}\n")
            continue
        except Exception as err:  # last safety net: never crash on one bad lookup
            print(f"Unexpected error: {err}\n")
            continue

        print(format_now())
        print(format_quote(quote))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
