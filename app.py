import streamlit as st

st.set_page_config(
    page_title="Stock Analysis Suite",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Welcome to the Stock Analysis Suite!")

st.markdown("""
Select an analyzer from the sidebar to get started.

### 📊 Market Trend Analyzer
Interpret natural language queries about stock market trends and returns.
Enter queries like:
- "Show trend for AAPL over 6 months"
- "Compare MSFT and GOOGL YTD"
- "Price of NVDA"

### 🇮🇳 Indian Indices Dashboard
View major Indian stock indices and their options data.
*(Coming soon to this page - currently under development in the sidebar selection)*

""")

st.sidebar.success("Select a dashboard above.")

# Note: Streamlit automatically creates navigation to files in the 'pages' folder.
# Each file in 'pages/' becomes a new page in the sidebar.
# The filename (excluding the leading number and underscore, and with underscores replaced by spaces)
# is used as the page name in the sidebar.
# e.g., pages/1_📈_Market_Trend_Analyzer.py becomes "📈 Market Trend Analyzer"
# e.g., pages/market_trend_analyzer.py becomes "Market Trend Analyzer"
# e.g., pages/2_🇮🇳_Indian_Indices_Dashboard.py will become "🇮🇳 Indian Indices Dashboard"
