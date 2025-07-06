import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

JOSAA_ORCR_URL = "https://josaa.admissions.nic.in/applicant/SeatAllotmentResult/CurrentORCR.aspx"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': JOSAA_ORCR_URL,
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9'
}

def fetch_josaa_orcr_data(round_no=4, institute_type="ALL", institute_name="ALL", program_name="ALL", seat_category="ALL"):
    """
    Fetches Opening and Closing Rank data from JoSAA website.

    Args:
        round_no (int): The round number (e.g., 4).
        institute_type (str): Institute type code (e.g., "ALL", specific codes).
        institute_name (str): Institute name code (e.g., "ALL", specific codes).
        program_name (str): Program name code (e.g., "ALL", specific codes).
        seat_category (str): Seat category code (e.g., "ALL", "OPEN", "EWS").

    Returns:
        pandas.DataFrame: A DataFrame containing the cleaned ORCR data, or an empty DataFrame on failure.
    """
    s = requests.Session()
    s.headers.update(HEADERS)

    try:
        # Step 1: Initial GET request to get form parameters
        print("Fetching initial JoSAA page to get form parameters...")
        response_get = s.get(JOSAA_ORCR_URL, timeout=20)
        response_get.raise_for_status()
        soup = BeautifulSoup(response_get.text, 'lxml')

        viewstate = soup.find('input', {'name': '__VIEWSTATE'})['value']
        viewstategenerator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value']
        eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})['value']

        print(f"  VIEWSTATE captured (length: {len(viewstate)})")
        # print(f"  EVENTVALIDATION captured (length: {len(eventvalidation)})")


        # Step 2: Construct POST payload
        # These are typical names for ASP.NET controls. May need adjustment if exact IDs are different.
        # Based on typical JoSAA structure:
        # ctl00$ContentPlaceHolder1$ddlroundno -> Round
        # ctl00$ContentPlaceHolder1$ddlInstype -> Institute Type
        # ctl00$ContentPlaceHolder1$ddlInstitute -> Institute (ALL can be 'ALL')
        # ctl00$ContentPlaceHolder1$ddlBranch -> Program (ALL can be 'ALL')
        # ctl00$ContentPlaceHolder1$ddlSeatType -> Seat Category/Type (ALL can be 'ALL')
        # ctl00$ContentPlaceHolder1$btnSubmit -> Submit button

        payload = {
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            '__LASTFOCUS': '',
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstategenerator,
            '__EVENTVALIDATION': eventvalidation,
            'ctl00$ContentPlaceHolder1$ddlroundno': str(round_no),
            'ctl00$ContentPlaceHolder1$ddlInstype': institute_type, # "ALL" or specific code
            'ctl00$ContentPlaceHolder1$ddlInstitute': institute_name, # "ALL" or specific code
            'ctl00$ContentPlaceHolder1$ddlBranch': program_name,    # "ALL" or specific code
            'ctl00$ContentPlaceHolder1$ddlSeatType': seat_category, # "ALL" or specific code
            'ctl00$ContentPlaceHolder1$btnSubmit': 'Submit'
        }

        print(f"Submitting POST request for Round {round_no}, InstType: {institute_type}, SeatCat: {seat_category}...")
        # Step 3: POST request to get the data
        response_post = s.post(JOSAA_ORCR_URL, data=payload, timeout=60) # Longer timeout for data retrieval
        response_post.raise_for_status()
        print("  POST request successful. Parsing HTML table...")

        # Step 4: Parse the HTML table from the response
        # pandas.read_html usually finds tables well. We might need to select the correct one if multiple exist.
        # The target table is often identified by an ID like 'ctl00_ContentPlaceHolder1_grdInstlist' or similar.
        # However, read_html is quite good. Let's try without specific attrs first.
        dfs = pd.read_html(response_post.text)

        if not dfs:
            print("  No tables found in the POST response.")
            return pd.DataFrame()

        # Assuming the main data table is one of the first ones, often the largest.
        # This might need adjustment based on actual page structure.
        # A common JoSAA table has columns like 'Institute', 'Academic Program Name', etc.
        # Let's find a table with a good number of columns, likely the data table.
        data_df = None
        for df_candidate in dfs:
            if df_candidate.shape[1] > 5: # Heuristic: actual data table has more than 5 columns
                # Check for typical column names if possible (very hard without seeing the exact HTML output)
                # For now, take the first one that looks plausible
                data_df = df_candidate
                break

        if data_df is None:
            print("  Could not identify the main data table from the parsed HTML.")
            return pd.DataFrame()

        print(f"  Successfully parsed a table with shape: {data_df.shape}")

        # Step 5: Clean the DataFrame
        if data_df.empty:
            print("  Parsed table is empty.")
            return pd.DataFrame()

        # Expected columns (actual names might vary slightly based on JoSAA HTML):
        # 'Institute', 'Academic Program Name', 'Quota', 'Seat Type', 'Gender', 'Opening Rank', 'Closing Rank'
        # The scraper might return slightly different names initially from read_html.
        # Common column names from JoSAA tables:
        # Column 0: Institute
        # Column 1: Academic Program Name
        # Column 2: Quota
        # Column 3: Seat Category (like OPEN, EWS, SC, ST, OBC-NCL, OPEN (PwD), etc.)
        # Column 4: Gender (like Gender-Neutral, Female-only (including Supernumerary))
        # Column 5: Opening Rank
        # Column 6: Closing Rank

        # Basic rename if columns are just numbered by pandas.read_html
        if all(isinstance(col, int) for col in data_df.columns):
             # Check if the number of columns is what we expect (e.g., 7)
            if data_df.shape[1] == 7:
                data_df.columns = ['Institute', 'Program', 'Quota', 'Category', 'Gender', 'OpeningRank', 'ClosingRank']
            else:
                print(f"  Parsed table has {data_df.shape[1]} columns, expected 7 for default renaming. Using raw columns.")
        else: # If columns already have names, try to standardize known ones
            # This part is tricky as exact names from read_html can vary.
            # We will rely on the user to verify and potentially map columns in the Streamlit app if needed,
            # or refine this scraper after seeing the first output.
            # For now, let's assume the column order is somewhat consistent.
            # A more robust way is to inspect the actual headers from the HTML table if possible.
            # For now, we'll do a generic rename if it's a 7-column table.
             if data_df.shape[1] == 7: # A common structure
                # Check if first row is header-like and promote it
                if data_df.iloc[0].astype(str).str.contains('Institute|Program|Quota|Rank', case=False).any():
                    print("  Promoting first row as header.")
                    data_df.columns = data_df.iloc[0]
                    data_df = data_df[1:]
                    data_df.reset_index(drop=True, inplace=True)

                # Standardize column names based on common patterns
                rename_map = {}
                for col in data_df.columns:
                    col_lower = str(col).lower()
                    if 'institute' in col_lower: rename_map[col] = 'Institute'
                    elif 'program' in col_lower: rename_map[col] = 'Program'
                    elif 'quota' in col_lower: rename_map[col] = 'Quota'
                    elif 'seat type' in col_lower or 'category' in col_lower: rename_map[col] = 'Category'
                    elif 'gender' in col_lower: rename_map[col] = 'Gender'
                    elif 'opening' in col_lower and 'rank' in col_lower: rename_map[col] = 'OpeningRank'
                    elif 'closing' in col_lower and 'rank' in col_lower: rename_map[col] = 'ClosingRank'
                data_df.rename(columns=rename_map, inplace=True)


        # Convert rank columns to numeric, coercing errors.
        # JoSAA ranks can be like '1234' or '123P' (PwD closing rank beyond general closing).
        # For '123P', the 'P' indicates it's a PwD rank. We need to decide how to treat it.
        # Option 1: Extract numeric part, add a PwD flag column.
        # Option 2: Treat '...P' as a very high number or NaN if direct comparison is needed.
        # For now, let's try to extract numeric part and store 'P' separately if needed.
        # A simpler initial approach: remove 'P' and convert.

        def clean_rank(rank_str):
            if pd.isna(rank_str):
                return None
            s = str(rank_str).strip()
            if not s: # Handle empty strings
                return None
            # Remove " (PwD)" suffix if present from some JoSAA formats
            s = s.replace(" (PwD)", "")
            if s.endswith('P'):
                # For simplicity, removing 'P' and taking the number.
                # This means '123P' becomes 123. This might not be ideal for strict comparison logic
                # without knowing the context of 'P' (e.g., if it means rank went into preparatory course).
                # For now, this is a basic conversion.
                return pd.to_numeric(s[:-1], errors='coerce')
            return pd.to_numeric(s, errors='coerce')

        if 'OpeningRank' in data_df.columns:
            data_df['OpeningRank'] = data_df['OpeningRank'].apply(clean_rank)
        if 'ClosingRank' in data_df.columns:
            data_df['ClosingRank'] = data_df['ClosingRank'].apply(clean_rank)

        # Drop rows where essential data might be missing after cleaning (e.g. ranks)
        if 'ClosingRank' in data_df.columns:
            data_df.dropna(subset=['ClosingRank', 'OpeningRank'], how='any', inplace=True)


        print("  DataFrame cleaned. Final shape:", data_df.shape)
        return data_df

    except requests.exceptions.Timeout:
        print(f"Timeout while trying to reach JoSAA website: {JOSAA_ORCR_URL}")
    except requests.exceptions.RequestException as e:
        print(f"Request to JoSAA failed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while fetching JoSAA data: {e}")

    return pd.DataFrame()


