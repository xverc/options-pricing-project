import yfinance as yf
import pandas as pd
from datetime import date

def fetch_options_data(ticker_symbol):
    """Fetches all option chains for a given ticker from yfinance."""
    
    ticker = yf.Ticker(ticker_symbol)

    expirations = ticker.options
    
    all_options_data = []

    for exp in expirations:
        try:
            opt_chain = ticker.option_chain(exp)
            opt_chain.calls['expiration_date'] = exp
            opt_chain.calls['option_type'] = 'call'
            opt_chain.puts['expiration_date'] = exp
            opt_chain.puts['option_type'] = 'put'
            
            all_options_data.append(opt_chain.calls)
            all_options_data.append(opt_chain.puts)
        
        except Exception as e:
            print(f"Warning: Could not fetch chain for {ticker_symbol} exp {exp}. Error: {e}")
            

    if not all_options_data:
        print(f"No options data found for {ticker_symbol}.")
        return pd.DataFrame() 
        
    master_df = pd.concat(all_options_data)
    master_df['ticker'] = ticker_symbol

    try:
        underlying_price = ticker.fast_info['lastPrice']
    except Exception:
        hist = ticker.history(period="1d")
        if not hist.empty:
            underlying_price = hist['Close'].iloc[0]
        else:
            underlying_price = None
            print(f"Warning: Could not get underlying price for {ticker_symbol}.")

    master_df['underlying_price'] = underlying_price
    master_df['fetch_timestamp'] = pd.Timestamp.now()
    
    return master_df

if __name__ == "__main__":
    print("Testing fetch_options_data...")
    spy_data = fetch_options_data("SPY")
    if not spy_data.empty:
        print(f"Successfully fetched {len(spy_data)} contracts for SPY.")
        print(spy_data.head())
    else:
        print("Test fetch failed or returned no data.")