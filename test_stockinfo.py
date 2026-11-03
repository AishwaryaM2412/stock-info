"""Offline tests: the network is replaced with fake responses."""
import io
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from unittest import mock

import requests

import stockinfo as si


def ts(y, m, d, hour=14):
    return int(datetime(y, m, d, hour, 30, tzinfo=timezone.utc).timestamp())


def chart(closes, days, price, quote_day, name="Adobe Inc.", offset=-25200):
    """Build a fake Yahoo chart payload. `days` are (y, m, d) for each close."""
    return {"chart": {"error": None, "result": [{
        "meta": {"symbol": "ADBE", "longName": name, "regularMarketPrice": price,
                 "regularMarketTime": ts(*quote_day, hour=20), "gmtoffset": offset},
        "timestamp": [ts(*d) for d in days],
        "indicators": {"quote": [{"close": closes}]},
    }]}}


class FakeResponse:
    def __init__(self, status=200, payload=None, bad_json=False):
        self.status_code = status
        self._payload = payload
        self._bad = bad_json

    def json(self):
        if self._bad:
            raise ValueError("not json")
        return self._payload


class ParseTests(unittest.TestCase):
    def test_increase(self):
        p = chart([108.64, 109.24], [(2016, 10, 7), (2016, 10, 10)], 109.24, (2016, 10, 10))
        q = si.parse_chart(p, "ADBE")
        self.assertEqual(q.name, "Adobe Inc.")
        self.assertAlmostEqual(q.change, 0.60, places=2)
        self.assertAlmostEqual(q.percent, 0.5523, places=3)
        self.assertEqual(si.format_quote(q), "Adobe Inc. (ADBE)\n109.24 +0.60 (+0.55%)")

    def test_decrease_has_minus_signs(self):
        p = chart([110.00, 108.90], [(2016, 10, 6), (2016, 10, 7)], 108.90, (2016, 10, 7))
        text = si.format_quote(si.parse_chart(p, "ADBE"))
        self.assertIn("108.90 -1.10 (-1.00%)", text)

    def test_market_open_uses_yesterday_as_previous(self):
        # newest bar is today's partial bar, quote is from today
        p = chart([100.0, 101.0, 103.0], [(2016, 10, 5), (2016, 10, 6), (2016, 10, 7)], 103.0, (2016, 10, 7))
        q = si.parse_chart(p, "ADBE")
        self.assertAlmostEqual(q.change, 2.0)

    def test_premarket_quote_is_last_close(self):
        # quote still from Friday, newest bar is Friday: previous is Thursday
        p = chart([100.0, 101.0], [(2016, 10, 6), (2016, 10, 7)], 101.0, (2016, 10, 7))
        self.assertAlmostEqual(si.parse_chart(p, "ADBE").change, 1.0)

    def test_null_closes_are_skipped(self):
        p = chart([100.0, 101.0, None], [(2016, 10, 5), (2016, 10, 6), (2016, 10, 7)], 101.0, (2016, 10, 6))
        self.assertAlmostEqual(si.parse_chart(p, "ADBE").change, 1.0)

    def test_name_falls_back_to_symbol(self):
        p = chart([1.0, 2.0], [(2016, 10, 6), (2016, 10, 7)], 2.0, (2016, 10, 7), name=None)
        self.assertEqual(si.parse_chart(p, "XYZ").name, "XYZ")

    def test_error_not_found(self):
        p = {"chart": {"result": None, "error": {"code": "Not Found", "description": "x"}}}
        with self.assertRaises(si.InvalidSymbolError):
            si.parse_chart(p, "ZZZZ")

    def test_empty_result_is_invalid_symbol(self):
        with self.assertRaises(si.InvalidSymbolError):
            si.parse_chart({"chart": {"result": [], "error": None}}, "ZZZZ")

    def test_garbage_payload(self):
        with self.assertRaises(si.DataError):
            si.parse_chart({"hello": "world"}, "ADBE")
        with self.assertRaises(si.DataError):
            si.parse_chart(None, "ADBE")

    def test_no_price(self):
        p = {"chart": {"error": None, "result": [{"meta": {}, "timestamp": [], "indicators": {"quote": [{"close": []}]}}]}}
        with self.assertRaises(si.DataError):
            si.parse_chart(p, "ADBE")