if __name__ == '__main__':
    print("Attempting to fetch JoSAA ORCR Data for Round 4 (ALL, ALL, ALL, ALL)...")
    # This will fetch ALL data, which can be very large and slow.
    # For testing, one might fetch for a specific institute type or category if the website doesn't timeout.
    # However, the plan is to fetch all and filter in pandas.

    # To make the test faster, let's try for a specific institute type.
    # Example: "NIT" (National Institute of Technology). The actual code for "NIT" might be like "101" or "I"
    # This requires knowing the <option value="..."> for "NIT" from the ddlInstype dropdown.
    # For now, sticking to "ALL" as per the plan, but be aware it's a large fetch.

    # df_josaa = fetch_josaa_orcr_data(round_no=4) # Fetch all data for Round 4

    # A more targeted test for development:
    # df_josaa = fetch_josaa_orcr_data(round_no=4, institute_type="101", seat_category="OPEN") # Example: NIT, OPEN
    # The above institute_type "101" is a guess. The actual values need to be known from the JoSAA page source for ddlInstype.
    # For the initial generic scraper, we rely on "ALL".

    df_josaa = fetch_josaa_orcr_data(round_no=4, institute_type="ALL", institute_name="ALL", program_name="ALL", seat_category="ALL")


    if not df_josaa.empty:
        print("\nJoSAA Data Fetched Successfully:")
        print(f"Shape: {df_josaa.shape}")
        print("\nFirst 5 rows:")
        print(df_josaa.head())
        print("\nLast 5 rows:")
        print(df_josaa.tail())

        print("\nInfo:")
        df_josaa.info()

        if 'Category' in df_josaa.columns:
            print("\nUnique Categories found:")
            print(df_josaa['Category'].unique())
        if 'Quota' in df_josaa.columns:
            print("\nUnique Quotas found:")
            print(df_josaa['Quota'].unique())
        if 'Gender' in df_josaa.columns:
            print("\nUnique Genders found:")
            print(df_josaa['Gender'].unique())

        # Check rank columns
        if 'OpeningRank' in df_josaa.columns and 'ClosingRank' in df_josaa.columns:
            print("\nRank columns describe:")
            print(df_josaa[['OpeningRank', 'ClosingRank']].describe())
            print("\nNulls in rank columns after cleaning:")
            print(df_josaa[['OpeningRank', 'ClosingRank']].isnull().sum())

    else:
        print("\nFailed to fetch JoSAA data or data was empty.")

    print("\n--- Scraper Test Complete ---")
