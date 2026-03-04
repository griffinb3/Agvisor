import time
import logging
import urllib.request
import json

logger = logging.getLogger(__name__)

_price_cache = {
    "data": None,
    "timestamp": 0,
}

CACHE_TTL_SECONDS = 3600

COMMODITY_SYMBOLS = {
    "Corn": "ZC=F",
    "Soybeans": "ZS=F",
    "Wheat": "ZW=F",
    "Cotton": "CT=F",
    "Rice": "ZR=F",
    "Live Cattle": "LE=F",
    "Feeder Cattle": "GF=F",
    "Lean Hogs": "HE=F",
    "Class III Milk": "DC=F",
    "Sugar": "SB=F",
}

COMMODITY_UNITS = {
    "Corn": "per bushel",
    "Soybeans": "per bushel",
    "Wheat": "per bushel",
    "Cotton": "per pound",
    "Rice": "per cwt",
    "Live Cattle": "per cwt",
    "Feeder Cattle": "per cwt",
    "Lean Hogs": "per cwt",
    "Class III Milk": "per cwt",
    "Sugar": "per pound",
}

COMMODITY_KEYWORDS = {
    "Corn": ["corn", "grain", "feed grain"],
    "Soybeans": ["soybean", "soybeans", "oilseed"],
    "Wheat": ["wheat", "winter wheat", "spring wheat", "grain"],
    "Cotton": ["cotton", "fiber"],
    "Rice": ["rice", "paddy"],
    "Live Cattle": ["cattle", "beef", "cow-calf", "cow/calf", "beef cattle", "livestock"],
    "Feeder Cattle": ["cattle", "feeder", "stocker", "beef", "livestock"],
    "Lean Hogs": ["hog", "hogs", "pork", "swine", "pig", "livestock"],
    "Class III Milk": ["dairy", "milk", "cheese"],
    "Sugar": ["sugar", "sugarcane", "sugar beet"],
}


def _fetch_prices_from_api():
    prices = {}
    symbols = list(COMMODITY_SYMBOLS.values())
    symbols_str = ",".join(symbols)

    try:
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbols_str}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; Agvisor/1.0)"
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        results = data.get("quoteResponse", {}).get("result", [])
        symbol_to_name = {v: k for k, v in COMMODITY_SYMBOLS.items()}

        for quote in results:
            symbol = quote.get("symbol", "")
            name = symbol_to_name.get(symbol)
            if name:
                price = quote.get("regularMarketPrice")
                change = quote.get("regularMarketChangePercent", 0)
                if price is not None:
                    prices[name] = {
                        "price": round(float(price), 2),
                        "change_pct": round(float(change), 2) if change else 0.0,
                        "unit": COMMODITY_UNITS.get(name, ""),
                    }
    except Exception as e:
        logger.warning(f"Yahoo Finance API failed: {e}")

    if not prices:
        try:
            for name, symbol in COMMODITY_SYMBOLS.items():
                try:
                    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1d"
                    req = urllib.request.Request(url, headers={
                        "User-Agent": "Mozilla/5.0 (compatible; Agvisor/1.0)"
                    })
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        data = json.loads(resp.read().decode())
                    meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
                    price = meta.get("regularMarketPrice")
                    prev_close = meta.get("previousClose", price)
                    if price is not None:
                        change_pct = 0.0
                        if prev_close and prev_close != 0:
                            change_pct = round(((price - prev_close) / prev_close) * 100, 2)
                        prices[name] = {
                            "price": round(float(price), 2),
                            "change_pct": change_pct,
                            "unit": COMMODITY_UNITS.get(name, ""),
                        }
                except Exception as inner_e:
                    logger.warning(f"Failed to fetch {name} ({symbol}): {inner_e}")
                    continue
        except Exception as e:
            logger.warning(f"Individual commodity fetch failed: {e}")

    return prices


def _get_cached_prices():
    now = time.time()
    if _price_cache["data"] is not None and (now - _price_cache["timestamp"]) < CACHE_TTL_SECONDS:
        return _price_cache["data"]

    prices = _fetch_prices_from_api()
    if prices:
        _price_cache["data"] = prices
        _price_cache["timestamp"] = now
    elif _price_cache["data"] is not None:
        return _price_cache["data"]

    return prices


def get_commodity_prices():
    prices = _get_cached_prices()

    if not prices:
        return "Current commodity prices are temporarily unavailable."

    lines = ["CURRENT COMMODITY PRICES:"]
    for name in COMMODITY_SYMBOLS:
        if name in prices:
            p = prices[name]
            direction = "▲" if p["change_pct"] > 0 else "▼" if p["change_pct"] < 0 else "—"
            sign = "+" if p["change_pct"] > 0 else ""
            lines.append(
                f"  {name}: ${p['price']:.2f} {p['unit']} "
                f"({direction} {sign}{p['change_pct']:.1f}%)"
            )

    return "\n".join(lines)


def get_relevant_prices(state_name, business_type):
    prices = _get_cached_prices()

    if not prices:
        return "Current commodity prices are temporarily unavailable."

    relevant_commodities = set()

    if state_name:
        try:
            from data.query import get_state_commodities as _get_state_commodities
            commodities_text = _get_state_commodities(state_name)
            if commodities_text:
                text_lower = commodities_text.lower()
                for commodity, keywords in COMMODITY_KEYWORDS.items():
                    for kw in keywords:
                        if kw in text_lower:
                            relevant_commodities.add(commodity)
                            break
        except Exception as e:
            logger.warning(f"Failed to get state commodities for relevance matching: {e}")

    if business_type:
        bt_lower = business_type.lower()
        for commodity, keywords in COMMODITY_KEYWORDS.items():
            for kw in keywords:
                if kw in bt_lower:
                    relevant_commodities.add(commodity)
                    break

    if not relevant_commodities:
        relevant_commodities = set(COMMODITY_SYMBOLS.keys())

    lines = [f"RELEVANT COMMODITY PRICES (for {state_name or 'your region'}):"]
    found_any = False
    for name in COMMODITY_SYMBOLS:
        if name in relevant_commodities and name in prices:
            p = prices[name]
            direction = "▲" if p["change_pct"] > 0 else "▼" if p["change_pct"] < 0 else "—"
            sign = "+" if p["change_pct"] > 0 else ""
            lines.append(
                f"  {name}: ${p['price']:.2f} {p['unit']} "
                f"({direction} {sign}{p['change_pct']:.1f}%)"
            )
            found_any = True

    if not found_any:
        return "Current commodity prices are temporarily unavailable."

    return "\n".join(lines)
