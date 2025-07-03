import streamlit as st
from nlp_parser import parse_query
from data_fetcher import get_stock_data
import pandas as pd

def main():
    st.set_page_config(layout="wide") # Use wider layout
    st.title("📈 Market Trend Analyzer")

    query = st.text_input("Enter your query (e.g., 'AAPL trend last 6 months', 'Compare GOOG and MSFT ytd', 'Price of NVDA'):", placeholder="Try 'MSFT vs AAPL over 1y'")

    if st.button("Analyze Query", type="primary"):
        if query:
            st.info(f"Interpreting your query: \"{query}\"")

            parsed_result = parse_query(query)

            with st.expander("View Interpreted Query Details", expanded=False):
                st.json(parsed_result)

            tickers = parsed_result.get("tickers")
            period = parsed_result.get("period", "1y")
            intent = parsed_result.get("intent")

            if not tickers:
                st.error("⚠️ **No stock tickers identified.** Please ensure tickers are clear in your query (e.g., 'AAPL', 'MSFT').")
                st.warning("Example: 'Show trend for GOOGL and META over the last 3 months'.")
            elif intent == "unknown" and not tickers: # Should be caught by above, but as a safeguard
                st.error("⚠️ **Could not understand the query.** Please try rephrasing.")
            else:
                st.subheader(f"📊 Analysis for: {', '.join(tickers)}", divider='rainbow')

                with st.spinner(f"Fetching market data for {', '.join(tickers)} for period: {period}..."):
                    fetch_period = period
                    if intent == "price" and period == "1y": # Default period from parser for "price"
                        fetch_period = "5d"

                    stock_data = get_stock_data(tickers, period=fetch_period)

                if stock_data.empty:
                    st.error(f"🚫 **Failed to fetch data.** This could be due to invalid ticker(s) ({', '.join(tickers)}), an unsupported period ({fetch_period}), or no data available. Please check and try again.")
                else:
                    st.success(f"Successfully fetched data for: {', '.join(tickers)}")

                    with st.expander("View Raw Data Table"):
                        st.dataframe(stock_data, use_container_width=True)

                    st.markdown("---") # Visual separator

                    if intent == "trend":
                        if len(tickers) == 1:
                            st.write(f"📈 **Trend for {tickers[0]}** (Close Price)")
                            if 'Close' in stock_data.columns:
                                st.line_chart(stock_data['Close'], use_container_width=True)
                            else:
                                st.warning(f"Could not find 'Close' price data for {tickers[0]} to plot the trend.")
                        else:
                            st.write(f"📈 **Trend Comparison for {', '.join(tickers)}** (Close Prices)")
                            if 'Close' in stock_data.columns and isinstance(stock_data['Close'], pd.DataFrame) and not stock_data['Close'].empty:
                                st.line_chart(stock_data['Close'], use_container_width=True)
                            elif isinstance(stock_data, pd.DataFrame) and all((('Close', ticker) in stock_data.columns for ticker in tickers)): # Check multi-index case
                                st.line_chart(stock_data['Close'][tickers], use_container_width=True)
                            else:
                                 st.warning("Could not extract comparable 'Close' price data for all tickers to plot trends.")

                    elif intent == "compare":
                        if len(tickers) > 1:
                            st.write(f"🆚 **Comparison: {', '.join(tickers)}** (Close Prices)")
                            if 'Close' in stock_data.columns and isinstance(stock_data['Close'], pd.DataFrame) and not stock_data['Close'].empty:
                                # Handles cases where 'Close' is a DataFrame (multiple tickers)
                                st.line_chart(stock_data['Close'], use_container_width=True)
                            elif isinstance(stock_data, pd.DataFrame) and all((('Close', ticker) in stock_data.columns for ticker in tickers)):
                                # Handles yfinance multi-index columns: stock_data[('Close', 'AAPL')]
                                st.line_chart(stock_data['Close'][tickers], use_container_width=True)
                            else:
                                st.warning("Could not extract comparable 'Close' price data for comparison.")
                        else:
                            st.warning("⚠️ Comparison typically requires at least two tickers. Showing trend for the single ticker instead.")
                            if 'Close' in stock_data.columns:
                                st.line_chart(stock_data['Close'], use_container_width=True)
                            elif tickers and ('Close', tickers[0]) in stock_data.columns:
                                st.line_chart(stock_data[('Close', tickers[0])], use_container_width=True)
                            else:
                                st.warning(f"Could not find 'Close' price data to plot trend for {tickers[0] if tickers else 'the ticker'}.")

                    elif intent == "price":
                        st.write(f"💲 **Latest Price Information for {', '.join(tickers)}** (fetched for period: {fetch_period})")
                        latest_data_list = []
                        processed_tickers = set()

                        for ticker in tickers:
                            if ticker in processed_tickers: continue # Skip if already processed (e.g. single ticker df)

                            ticker_df = None
                            if isinstance(stock_data.columns, pd.MultiIndex):
                                # Data for multiple tickers, select specific ticker's columns
                                if ('Close', ticker) in stock_data.columns:
                                   ticker_df = stock_data.xs(ticker, level=1, axis=1)
                            elif len(tickers) == 1 and ticker == tickers[0]: # Single ticker DataFrame
                                ticker_df = stock_data

                            if ticker_df is not None and not ticker_df.empty and 'Close' in ticker_df.columns:
                                latest_row = ticker_df.iloc[-1]
                                latest_data_list.append({
                                    "Ticker": ticker,
                                    "Date": latest_row.name.strftime('%Y-%m-%d %H:%M:%S') if isinstance(latest_row.name, pd.Timestamp) else latest_row.name,
                                    "Close": latest_row['Close'],
                                    "Open": latest_row.get('Open', 'N/A'), # Use .get for safety
                                    "High": latest_row.get('High', 'N/A'),
                                    "Low": latest_row.get('Low', 'N/A'),
                                    "Volume": latest_row.get('Volume', 'N/A')
                                })
                            else:
                                latest_data_list.append({"Ticker": ticker, "Date": "N/A", "Close": "N/A", "Error": f"Data not found or incomplete for {ticker}."})
                            processed_tickers.add(ticker)

                        if latest_data_list:
                            price_df = pd.DataFrame(latest_data_list)
                            st.dataframe(price_df.set_index("Ticker"), use_container_width=True)
                        else:
                            st.warning("Could not retrieve latest price information.")

                    elif intent == "unknown" and tickers: # Has tickers, but unclear intent
                        st.warning(f"⚠️ **Intent unclear for {', '.join(tickers)}.** Displaying default trend chart.")
                        if len(tickers) == 1 and 'Close' in stock_data.columns:
                             st.line_chart(stock_data['Close'], use_container_width=True)
                        elif 'Close' in stock_data.columns and isinstance(stock_data['Close'], pd.DataFrame) and not stock_data['Close'].empty :
                             st.line_chart(stock_data['Close'], use_container_width=True)
                        elif isinstance(stock_data, pd.DataFrame) and all((('Close', ticker) in stock_data.columns for ticker in tickers)):
                             st.line_chart(stock_data['Close'][tickers], use_container_width=True)
                        else:
                             st.warning("Could not determine default data to plot.")
                    else: # Truly unknown or other unhandled cases
                         st.error("⚠️ **Could not fully process the request.** Please try rephrasing or check ticker symbols.")


        else:
            st.warning("💡 Please enter a query in the text box above.")

if __name__ == "__main__":
    main()
