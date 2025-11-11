
import streamlit as st
import pandas as pd
import db_manager as db
import matplotlib.pyplot as plt
import os

st.set_page_config(
    page_title="Options Pricing Dashboard",
    page_icon="📈",
    layout="wide"
)

@st.cache_data(ttl=3600)
def load_data():
    """Loads the cached analytics data from the database."""
    if not os.path.exists('data/options.db'):
        return None
        
    df = db.load_from_db("SELECT * FROM analytics_data")
    return df

def plot_volatility_smile(data_df, ticker):
    ticker_data = data_df[data_df['ticker'] == ticker].dropna(subset=['calc_iv', 'K'])
    if ticker_data.empty:
        st.warning(f"No analytics data found for {ticker}.")
        return None

    expirations = sorted(ticker_data['expiration'].unique())
    expirations_to_plot = expirations[:4] 

    fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(15, 10), sharex=True, sharey=True)
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
    return fig

def plot_term_structure(data_df, ticker):
    ticker_data = data_df[data_df['ticker'] == ticker].dropna(subset=['calc_iv', 'T'])
    if ticker_data.empty:
        st.warning(f"No analytics data found for {ticker}.")
        return None

    S = ticker_data['S'].iloc[0]
    atm_data = ticker_data[(ticker_data['K'] > S * 0.9) & (ticker_data['K'] < S * 1.1)]
    if atm_data.empty:
        st.warning("No ATM options found to plot term structure.")
        return None
        
    fig, ax = plt.subplots(figsize=(12, 7))
    calls = atm_data[atm_data['type'] == 'call']
    ax.scatter(calls['T'], calls['calc_iv'] * 100, label='ATM Calls', alpha=0.7)
    puts = atm_data[atm_data['type'] == 'put']
    ax.scatter(puts['T'], puts['calc_iv'] * 100, label='ATM Puts', alpha=0.7)
    avg_iv_by_T = atm_data.groupby('T')['calc_iv'].mean()
    ax.plot(avg_iv_by_T.index, avg_iv_by_T.values * 100, color='red', linestyle='--', label='Average IV')
    ax.set_title(f'Volatility Term Structure for {ticker} (ATM Options)', fontsize=18)
    ax.set_xlabel('Time to Expiration (T) in Years')
    ax.set_ylabel('Implied Volatility (%)')
    ax.legend()
    ax.grid(True)
    return fig


st.title("📈 Options Pricing & Analytics Dashboard")

data = load_data()

if data is None:
    st.error("Database not found. Please run the pipeline first: python src/run_pipeline.py")
else:
    st.header("Implied Volatility Analysis")
    
    st.sidebar.header("User Inputs")
    available_tickers = sorted(data['ticker'].unique())
    selected_ticker = st.sidebar.selectbox(
        "Select Ticker:",
        available_tickers,
        index=available_tickers.index('SPY') 
    )

    st.subheader(f"Volatility Smile for {selected_ticker}")
    smile_fig = plot_volatility_smile(data, selected_ticker)
    if smile_fig:
        st.pyplot(smile_fig)
    
    st.subheader(f"Volatility Term Structure for {selected_ticker}")
    term_fig = plot_term_structure(data, selected_ticker)
    if term_fig:
        st.pyplot(term_fig)
        
    with st.expander(f"View Raw Analytics Data for {selected_ticker}"):
        st.dataframe(data[data['ticker'] == selected_ticker].drop(columns=['ticker']))