
import db_manager as db
import models as m
import pandas as pd
from tqdm import tqdm
import matplotlib.pyplot as plt
import argparse 
import warnings


def calculate_and_cache_analytics():
    """
    Loads all 'curated_options', calculates IV and Greeks for each,
    and saves the results to a new table 'analytics_data'.
    """
    print("Loading data from 'curated_options'...")
    options_df = db.load_from_db("SELECT * FROM curated_options")
    
    if options_df.empty:
        print("No data in 'curated_options'. Run pipeline first.")
        return

    warnings.filterwarnings('ignore')

    implied_vols = []
    deltas = []
    gammas = []
    vegas = []
    thetas = []

    print(f"Calculating analytics for {len(options_df)} options...")
    
    for index, row in tqdm(options_df.iterrows(), total=options_df.shape[0]):
        
        iv = m.implied_volatility(
            market_price=row['market_price'],
            S=row['S'],
            K=row['K'],
            T=row['T'],
            r=row['r'],
            option_type=row['type']
        )
        
        if iv is not None and iv > 0:
            implied_vols.append(iv)
            
            greeks = m.bsm_greeks(
                S=row['S'],
                K=row['K'],
                T=row['T'],
                r=row['r'],
                sigma=iv,
                option_type=row['type']
            )
            deltas.append(greeks['delta'])
            gammas.append(greeks['gamma'])
            vegas.append(greeks['vega'])
            thetas.append(greeks['theta'])
        else:
            implied_vols.append(None)
            deltas.append(None)
            gammas.append(None)
            vegas.append(None)
            thetas.append(None)

    print("Calculation complete. Adding to DataFrame...")

    options_df['calc_iv'] = implied_vols
    options_df['delta'] = deltas
    options_df['gamma'] = gammas
    options_df['vega'] = vegas
    options_df['theta'] = thetas

    db.save_to_db(options_df, 'analytics_data')
    
    print(f"Successfully cached {len(options_df)} rows to 'analytics_data'.")
    return options_df


def plot_volatility_smile(data_df, ticker):
    """
    Plots the Volatility Smile for a given ticker, faceted by expiration date.
    """
    print(f"Generating Volatility Smile for {ticker}...")
    
    ticker_data = data_df[data_df['ticker'] == ticker].dropna(subset=['calc_iv', 'K'])
    
    if ticker_data.empty:
        print(f"No analytics data found for {ticker}.")
        return


    expirations = sorted(ticker_data['expiration'].unique())
    expirations_to_plot = expirations[:4] 

    fig, axes = plt.subplots(
        nrows=2, 
        ncols=2, 
        figsize=(15, 10), 
        sharex=True, 
        sharey=True
    )
    fig.suptitle(f'Volatility Smile for {ticker} (IV vs. Strike)', fontsize=20)
    
    ax_list = axes.flatten()

    for i, exp_date in enumerate(expirations_to_plot):
        if i >= len(ax_list): break
        
        ax = ax_list[i]
        exp_data = ticker_data[ticker_data['expiration'] == exp_date]

        calls = exp_data[exp_data['type'] == 'call']
        ax.scatter(calls['K'], calls['calc_iv'] * 100, label='Calls', alpha=0.7)
        puts = exp_data[exp_data['type'] == 'put']
        ax.scatter(puts['K'], puts['calc_iv'] * 100, label='Puts', alpha=0.7)
        S = exp_data['S'].iloc[0]
        ax.axvline(S, color='red', linestyle='--', label=f'Stock Price (${S:.2f})')
        
        exp_str = pd.to_datetime(exp_date).strftime('%Y-%m-%d')
        T_str = exp_data['T'].iloc[0]
        ax.set_title(f'Expiration: {exp_str} (T={T_str:.3f} yrs)')
        ax.set_xlabel('Strike Price (K)')
        ax.set_ylabel('Implied Volatility (%)')
        ax.legend()
        ax.grid(True)

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    filename = f'{ticker}_vol_smile.png'
    plt.savefig(filename)
    print(f"Saved plot to {filename}")



def plot_term_structure(data_df, ticker):
    """
    Plots the Volatility Term Structure (IV vs. Time to Expiration).
    """
    print(f"Generating Volatility Term Structure for {ticker}...")
    
    ticker_data = data_df[data_df['ticker'] == ticker].dropna(subset=['calc_iv', 'T'])
    
    if ticker_data.empty:
        print(f"No analytics data found for {ticker}.")
        return
    S = ticker_data['S'].iloc[0]
    atm_data = ticker_data[
        (ticker_data['K'] > S * 0.9) & (ticker_data['K'] < S * 1.1)
    ]
    
    if atm_data.empty:
        print("No ATM options found to plot term structure.")
        return
        
    plt.figure(figsize=(12, 7))

    calls = atm_data[atm_data['type'] == 'call']
    plt.scatter(calls['T'], calls['calc_iv'] * 100, label='ATM Calls', alpha=0.7)
    puts = atm_data[atm_data['type'] == 'put']
    plt.scatter(puts['T'], puts['calc_iv'] * 100, label='ATM Puts', alpha=0.7)
    
    plt.title(f'Volatility Term Structure for {ticker} (ATM Options)', fontsize=18)
    plt.xlabel('Time to Expiration (T) in Years')
    plt.ylabel('Implied Volatility (%)')
    
    avg_iv_by_T = atm_data.groupby('T')['calc_iv'].mean()
    plt.plot(avg_iv_by_T.index, avg_iv_by_T.values * 100, color='red', linestyle='--', label='Average IV')
    
    plt.legend()
    plt.grid(True)
    filename = f'{ticker}_term_structure.png'
    plt.savefig(filename)
    print(f"Saved plot to {filename}")


def main():
    """
    Main function to run the CLI.
    """
    parser = argparse.ArgumentParser(description="Options Analytics & Plotting Tool")
    parser.add_argument(
        '--action', 
        required=True, 
        choices=['calculate', 'plot', 'all'], 
        help="Action to perform: 'calculate' (run IV/Greeks), 'plot', or 'all'"
    )
    parser.add_argument(
        '--ticker', 
        default='SPY', 
        help="Ticker symbol to plot (e.g., AAPL, SPY)"
    )
    
    args = parser.parse_args()
    
    analytics_df = None
    if args.action == 'calculate' or args.action == 'all':
        analytics_df = calculate_and_cache_analytics()
    if args.action == 'plot' or args.action == 'all':
        if analytics_df is None:
            print("Loading cached data from 'analytics_data'...")
            analytics_df = db.load_from_db("SELECT * FROM analytics_data")
            
            if analytics_df.empty:
                print("Cache is empty. Run with --action=calculate first.")
                return
        plot_volatility_smile(analytics_df, args.ticker)
        plot_term_structure(analytics_df, args.ticker)

if __name__ == "__main__":
    main()