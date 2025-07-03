import yfinance as yf
import pandas as pd

def get_stock_data(tickers, period="1y", interval="1d"):
    """
    Fetches historical stock data from Yahoo Finance.

    Args:
        tickers (list or str): A list of stock tickers (e.g., ['AAPL', 'GOOG']) or a single ticker string.
        period (str): The period for which to fetch data.
                        Valid periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
        interval (str): The interval of data points.
                        Valid intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
                        Note: '1m' interval is only available for the last 7 days. For longer periods,
                              use daily or weekly intervals.

    Returns:
        pandas.DataFrame: A DataFrame containing the historical data for the tickers.
                          The DataFrame will have a MultiIndex for columns if multiple tickers are fetched,
                          with levels for (Ticker, PriceType) e.g. (AAPL, Close), (MSFT, Close).
                          Returns an empty DataFrame if an error occurs or no data is found.
    """
    if not tickers:
        return pd.DataFrame()

    try:
        if isinstance(tickers, str):
            tickers = [tickers]

        data = yf.download(tickers, period=period, interval=interval, progress=False)

        if data.empty:
            print(f"No data found for tickers: {tickers} with period: {period} and interval: {interval}")
            return pd.DataFrame()

        # If only one ticker is fetched, yfinance might not return a MultiIndex for columns.
        # We can standardize it for consistency, though for single ticker trend, it's often simpler without.
        # For now, we'll return as is from yfinance, app.py will handle single vs multiple.

        return data
    except Exception as e:
        print(f"Error fetching data for {tickers}: {e}")
        return pd.DataFrame()

if __name__ == '__main__':
    # Test cases
    print("Fetching data for AAPL (1 year):")
    aapl_data = get_stock_data("AAPL", period="1y")
    if not aapl_data.empty:
        print(aapl_data.head())
        print("\n")

    print("Fetching data for MSFT (3 months):")
    msft_data = get_stock_data(["MSFT"], period="3mo")
    if not msft_data.empty:
        print(msft_data.head())
        print("\n")

    print("Fetching data for GOOG and META (YTD):")
    compare_data = get_stock_data(['GOOG', 'META'], period="ytd")
    if not compare_data.empty:
        print(compare_data.head())
        # For multiple tickers, 'Close' price is under a multi-index: e.g., compare_data[('Close', 'GOOG')]
        # or more simply, compare_data['Close'] will give closing prices for all tickers.
        if 'Close' in compare_data.columns:
             print("\nClosing prices:")
             print(compare_data['Close'].head())
        print("\n")

    print("Fetching data for an invalid ticker 'NONEXISTENTTICKER':")
    invalid_data = get_stock_data("NONEXISTENTTICKER", period="1mo")
    if invalid_data.empty:
        print("Returned empty DataFrame as expected for invalid ticker.\n")

    print("Fetching data for multiple tickers including an invalid one ['NVDA', 'INVALIDTICK']:")
    mixed_data = get_stock_data(['NVDA', 'INVALIDTICK'], period="1mo")
    if not mixed_data.empty:
        print(mixed_data.head())
        # yfinance might download data only for the valid ticker or handle errors differently.
        # Check which columns are present.
        print(f"\nColumns: {mixed_data.columns}")
        if 'NVDA' in mixed_data.columns.get_level_values(1):
             print("NVDA data fetched.")
        if 'INVALIDTICK' in mixed_data.columns.get_level_values(1):
             print("INVALIDTICK data somehow present (unexpected).")
        elif 'Close' in mixed_data and not mixed_data['Close']['INVALIDTICK'].dropna().empty:
             print("INVALIDTICK data somehow present (unexpected).")

    else:
        print("Returned empty DataFrame or partial data for mixed valid/invalid tickers.\n")

    print("Fetching data for BTC-USD (1 week, 1h interval):")
    btc_data = get_stock_data("BTC-USD", period="1wk", interval="1h")
    if not btc_data.empty:
        print(btc_data.head())
    else:
        print("Failed to fetch BTC-USD data or it was empty.")
