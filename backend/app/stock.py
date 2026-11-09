"""Historical context only; never a forecast or causal earnings attribution."""
from datetime import date, timedelta
import math
import re
from app.schemas import StockContextResponse, StockPoint


def session_context(points: list[StockPoint], earnings: date, timing: str) -> tuple[date | None, date | None, float | None]:
    """Unknown timing does not permit a precise event-reaction calculation."""
    if timing == 'unknown':
        return None, None, None
    starting = earnings + timedelta(days=1) if timing == 'after_close' else earnings
    after = next((idx for idx, point in enumerate(points) if point.date >= starting), None)
    if after is None or after == 0:
        return None, None, None
    prior, current = points[after - 1], points[after]
    change = round((current.close / prior.close - 1) * 100, 2) if prior.close else None
    return current.date, prior.date, change


def get_stock(ticker: str, earnings: date, timing: str = 'unknown') -> StockContextResponse:
    if not re.fullmatch(r'[A-Za-z0-9.\-]{1,12}', ticker):
        raise ValueError('Invalid ticker')
    warning = None
    points: list[StockPoint] = []
    currency = None
    try:
        import yfinance as yf
        frame = yf.download(ticker, start=(earnings - timedelta(days=17)).isoformat(),
                            end=(earnings + timedelta(days=18)).isoformat(),
                            auto_adjust=False, progress=False, threads=False)
        if frame is not None and not frame.empty:
            for index, row in frame.iterrows():
                close, volume = row['Close'], row['Volume']
                # yfinance versions differ: MultiIndex tickers return Series.
                if hasattr(close, 'iloc'):
                    close = close.iloc[0]
                if hasattr(volume, 'iloc'):
                    volume = volume.iloc[0]
                if math.isfinite(float(close)) and math.isfinite(float(volume)):
                    points.append(StockPoint(date=index.date(), close=round(float(close), 4), volume=int(volume)))
        else:
            warning = 'No historical market data returned for the ticker and selected dates.'
    except Exception:  # yfinance raises vendor-specific network/data exceptions
        # Vendors, connectivity and optional dependencies must not crash analysis.
        warning = 'Historical stock data is temporarily unavailable. Check the ticker or connectivity.'
    first, prior, pct = session_context(points, earnings, timing)
    if timing == 'unknown':
        warning = (warning + ' ' if warning else '') + 'Announcement timing unknown; no reaction window is inferred.'
    elif not first and points:
        warning = (warning + ' ' if warning else '') + 'Could not determine an eligible comparison session.'
    return StockContextResponse(ticker=ticker.upper(), currency=currency, points=points,
                                earnings_date=earnings, market_timing=timing,
                                first_session_on_or_after_date=first,
                                previous_session_date=prior,
                                session_close_change_percent=pct, warning=warning)
