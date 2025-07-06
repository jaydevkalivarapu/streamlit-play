import streamlit as st
import pandas as pd
import sys
import os

# Ensure the root directory is in sys.path for module imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from josaa_scraper import fetch_josaa_orcr_data # Placeholder, will be created

# Page Configuration
st.set_page_config(layout="wide", page_title="🎓 JEE Rank Analyzer")
st.title("🎓 JEE Rank Analyzer")
st.caption("Analyze JoSAA Opening & Closing Ranks to find suitable engineering options.")

st.markdown("---")

# Placeholder for Data Loading section
st.subheader("Load JoSAA Data")

@st.cache_data(show_spinner="Fetching JoSAA data (Round 4)... This may take a few minutes.")
def load_josaa_data_round_4():
    """Calls the scraper to fetch JoSAA data for Round 4 and caches it."""
    print("Attempting to fetch JoSAA data via scraper...") # For server log
    df = fetch_josaa_orcr_data(round_no=4) # Default is Round 4, ALL, ALL, ALL
    if df.empty:
        print("Fetching returned empty DataFrame.")
    else:
        print(f"Fetched DataFrame with shape: {df.shape}")
    return df

# Button to trigger data loading
if st.button("Load/Refresh JoSAA Round 4 Data", key="load_josaa_data_btn"):
    # Clearing specific cache for a function is not direct with new @st.cache_data without changing its args.
    # For a true refresh, one might add a dummy parameter that changes, or clear all cache.
    # A simpler approach for now: direct call, relies on user clicking if they want a refresh.
    # Or, we can remove data from session state to ensure it re-runs and re-assigns.
    if 'josaa_df' in st.session_state:
        del st.session_state.josaa_df # Remove old data to ensure re-load if button is pressed
        st.cache_data.clear() # Clear all cached functions - might be too broad but ensures refresh for this one.
        st.info("Cache cleared. Re-fetching JoSAA data...")

    josaa_df = load_josaa_data_round_4()
    if not josaa_df.empty:
        st.session_state.josaa_df = josaa_df
        st.success(f"JoSAA Round 4 data loaded successfully! Found {len(josaa_df)} records.")
        # st.dataframe(st.session_state.josaa_df.head()) # Optional: show a preview
    else:
        st.error("Failed to load JoSAA data. The scraper might have encountered an issue. Check server logs.")
        if 'josaa_df' in st.session_state: # Ensure it's not there if load failed
            del st.session_state.josaa_df

if 'josaa_df' not in st.session_state:
    st.warning("JoSAA data not loaded. Click the button above to load it.")
else:
    st.info(f"JoSAA data (Round 4) is loaded with {len(st.session_state.josaa_df)} records.")


st.markdown("---")

# Placeholder for User Inputs section
st.subheader("Your Preferences")

# Initialize session state for inputs if they don't exist
if 'user_rank' not in st.session_state:
    st.session_state.user_rank = 10000
if 'user_category' not in st.session_state:
    st.session_state.user_category = None
if 'user_quota' not in st.session_state:
    st.session_state.user_quota = None
if 'user_gender' not in st.session_state:
    st.session_state.user_gender = 'Gender-Neutral' # Default
if 'user_programs' not in st.session_state:
    st.session_state.user_programs = []


if 'josaa_df' in st.session_state and not st.session_state.josaa_df.empty:
    josaa_df_loaded = st.session_state.josaa_df

    # --- User Inputs ---
    cols = st.columns(4)
    with cols[0]:
        st.session_state.user_rank = st.number_input(
            "Enter your Category Rank:",
            min_value=1,
            value=st.session_state.user_rank,  # Persist value
            step=1
        )

    # Dynamically populate Category options
    available_categories = sorted(josaa_df_loaded['Category'].unique().tolist()) if 'Category' in josaa_df_loaded.columns else []
    if available_categories:
        # Ensure previous selection is still valid or reset
        if st.session_state.user_category not in available_categories:
            st.session_state.user_category = available_categories[0] if available_categories else None
        with cols[1]:
            st.session_state.user_category = st.selectbox(
                "Select your Category:",
                options=available_categories,
                index=available_categories.index(st.session_state.user_category) if st.session_state.user_category in available_categories else 0
            )
    else:
        with cols[1]:
            st.text("Category: (Load data)")

    # Dynamically populate Quota options
    available_quotas = sorted(josaa_df_loaded['Quota'].unique().tolist()) if 'Quota' in josaa_df_loaded.columns else []
    if available_quotas:
        if st.session_state.user_quota not in available_quotas:
            st.session_state.user_quota = available_quotas[0] if available_quotas else None
        with cols[2]:
            st.session_state.user_quota = st.selectbox(
                "Select Quota:",
                options=available_quotas,
                index=available_quotas.index(st.session_state.user_quota) if st.session_state.user_quota in available_quotas else 0
            )
    else:
        with cols[2]:
            st.text("Quota: (Load data)")

    with cols[3]:
        st.session_state.user_gender = st.selectbox(
            "Select Gender:",
            options=['Gender-Neutral', 'Female-only (including Supernumerary)'],
            index=0 if st.session_state.user_gender == 'Gender-Neutral' else 1
        )

    # Program preference (optional)
    available_programs = sorted(josaa_df_loaded['Program'].unique().tolist()) if 'Program' in josaa_df_loaded.columns else []
    if available_programs:
        st.session_state.user_programs = st.multiselect(
            "Filter by Program(s) (Optional - leave blank for all):",
            options=available_programs,
            default=st.session_state.user_programs # Persist selection
        )
    else:
        st.text("Programs: (Load data to see options)")

    # Store inputs in session state for potential use in filtering logic (though direct use is also fine)
    # This is already done by assigning to st.session_state.input_X above.

