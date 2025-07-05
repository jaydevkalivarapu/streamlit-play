import requests
import pandas as pd
import json
from datetime import datetime

# Base URL for NSE India option chain page (for initial cookie and headers)
# This might need adjustment if NSE changes its main site structure.
# Using a general quotes page as the referer/initial visit often works.
BASE_NSE_URL = "https://www.nseindia.com/get-quotes/equity?symbol=SBIN" # Example equity page
# Actual API endpoint for index option chain
API_URL_TEMPLATE = "https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"

# Standard browser-like headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept': 'application/json, text/javascript, */*; q=0.01', # Crucial for API
    # 'Referer': BASE_NSE_URL, # Referer is often important
    'Connection': 'keep-alive',
    'X-Requested-With': 'XMLHttpRequest', # Often used by AJAX calls
}

def fetch_nse_option_data(symbol_for_nse):
    """
    Fetches option chain data for a given NSE index symbol (e.g., "NIFTY", "BANKNIFTY").

    Args:
        symbol_for_nse (str): The symbol as expected by NSE (e.g., "NIFTY").

    Returns:
        tuple: (spot_price, expiry_dates_list, all_calls_df, all_puts_df)
               Returns (None, [], pd.DataFrame(), pd.DataFrame()) on failure.
    """
    session = requests.Session()

    try:
        # Step 1: Visit a base page to initialize session and get cookies
        # Using a timeout to prevent indefinite hanging
        # The referer for the API call will be set to the actual option chain page for the symbol
        initial_page_url = f"https://www.nseindia.com/get-quotes/derivatives?symbol={symbol_for_nse}"
        if symbol_for_nse == "NIFTY": # Nifty has a slightly different quote page structure sometimes
            initial_page_url = "https://www.nseindia.com/market-data/live-equity-market" # A general market page

        # Update Referer for the session based on the symbol's likely page
        session.headers.update(HEADERS)
        session.headers.update({'Referer': initial_page_url})

        # Make an initial request to the derivatives page for the symbol to get cookies
        try:
            session.get(initial_page_url, timeout=10)
        except requests.exceptions.RequestException as e:
            print(f"Initial NSE page visit failed for {symbol_for_nse}: {e}. Proceeding with API call, might fail.")
            # It might still work if cookies are not strictly enforced or old ones are reused by session

        # Step 2: Fetch the actual option chain data from the API
        api_url = API_URL_TEMPLATE.format(symbol=symbol_for_nse)
        response = session.get(api_url, timeout=15) # Increased timeout for API call
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        data = response.json()

        if not data or 'records' not in data or not data['records']:
            print(f"No records found in NSE API response for {symbol_for_nse}")
            return None, [], pd.DataFrame(), pd.DataFrame()

        # Extract expiry dates from the records (assuming they are consistent across strikes)
        # and also the underlying value (spot price)
        expiry_dates_set = set()
        spot_price = None

        if 'data' in data['records'] and data['records']['data']:
            for record in data['records']['data']:
                expiry_dates_set.add(record['expiryDate'])
                if 'PE' in record and record['PE'] and 'underlyingValue' in record['PE']:
                    spot_price = record['PE']['underlyingValue']
                elif 'CE' in record and record['CE'] and 'underlyingValue' in record['CE']:
                    spot_price = record['CE']['underlyingValue']
            if not spot_price and data['records']['underlyingValue']: # Fallback if not in PE/CE records
                 spot_price = data['records']['underlyingValue']


        expiry_dates_list = sorted(list(expiry_dates_set), key=lambda d: datetime.strptime(d, '%d-%b-%Y'))

        all_calls_data = []
        all_puts_data = []

        if 'data' in data['records'] and data['records']['data']:
            for record in data['records']['data']:
                common_data = {'expiryDate': record['expiryDate']}
                if 'CE' in record and record['CE']:
                    ce_data = record['CE']
                    ce_data.update(common_data)
                    all_calls_data.append(ce_data)

                if 'PE' in record and record['PE']:
                    pe_data = record['PE']
                    pe_data.update(common_data)
                    all_puts_data.append(pe_data)

        calls_df = pd.DataFrame(all_calls_data)
        puts_df = pd.DataFrame(all_puts_data)

        # Standardize column names if possible (e.g., 'openInterest', 'strikePrice')
        # NSE uses camelCase, so we might want to convert to a more Pythonic snake_case or keep as is.
        # For now, keeping as is from NSE.

        return spot_price, expiry_dates_list, calls_df, puts_df

    except requests.exceptions.RequestException as e:
        print(f"Request to NSE failed for {symbol_for_nse}: {e}")
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON from NSE for {symbol_for_nse}: {e}")
        print(f"Response text: {response.text[:500] if response else 'No response'}") # Log part of the response
    except Exception as e:
        print(f"An unexpected error occurred while fetching NSE data for {symbol_for_nse}: {e}")

    return None, [], pd.DataFrame(), pd.DataFrame()


if __name__ == '__main__':
    print("Fetching NIFTY Option Chain Data...")
    nifty_spot, nifty_expiries, nifty_calls, nifty_puts = fetch_nse_option_data("NIFTY")

    if nifty_spot:
        print(f"NIFTY Spot Price: {nifty_spot}")
        print(f"Available Expiry Dates: {nifty_expiries}")
        print("\nNIFTY Calls (first 5 rows):")
        print(nifty_calls.head())
        print("\nNIFTY Puts (first 5 rows):")
        print(nifty_puts.head())

        # Filter for a specific expiry to test
        if nifty_expiries:
            target_expiry = nifty_expiries[0] # Take the first expiry
            print(f"\n--- Data for expiry: {target_expiry} ---")

            nifty_calls_expiry = nifty_calls[nifty_calls['expiryDate'] == target_expiry]
            nifty_puts_expiry = nifty_puts[nifty_puts['expiryDate'] == target_expiry]

            print(f"\nNIFTY Calls for {target_expiry} (first 5):")
            print(nifty_calls_expiry[['strikePrice', 'openInterest', 'lastPrice', 'underlyingValue']].head())

            print(f"\nNIFTY Puts for {target_expiry} (first 5):")
            print(nifty_puts_expiry[['strikePrice', 'openInterest', 'lastPrice', 'underlyingValue']].head())

    else:
        print("Failed to fetch NIFTY data.")

    print("\n\nFetching BANKNIFTY Option Chain Data...")
    banknifty_spot, banknifty_expiries, banknifty_calls, banknifty_puts = fetch_nse_option_data("BANKNIFTY")
    if banknifty_spot:
        print(f"BANKNIFTY Spot Price: {banknifty_spot}")
        # print(f"Available Expiry Dates: {banknifty_expiries}")
        print("\nBANKNIFTY Calls (first 5 rows):")
        print(banknifty_calls.head())
        # print("\nBANKNIFTY Puts (first 5 rows):")
        # print(banknifty_puts.head())
    else:
        print("Failed to fetch BANKNIFTY data.")
