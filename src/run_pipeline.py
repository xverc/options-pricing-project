import pandas as pd
import yfinance as yf
from datetime import datetime
from data_ingestion import fetch_options_data
import db_manager as db

def fetch_risk_free_rate():
    """
    Fetches the 10-Year Treasury yield as a proxy for 'r'.
    ^TNX is the CBOE 10-Year Treasury Note Yield index.
    """
    try:
        tnx = yf.Ticker("^TNX")
        r_decimal = tnx.fast_info['lastPrice']
        
        if r_decimal is None:
            print("Could not fetch ^TNX fast_info, using history...")
            hist = tnx.history(period="1d")
            if not hist.empty:
                r_decimal = hist['Close'].iloc[0]
            else:
                raise Exception("TNX history is empty")
        
        print(f"Raw risk-free rate (10-Yr Treasury): {r_decimal}%")
        return r_decimal / 100
    
    except Exception as e:
        print(f"Warning: Could not fetch risk-free rate, using 0.04. Error: {e}")
        return 0.04 

def create_curated_table(raw_df, risk_free_rate):
    """
    Transforms raw options data into a curated table for pricing models.
    Calculates Time to Expiration (T) and adds risk-free rate (r).
    """
    if raw_df.empty:
        return pd.DataFrame()
        
    curated_df = raw_df.copy()
    curated_df['expiration_date'] = pd.to_datetime(curated_df['expiration_date'])
    curated_df['fetch_timestamp'] = pd.to_datetime(curated_df['fetch_timestamp'])
    time_delta = (curated_df['expiration_date'] + pd.DateOffset(days=1)) - curated_df['fetch_timestamp']
    curated_df['T'] = time_delta.dt.total_seconds() / (365.25 * 24 * 60 * 60)
    curated_df['r'] = risk_free_rate
    final_cols = {
        'ticker': 'ticker',
        'underlying_price': 'S',
        'strike': 'K',
        'T': 'T',
        'r': 'r',
        'option_type': 'type',
        'lastPrice': 'market_price',
        'volume': 'volume',
        'openInterest': 'open_interest',
        'impliedVolatility': 'market_iv',
        'expiration_date': 'expiration',
        'fetch_timestamp': 'fetched_at',
        'contractSymbol': 'contract_symbol'
    }
    cols_to_use = [col for col in final_cols.keys() if col in curated_df.columns]
    curated_df = curated_df[cols_to_use]
    
    curated_df = curated_df.rename(columns=final_cols)
    curated_df = curated_df[curated_df['T'] > 0].reset_index(drop=True)
    
    return curated_df

def run_full_pipeline(tickers_list):
    """
    Runs the full ETL (Extract, Transform, Load) pipeline.
    """
    print("Starting pipeline...")
    r = fetch_risk_free_rate()
    print(f"Using Risk-Free Rate (r): {r:.4f}")

    all_raw_data = []
    for ticker in tickers_list:
        print(f"Fetching data for {ticker}...")
        raw_data = fetch_options_data(ticker)
        if not raw_data.empty:
            all_raw_data.append(raw_data)
    
    if not all_raw_data:
        print("No data fetched. Exiting.")
        return

    master_raw_df = pd.concat(all_raw_data)
    print("Transforming data into curated table...")
    curated_df = create_curated_table(master_raw_df, r)
    print("Saving data to database...")
    db.save_to_db(master_raw_df, table_name='raw_options')
    db.save_to_db(curated_df, table_name='curated_options')
    
    print("Pipeline finished successfully.")
    print(f"\n--- Curated Data Head (from data/options.db) ---")
    print(db.load_from_db("SELECT * FROM curated_options LIMIT 5"))

if __name__ == "__main__":
    run_full_pipeline(tickers_list=["SPY", "AAPL", "MSFT", "NVDA"])