else:
    st.info("Load JoSAA data to set your preferences.")


st.markdown("---")

# Results section
st.subheader("Matching Options")

if 'josaa_df' in st.session_state and not st.session_state.josaa_df.empty:
    filtered_df = st.session_state.josaa_df.copy()

    # Apply filters based on user input stored in session state
    user_rank = st.session_state.user_rank
    user_category = st.session_state.user_category
    user_quota = st.session_state.user_quota
    user_gender = st.session_state.user_gender
    user_programs = st.session_state.user_programs

    # 1. Filter by Category
    if user_category and 'Category' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Category'] == user_category]

    # 2. Filter by Quota
    if user_quota and 'Quota' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Quota'] == user_quota]

    # 3. Filter by Rank (ClosingRank >= User's Rank)
    # Ensure 'ClosingRank' is numeric. Scraper attempts this.
    if 'ClosingRank' in filtered_df.columns:
        # Convert user_rank to float for comparison, assuming ClosingRank is float/int
        filtered_df['ClosingRank'] = pd.to_numeric(filtered_df['ClosingRank'], errors='coerce')
        filtered_df = filtered_df[filtered_df['ClosingRank'] >= float(user_rank)]
    else:
        st.warning("Warning: 'ClosingRank' column not found. Cannot filter by rank.")

    # 4. Filter by Gender
    # This assumes the 'Gender' column from the scraper contains 'Gender-Neutral' or 'Female-only (including Supernumerary)'
    if user_gender and 'Gender' in filtered_df.columns:
        if user_gender == 'Female-only (including Supernumerary)':
            # Exact match for female-only seats
            filtered_df = filtered_df[filtered_df['Gender'] == 'Female-only (including Supernumerary)']
        elif user_gender == 'Gender-Neutral':
            # For Gender-Neutral, we typically consider seats explicitly marked Gender-Neutral.
            # Some interpretations might include Female-Only seats too if a female is searching under Gender-Neutral,
            # but JoSAA data usually distinguishes these. So, exact match for "Gender-Neutral".
            filtered_df = filtered_df[filtered_df['Gender'] == 'Gender-Neutral']
        # If 'Gender' column has other values or this logic needs refinement, it will be seen in testing.
    elif 'Gender' not in filtered_df.columns:
         st.warning("Warning: 'Gender' column not found in JoSAA data. Cannot filter by gender.")


    # 5. Filter by Program (if any selected)
    if user_programs and 'Program' in filtered_df.columns: # user_programs is a list from multiselect
        filtered_df = filtered_df[filtered_df['Program'].isin(user_programs)]

    if not filtered_df.empty:
        st.write(f"Found {len(filtered_df)} matching options based on your preferences:")

        # Sort by Closing Rank by default
        # Ensure 'ClosingRank' is numeric for sorting; it should be from previous step's coercion
        if 'ClosingRank' in filtered_df.columns:
            # Convert again just in case, or rely on previous coercion
            filtered_df['ClosingRank'] = pd.to_numeric(filtered_df['ClosingRank'], errors='coerce')
            # Handle NaNs in sorting, e.g., place them last or first depending on preference
            # For ranks, NaNs likely mean data issue or 'P' was not fully converted. Assuming NaNs are not desirable to see first.
            sorted_df = filtered_df.sort_values(by='ClosingRank', ascending=True, na_position='last')
        else:
            sorted_df = filtered_df # Cannot sort if column is missing

        # Define columns to display in the main table
        display_columns = ['Institute', 'Program', 'Quota', 'Category', 'OpeningRank', 'ClosingRank']
        # Ensure these columns exist in the dataframe
        existing_display_columns = [col for col in display_columns if col in sorted_df.columns]

        if not existing_display_columns:
            st.warning("The expected columns for display (Institute, Program, etc.) are not available in the filtered data.")
            st.dataframe(sorted_df, use_container_width=True) # Show raw if no standard columns
        else:
            st.dataframe(sorted_df[existing_display_columns], use_container_width=True)

        with st.expander("View all columns for filtered results"):
            st.dataframe(sorted_df, use_container_width=True)

    else:
        st.info("No matching options found for your current criteria. Try adjusting your preferences or rank.")

else:
    st.info("Load JoSAA data and set your preferences to see matching options.")


st.markdown("---")

# Placeholder for Results section
st.subheader("Matching Options")
st.write("Filtered and sorted college/program options will be displayed here.")

st.markdown("---")
st.info("This page is under active development. Full functionality coming soon!")
