import db_manager as db
import models as m
import pandas as pd

def run_validation_test():
    """
    Pulls one option from the DB, calculates its IV, and validates
    the BSM pricer against the market price.
    """
    print("--- Running Pricer Validation Test ---")
    query = """
    SELECT * FROM curated_options 
    WHERE ticker = 'AAPL' 
      AND type = 'call' 
      AND T > (30.0/365.0)
    ORDER BY ABS(S - K) -- Order by "nearness" to money
    LIMIT 1
    """
    
    option_data = db.load_from_db(query)
    
    if option_data.empty:
        print("No suitable option found in DB. Try running the pipeline again.")
        return
    option = option_data.iloc[0]
    
    print(f"Loaded Option: {option['contract_symbol']}")
    print(f"Market Price: {option['market_price']}")
    print(f"S: {option['S']}, K: {option['K']}, T: {option['T']:.4f}, r: {option['r']:.4f}\n")
    print("Solving for Implied Volatility (IV)...")
    iv = m.implied_volatility(
        market_price=option['market_price'],
        S=option['S'],
        K=option['K'],
        T=option['T'],
        r=option['r'],
        option_type=option['type']
    )
    
    if iv is None:
        print("IV solver failed to converge. Exiting.")
        return

    print(f"Calculated IV: {iv:.6f} (or {iv*100:.2f}%)")
    print("Running parity check (re-pricing with our IV)...")
    
    model_price = m.bsm_price(
        S=option['S'],
        K=option['K'],
        T=option['T'],
        r=option['r'],
        sigma=iv,
        option_type=option['type']
    )
    
    print(f"  Market Price: {option['market_price']}")
    print(f"  Our BSM Price: {model_price:.6f}")
    
    price_diff = abs(option['market_price'] - model_price)
    print(f"  Price Difference: {price_diff:.8f}")
    
    if price_diff < 0.01:
        print("✅ SUCCESS: Model price matches market price. IV solver is working.")
    else:
        print("❌ WARNING: Model price is different from market price. Check calculations.")
    print("\nCalculating Greeks with our IV...")
    greeks = m.bsm_greeks(
        S=option['S'],
        K=option['K'],
        T=option['T'],
        r=option['r'],
        sigma=iv,
        option_type=option['type']
    )
    
    print(pd.Series(greeks).to_string())

if __name__ == "__main__":
    run_validation_test()