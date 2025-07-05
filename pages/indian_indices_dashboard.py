import streamlit as st
import yfinance as yf
import pandas as pd
import sys
import os

# Ensure the root directory is in sys.path for module imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from data_fetcher import get_stock_data
from nse_scraper import fetch_nse_option_data # Import the new scraper

# Page Configuration
st.set_page_config(layout="wide", page_title="🇮🇳 Indian Indices Dashboard")
st.title("🇮🇳 Indian Indices & Options Dashboard")

# Define Indian indices (for yfinance historical data)
INDIAN_INDICES = {
    "NIFTY 50": "^NSEI",
    "NIFTY BANK": "^NSEBANK",
    "SENSEX": "^BSESN", # Options for SENSEX might not be available via the same NSE API path
    "NIFTY MIDCAP 100": "^CNXMIDCAP",
    "NIFTY SMALLCAP 100": "^CNXSMALLCAP"
}

# Mapping for NSE scraper symbols (main ones for options)
NSE_SYMBOL_MAP = {
    "NIFTY 50": "NIFTY",
    "NIFTY BANK": "BANKNIFTY",
    # Other indices like FINNIFTY ("FINNIFTY") could be added if scraper supports
}

st.subheader("Select an Index")
selected_index_name = st.selectbox(
    "Choose an Indian Index:",
    options=list(INDIAN_INDICES.keys()),
    index=0 # Default to the first index in the list
)

