"""Probe gold price and FX rates.

Primary: Yahoo Finance (free, no API key required).
Fallback: GoldAPI / ExchangeRate-API if keys are present in .env.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import os
import requests
from utils import load_sources, make_record, save_outputs, TIMEOUT, HEADERS

YAHOO_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
GOLDAPI_BASE = "https://www.goldapi.io/api"
EXCHANGERATE_BASE = "https://v6.exchangerate-api.com/v6"


def _yahoo_quote(symbol: str) -> tuple[float | None, str | None]:
    """Fetch latest price from Yahoo Finance. Returns (price, error).

    Must use Googlebot UA — standard Mozilla UA returns 429 on this machine
    (Python 3.9 + LibreSSL 2.8.3 + local proxy 127.0.0.1:7897).
    """
    import urllib.request, urllib.parse, json as _json
    url = f"{YAHOO_BASE}/{urllib.parse.quote(symbol)}?interval=1d&range=1d"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1)",
        "Accept": "application/json, */*",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            meta = _json.loads(r.read())["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice") or meta.get("previousClose")
        return float(price), None
    except Exception as e:
        return None, str(e)


def _probe_gold_yahoo(cfg: dict) -> dict:
    symbol = cfg.get("symbol", "GC=F")
    currency = cfg.get("currency", "USD")
    url = f"{YAHOO_BASE}/{symbol}"

    price, err = _yahoo_quote(symbol)
    if err:
        return make_record("market_data", "Global", "Yahoo Finance – Gold",
                           url=url, status="failed", error=err)
    return make_record(
        "market_data", "Global", "Yahoo Finance – Gold",
        url=url,
        title=f"Gold Futures ({symbol}) in {currency}",
        summary=f"{price:.2f} {currency}/troy oz",
        extra={"symbol": symbol, "price": price, "currency": currency},
    )


def _probe_fx_yahoo(pairs: list[dict]) -> list[dict]:
    records = []
    for pair in pairs:
        symbol = pair["symbol"]
        base = pair.get("base", "USD")
        target = pair.get("target", "SGD")
        url = f"{YAHOO_BASE}/{symbol}"

        price, err = _yahoo_quote(symbol)
        if err:
            records.append(make_record("market_data", "Global", f"Yahoo Finance – FX {base}/{target}",
                                       url=url, status="failed", error=err,
                                       extra={"base": base, "target": target}))
        else:
            records.append(make_record(
                "market_data", "Global", f"Yahoo Finance – FX {base}/{target}",
                url=url,
                title=f"{base}/{target} exchange rate",
                summary=f"1 {base} = {price:.4f} {target}",
                extra={"symbol": symbol, "base": base, "target": target, "rate": price},
            ))
    return records


def _probe_gold_api(gold_key: str, cfg: dict) -> dict:
    symbol = "XAU"
    currency = cfg.get("currency", "USD")
    url = f"{GOLDAPI_BASE}/{symbol}/{currency}"
    try:
        resp = requests.get(url, headers={**HEADERS, "x-access-token": gold_key}, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return make_record("market_data", "Global", "GoldAPI",
                           url=url,
                           title=f"XAU/{currency} (GoldAPI)",
                           summary=str(data.get("price", "")),
                           extra={"raw": data})
    except Exception as e:
        return make_record("market_data", "Global", "GoldAPI",
                           url=url, status="failed", error=str(e))


def _probe_fx_api(fx_key: str, cfg: dict) -> list[dict]:
    pairs = cfg.get("pairs", [])
    records = []
    for pair in pairs:
        base, target = pair.get("base", "USD"), pair.get("target", "SGD")
        url = f"{EXCHANGERATE_BASE}/{fx_key}/latest/{base}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            rates = resp.json().get("conversion_rates", {})
            rate = rates.get(target)
            records.append(make_record(
                "market_data", "Global", "ExchangeRate-API",
                url=url,
                title=f"{base}/{target} rate",
                summary=str(rate) if rate is not None else None,
                status="success" if rate is not None else "failed",
                error=None if rate is not None else f"{target} not in response",
                extra={"base": base, "target": target, "rate": rate},
            ))
        except Exception as e:
            records.append(make_record("market_data", "Global", "ExchangeRate-API",
                                       url=url, status="failed", error=str(e),
                                       extra={"base": base, "target": target}))
    return records


def probe_market_data() -> list[dict]:
    cfg = load_sources().get("market_data", {})
    gold_key = os.getenv("GOLDAPI_API_KEY", "")
    fx_key = os.getenv("EXCHANGE_RATE_API_KEY", "")
    raw_all, normalized = [], []

    # --- Gold price ---
    gold_cfg = cfg.get("gold", {})
    provider = gold_cfg.get("provider", "yahoo_finance")
    print(f"  → Gold price [{provider}]")
    if provider == "yahoo_finance":
        rec = _probe_gold_yahoo(gold_cfg)
        raw_all.append(rec)
        normalized.append(rec)
        print(f"    [{rec['status']}] {rec.get('summary','')}")
    elif gold_key:
        rec = _probe_gold_api(gold_key, gold_cfg)
        raw_all.append(rec)
        normalized.append(rec)
        print(f"    [{rec['status']}] {rec.get('summary','')}")
    else:
        print("    GOLDAPI_API_KEY not set — skipping")
        normalized.append(make_record("market_data", "Global", "GoldAPI",
                                      url=GOLDAPI_BASE, status="skipped",
                                      error="GOLDAPI_API_KEY not configured"))

    # --- FX rates ---
    fx_cfg = cfg.get("fx", {})
    provider = fx_cfg.get("provider", "yahoo_finance")
    print(f"  → FX rates [{provider}]")
    if provider == "yahoo_finance":
        pairs = fx_cfg.get("pairs", [])
        recs = _probe_fx_yahoo(pairs)
        raw_all.extend(recs)
        normalized.extend(recs)
        for r in recs:
            print(f"    [{r['status']}] {r.get('summary','')}")
    elif fx_key:
        recs = _probe_fx_api(fx_key, fx_cfg)
        raw_all.extend(recs)
        normalized.extend(recs)
        for r in recs:
            print(f"    [{r['status']}] {r.get('title','')} = {r.get('summary','')}")
    else:
        print("    EXCHANGE_RATE_API_KEY not set — skipping")
        for pair in fx_cfg.get("pairs", []):
            normalized.append(make_record("market_data", "Global", "ExchangeRate-API",
                                          url=EXCHANGERATE_BASE, status="skipped",
                                          error="EXCHANGE_RATE_API_KEY not configured",
                                          extra=pair))

    save_outputs("market_data", raw_all, normalized)
    return normalized


if __name__ == "__main__":
    print("=== probe_market_data ===")
    results = probe_market_data()
    ok = sum(1 for r in results if r["status"] == "success")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    print(f"Done: {ok}/{len(results)} success, {skipped} skipped")