class FetchTests(unittest.TestCase):
    def good(self):
        return FakeResponse(200, chart([108.64, 109.24], [(2016, 10, 7), (2016, 10, 10)], 109.24, (2016, 10, 10)))

    def test_ok(self):
        with mock.patch("requests.get", return_value=self.good()):
            self.assertEqual(si.fetch_quote("ADBE").symbol, "ADBE")

    def test_no_network(self):
        with mock.patch("requests.get", side_effect=requests.exceptions.ConnectionError()):
            with self.assertRaisesRegex(si.NetworkError, "No network"):
                si.fetch_quote("ADBE")

    def test_timeout(self):
        with mock.patch("requests.get", side_effect=requests.exceptions.Timeout()):
            with self.assertRaisesRegex(si.NetworkError, "timed out"):
                si.fetch_quote("ADBE")

    def test_http_404_is_invalid_symbol(self):
        with mock.patch("requests.get", return_value=FakeResponse(404)):
            with self.assertRaises(si.InvalidSymbolError):
                si.fetch_quote("ZZZZ")

    def test_http_429(self):
        with mock.patch("requests.get", return_value=FakeResponse(429)):
            with self.assertRaisesRegex(si.NetworkError, "Too many"):
                si.fetch_quote("ADBE")

    def test_http_500(self):
        with mock.patch("requests.get", return_value=FakeResponse(500)):
            with self.assertRaisesRegex(si.NetworkError, "HTTP 500"):
                si.fetch_quote("ADBE")

    def test_bad_json(self):
        with mock.patch("requests.get", return_value=FakeResponse(200, bad_json=True)):
            with self.assertRaises(si.DataError):
                si.fetch_quote("ADBE")


class InputTests(unittest.TestCase):
    def test_clean_symbol(self):
        self.assertEqual(si.clean_symbol("  adbe "), "ADBE")
        self.assertEqual(si.clean_symbol("brk-b"), "BRK-B")
        self.assertEqual(si.clean_symbol("^gspc"), "^GSPC")
        for bad in ["", "   ", "AD BE", "ADBE;rm", "A" * 40, "<script>"]:
            self.assertIsNone(si.clean_symbol(bad), bad)


class MainLoopTests(unittest.TestCase):
    def run_main(self, inputs, fetch):
        out = io.StringIO()
        with mock.patch("builtins.input", side_effect=inputs), \
             mock.patch("stockinfo.fetch_quote", side_effect=fetch), \
             mock.patch("stockinfo.format_now", return_value="Mon Oct 10 17:23:48 PDT 2016"), \
             redirect_stdout(out):
            code = si.main()
        return code, out.getvalue()

    def test_good_then_bad_then_quit(self):
        q = si.Quote("ADBE", "Adobe Inc.", 109.24, 0.60, 0.55)

        def fetch(sym):
            if sym == "ZZZZ":
                raise si.InvalidSymbolError("'ZZZZ' is not a valid symbol.")
            if sym == "NONET":
                raise si.NetworkError("No network connection (or the server could not be reached).")
            if sym == "BOOM":
                raise RuntimeError("surprise")
            return q

        code, out = self.run_main(["adbe", "zzzz", "nonet", "boom", "!!!", "", "q"], fetch)
        self.assertEqual(code, 0)
        self.assertIn("Mon Oct 10 17:23:48 PDT 2016\nAdobe Inc. (ADBE)\n109.24 +0.60 (+0.55%)", out)
        self.assertIn("Error: 'ZZZZ' is not a valid symbol.", out)
        self.assertIn("Error: No network connection", out)
        self.assertIn("Unexpected error: surprise", out)
        self.assertEqual(out.count("doesn't look like a stock symbol"), 2)

    def test_ctrl_d_exits_cleanly(self):
        code, _ = self.run_main([EOFError()], lambda s: None)
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