if selected_index_name:
    selected_yf_ticker = INDIAN_INDICES[selected_index_name]
    st.write(f"Displaying data for: **{selected_index_name}** (yfinance ticker: `{selected_yf_ticker}`)")

    st.markdown("---")
    st.subheader(f"Historical Price Data for {selected_index_name} (Last 1 Year)")

    with st.spinner(f"Fetching 1-year historical data for {selected_index_name}..."):
        index_data = get_stock_data(selected_yf_ticker, period="1y")

    if not index_data.empty:
        st.line_chart(index_data['Close'], use_container_width=True)
        st.subheader("Latest Day's Summary (from yfinance)")
        latest_day_data = index_data.iloc[-1][['Open', 'High', 'Low', 'Close', 'Volume']]
        latest_day_df = pd.DataFrame(latest_day_data).T
        latest_day_df.index = [index_data.index[-1].strftime('%Y-%m-%d')]
        st.dataframe(latest_day_df, use_container_width=True)
        with st.expander("View Full Historical Data Table (1 Year)"):
            st.dataframe(index_data, use_container_width=True)
    else:
        st.error(f"Could not fetch historical price data for {selected_index_name} via yfinance.")

    st.markdown("---")
    st.subheader(f"Options Data for {selected_index_name} (from NSE)")

    if selected_index_name in NSE_SYMBOL_MAP:
        nse_symbol = NSE_SYMBOL_MAP[selected_index_name]

        # Manage fetching and caching of full NSE option data in session state
        # Key by nse_symbol to allow data for multiple symbols to exist if user switches
        nse_data_key_prefix = f'nse_data_{nse_symbol}'

        # Button to explicitly refresh NSE data
        if st.button(f"🔄 Refresh Options Data for {nse_symbol} from NSE"):
            for key_suffix in ['_spot', '_expiries', '_all_calls', '_all_puts', '_symbol_loaded', '_fetch_error']:
                st.session_state.pop(f'{nse_data_key_prefix}{key_suffix}', None)

        if not st.session_state.get(f'{nse_data_key_prefix}_symbol_loaded') == nse_symbol or st.session_state.get(f'{nse_data_key_prefix}_fetch_error'):
            with st.spinner(f"Fetching full options data from NSE for {nse_symbol}..."):
                spot_price, expiry_dates_list, all_calls_df, all_puts_df = fetch_nse_option_data(nse_symbol)
                if spot_price is not None and expiry_dates_list: # Basic check for successful fetch
                    st.session_state[f'{nse_data_key_prefix}_spot'] = spot_price
                    st.session_state[f'{nse_data_key_prefix}_expiries'] = expiry_dates_list
                    st.session_state[f'{nse_data_key_prefix}_all_calls'] = all_calls_df
                    st.session_state[f'{nse_data_key_prefix}_all_puts'] = all_puts_df
                    st.session_state[f'{nse_data_key_prefix}_symbol_loaded'] = nse_symbol
                    st.session_state[f'{nse_data_key_prefix}_fetch_error'] = False # Reset error flag
                    st.success(f"Fetched options data for {nse_symbol} from NSE.")
                else:
                    st.error(f"Failed to fetch options data from NSE for {nse_symbol}. Check scraper logs or NSE connectivity.")
                    st.session_state[f'{nse_data_key_prefix}_fetch_error'] = True
                    # Ensure keys exist with default empty values to prevent errors downstream
                    st.session_state.setdefault(f'{nse_data_key_prefix}_spot', None)
                    st.session_state.setdefault(f'{nse_data_key_prefix}_expiries', [])
                    st.session_state.setdefault(f'{nse_data_key_prefix}_all_calls', pd.DataFrame())
                    st.session_state.setdefault(f'{nse_data_key_prefix}_all_puts', pd.DataFrame())


        # Proceed if data is loaded for the current symbol and no fetch error
        if st.session_state.get(f'{nse_data_key_prefix}_symbol_loaded') == nse_symbol and not st.session_state.get(f'{nse_data_key_prefix}_fetch_error'):
            spot_price = st.session_state[f'{nse_data_key_prefix}_spot']
            expiry_dates = st.session_state[f'{nse_data_key_prefix}_expiries']
            all_calls_df_for_symbol = st.session_state[f'{nse_data_key_prefix}_all_calls']
            all_puts_df_for_symbol = st.session_state[f'{nse_data_key_prefix}_all_puts']

            st.metric(label=f"{nse_symbol} Spot Price (from NSE)", value=f"{spot_price:,.2f}" if spot_price else "N/A")

            if not expiry_dates:
                st.warning(f"No option expiry dates found for {selected_index_name} via NSE scraper.")
            else:
                selected_expiry_date = st.selectbox(
                    "Select Option Expiry Date:",
                    options=expiry_dates,
                    index=0 # Default to first expiry
                )

                if selected_expiry_date:
                    st.write(f"Data for Expiry: **{selected_expiry_date}**")

                    calls_df_expiry = all_calls_df_for_symbol[all_calls_df_for_symbol['expiryDate'] == selected_expiry_date]
                    puts_df_expiry = all_puts_df_for_symbol[all_puts_df_for_symbol['expiryDate'] == selected_expiry_date]

                    # Store current selection for potential reuse by plots if needed, though direct passing is fine too
                    st.session_state.current_nse_calls_expiry_df = calls_df_expiry
                    st.session_state.current_nse_puts_expiry_df = puts_df_expiry

                    if not calls_df_expiry.empty or not puts_df_expiry.empty:
                        tab_call, tab_put = st.tabs(["📞 Calls", "📝 Puts"])

                        # Common NSE columns: strikePrice, expiryDate, underlying, identifier, openInterest, changeinOpenInterest,
                        # pChangeinOpenInterest, totalTradedVolume, lastPrice, change, pChange, totalBuyQuantity, totalSellQuantity,
                        # bidQty, bidprice, askQty, askPrice, underlyingValue
                        # Prioritizing Open Interest and key price/volume metrics
                        relevant_cols = ['strikePrice', 'openInterest', 'lastPrice', 'totalTradedVolume', 'change', 'impliedVolatility', 'bidPrice', 'askPrice']

                        with tab_call:
                            st.subheader(f"Call Options")
                            if not calls_df_expiry.empty:
                                display_cols = [col for col in relevant_cols if col in calls_df_expiry.columns]
                                st.dataframe(calls_df_expiry[display_cols], use_container_width=True)
                                with st.expander("View All Call Option Columns for this Expiry"):
                                    st.dataframe(calls_df_expiry, use_container_width=True)
                            else:
                                st.info("No call options data for this expiry.")

                        with tab_put:
                            st.subheader(f"Put Options")
                            if not puts_df_expiry.empty:
                                display_cols = [col for col in relevant_cols if col in puts_df_expiry.columns]
                                st.dataframe(puts_df_expiry[display_cols], use_container_width=True)
                                with st.expander("View All Put Option Columns for this Expiry"):
                                    st.dataframe(puts_df_expiry, use_container_width=True)
                            else:
                                st.info("No put options data for this expiry.")

                        # --- Plot Open Interest by Strike Price ---
                        st.markdown("---")
                        st.subheader("Open Interest Analysis (NSE Data)")

                        # NSE data uses 'strikePrice' and 'openInterest'
                        if 'strikePrice' in calls_df_expiry.columns and 'openInterest' in calls_df_expiry.columns and \
                           'strikePrice' in puts_df_expiry.columns and 'openInterest' in puts_df_expiry.columns:

                            call_oi_data = calls_df_expiry[['strikePrice', 'openInterest']].copy()
                            put_oi_data = puts_df_expiry[['strikePrice', 'openInterest']].copy()

                            call_oi_data['strikePrice'] = pd.to_numeric(call_oi_data['strikePrice'], errors='coerce')
                            call_oi_data['openInterest'] = pd.to_numeric(call_oi_data['openInterest'], errors='coerce').fillna(0)
                            put_oi_data['strikePrice'] = pd.to_numeric(put_oi_data['strikePrice'], errors='coerce')
                            put_oi_data['openInterest'] = pd.to_numeric(put_oi_data['openInterest'], errors='coerce').fillna(0)

                            # Rename for merge clarity
                            call_oi_data = call_oi_data.rename(columns={'openInterest': 'Call OI'})
                            put_oi_data = put_oi_data.rename(columns={'openInterest': 'Put OI'})

                            oi_by_strike = pd.merge(call_oi_data, put_oi_data, on='strikePrice', how='outer').fillna(0)
                            oi_by_strike = oi_by_strike.sort_values(by='strikePrice').set_index('strikePrice')

                            if not oi_by_strike.empty:
                                st.bar_chart(oi_by_strike[['Call OI', 'Put OI']], use_container_width=True)
                                with st.expander("View Open Interest Data Table (by Strike)"):
                                    st.dataframe(oi_by_strike, use_container_width=True)

                                total_call_oi_merged = oi_by_strike['Call OI'].sum()
                                total_put_oi_merged = oi_by_strike['Put OI'].sum()

                                if total_call_oi_merged > 0:
                                    pcr_oi = total_put_oi_merged / total_call_oi_merged
                                    st.metric(label=f"Put-Call Ratio (OI) for {selected_expiry_date}", value=f"{pcr_oi:.2f}")
                                else:
                                    st.metric(label=f"Put-Call Ratio (OI) for {selected_expiry_date}", value="N/A (Call OI is 0)")
                                st.caption(f"Total Call OI: {total_call_oi_merged:,.0f}, Total Put OI: {total_put_oi_merged:,.0f}")
                            else:
                                st.warning("Could not prepare Open Interest data from NSE for plotting.")
                        else:
                            st.warning("Required columns ('strikePrice', 'openInterest') not found in NSE options data for OI plot.")
                    else:
                        st.info("No options data available for the selected expiry to display or plot.")
        else:
             st.info(f"Options data from NSE for {nse_symbol} is currently unavailable or failed to load. Click 'Refresh' or select a different mapped index.")
    else:
        st.info(f"Options data via direct NSE scraping is not configured for '{selected_index_name}'. This feature is primarily for NIFTY and BANKNIFTY.")
else:
    st.info("Please select an index from the dropdown to view its data.")
