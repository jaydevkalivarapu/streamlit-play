import streamlit as st
import yfinance as yf
import pandas as pd
import sys
import os

# Ensure the root directory is in sys.path for module imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from data_fetcher import get_stock_data

# Page Configuration
st.set_page_config(layout="wide", page_title="🇮🇳 Indian Indices Dashboard")
st.title("🇮🇳 Indian Indices & Options Dashboard")

# Define Indian indices
INDIAN_INDICES = {
    "NIFTY 50": "^NSEI",
    "NIFTY BANK": "^NSEBANK",
    "SENSEX": "^BSESN",
    "NIFTY MIDCAP 100": "^CNXMIDCAP", # Nifty Midcap 100
    "NIFTY SMALLCAP 100": "^CNXSMALLCAP" # Nifty Smallcap 100
    # Add more indices if needed and available on Yahoo Finance
}

st.subheader("Select an Index")
selected_index_name = st.selectbox(
    "Choose an Indian Index:",
    options=list(INDIAN_INDICES.keys()),
    index=0 # Default to the first index in the list
)

if selected_index_name:
    selected_ticker = INDIAN_INDICES[selected_index_name]
    st.write(f"You selected: **{selected_index_name}** (Ticker: `{selected_ticker}`)")

    st.markdown("---")
    st.subheader(f"Historical Data for {selected_index_name} (Last 1 Year)")

    with st.spinner(f"Fetching 1-year data for {selected_index_name}..."):
        index_data = get_stock_data(selected_ticker, period="1y")

    if not index_data.empty:
        # Display line chart for 'Close' price
        st.line_chart(index_data['Close'], use_container_width=True)

        # Display summary for the latest day
        st.subheader("Latest Day's Summary")
        latest_day_data = index_data.iloc[-1][['Open', 'High', 'Low', 'Close', 'Volume']]
        # Transpose for better readability or keep as series
        latest_day_df = pd.DataFrame(latest_day_data).T
        latest_day_df.index = [index_data.index[-1].strftime('%Y-%m-%d')] # Use date as index
        st.dataframe(latest_day_df, use_container_width=True)

        # Optional: Show raw data in expander
        with st.expander("View Full Historical Data Table (1 Year)"):
            st.dataframe(index_data, use_container_width=True)
    else:
        st.error(f"Could not fetch historical data for {selected_index_name} ({selected_ticker}). It might be an invalid ticker or no data is available on Yahoo Finance.")

    # Placeholder for options data (future steps)
    st.markdown("---")
    st.subheader(f"Options Data for {selected_index_name}")

    try:
        yf_ticker = yf.Ticker(selected_ticker)
        expiry_dates = yf_ticker.options

        if not expiry_dates:
            st.warning(f"No option expiry dates found for {selected_index_name} ({selected_ticker}) on Yahoo Finance.")
        else:
            selected_expiry_date = st.selectbox(
                "Select Option Expiry Date:",
                options=expiry_dates,
                index=0
            )
            st.write(f"Selected Expiry: {selected_expiry_date}")

            if selected_expiry_date:
                with st.spinner(f"Fetching options chain for {selected_index_name} (Expiry: {selected_expiry_date})..."):
                    try:
                        options_chain = yf_ticker.option_chain(selected_expiry_date)
                        # Storing fetched data in session state to avoid re-fetching if only display changes later
                        st.session_state.options_calls = options_chain.calls
                        st.session_state.options_puts = options_chain.puts

                        st.success(f"Successfully fetched options chain for {selected_expiry_date}.")

                        # Display Calls and Puts DataFrames using st.tabs
                        if 'options_calls' in st.session_state and not st.session_state.options_calls.empty and \
                           'options_puts' in st.session_state and not st.session_state.options_puts.empty:

                            call_df = st.session_state.options_calls
                            put_df = st.session_state.options_puts

                            # Define relevant columns to display, check if they exist
                            relevant_cols = ['strike', 'lastPrice', 'openInterest', 'volume', 'impliedVolatility', 'bid', 'ask', 'change', 'percentChange', 'lastTradeDate']

                            display_call_cols = [col for col in relevant_cols if col in call_df.columns]
                            display_put_cols = [col for col in relevant_cols if col in put_df.columns]

                            tab_call, tab_put = st.tabs(["📞 Calls", "📝 Puts"])

                            with tab_call:
                                st.subheader(f"Call Options for {selected_index_name} (Expiry: {selected_expiry_date})")
                                if not call_df.empty:
                                    st.dataframe(call_df[display_call_cols], use_container_width=True)
                                    with st.expander("View All Call Option Columns"):
                                        st.dataframe(call_df, use_container_width=True)
                                else:
                                    st.info("No call options data to display.")

                            with tab_put:
                                st.subheader(f"Put Options for {selected_index_name} (Expiry: {selected_expiry_date})")
                                if not put_df.empty:
                                    st.dataframe(put_df[display_put_cols], use_container_width=True)
                                    with st.expander("View All Put Option Columns"):
                                        st.dataframe(put_df, use_container_width=True)
                                else:
                                    st.info("No put options data to display.")

                            # --- Plot Open Interest by Strike Price ---
                            st.markdown("---")
                            st.subheader("Open Interest Analysis")

                            # Prepare data for OI plot
                            # Ensure 'strike' and 'openInterest' columns exist
                            if 'strike' in call_df.columns and 'openInterest' in call_df.columns and \
                               'strike' in put_df.columns and 'openInterest' in put_df.columns:

                                # Ensure strike is numeric for proper sorting/merging if needed, handle NaNs in OI
                                call_oi = call_df[['strike', 'openInterest']].copy()
                                put_oi = put_df[['strike', 'openInterest']].copy()

                                call_oi['strike'] = pd.to_numeric(call_oi['strike'], errors='coerce')
                                call_oi['openInterest'] = pd.to_numeric(call_oi['openInterest'], errors='coerce').fillna(0)
                                put_oi['strike'] = pd.to_numeric(put_oi['strike'], errors='coerce')
                                put_oi['openInterest'] = pd.to_numeric(put_oi['openInterest'], errors='coerce').fillna(0)

                                # Merge OI data by strike price
                                oi_by_strike = pd.merge(
                                    call_oi.rename(columns={'openInterest': 'Call OI'}),
                                    put_oi.rename(columns={'openInterest': 'Put OI'}),
                                    on='strike',
                                    how='outer'
                                ).fillna(0).sort_values(by='strike').set_index('strike')

                                if not oi_by_strike.empty:
                                    st.bar_chart(oi_by_strike[['Call OI', 'Put OI']], use_container_width=True)

                                    # Show data table for the OI plot in an expander
                                    with st.expander("View Open Interest Data Table (by Strike)"):
                                        st.dataframe(oi_by_strike, use_container_width=True)

                                    # --- Calculate and Display Put-Call Ratio (OI based) ---
                                    total_call_oi = call_oi['Call OI'].sum() if 'Call OI' in call_oi else 0
                                    total_put_oi = put_oi['Put OI'].sum() if 'Put OI' in put_oi else 0 # oi_by_strike sums up from individual call_oi/put_oi which might have different strikes

                                    # Re-calculate total OI from the merged table to be sure, or use individual sums before merge
                                    total_call_oi_merged = oi_by_strike['Call OI'].sum()
                                    total_put_oi_merged = oi_by_strike['Put OI'].sum()

                                    if total_call_oi_merged > 0: # Avoid division by zero
                                        pcr_oi = total_put_oi_merged / total_call_oi_merged
                                        st.metric(label=f"Put-Call Ratio (Open Interest) for {selected_expiry_date}", value=f"{pcr_oi:.2f}")
                                    else:
                                        st.metric(label=f"Put-Call Ratio (Open Interest) for {selected_expiry_date}", value="N/A (Call OI is 0)")

                                    st.caption(f"Total Call OI: {total_call_oi_merged:,.0f}, Total Put OI: {total_put_oi_merged:,.0f}")

                                else:
                                    st.warning("Could not prepare Open Interest data for plotting (e.g., data might be empty after processing). PCR calculation also skipped.")
                            else:
                                st.warning("Required columns ('strike', 'openInterest') not found in options data for OI plot. PCR calculation also skipped.")
                        else:
                            st.info("Options data was fetched but seems to be empty for Calls or Puts, skipping OI plot and PCR calculation.")

                    except Exception as e_chain:
                        st.error(f"Failed to fetch options chain for {selected_expiry_date}: {e_chain}")
                        st.session_state.options_calls = pd.DataFrame() # Ensure empty df if error
                        st.session_state.options_puts = pd.DataFrame()

    except Exception as e:
        st.error(f"An error occurred while trying to fetch option expiry dates for {selected_index_name}: {e}")
        st.info("This index might not have options data available on Yahoo Finance, or there might be a temporary issue.")


else:
    st.info("Please select an index from the dropdown to view its data.")
