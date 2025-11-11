
import models as m
import time
import pandas as pd

def run_convergence_test():
    """
    Validates the CRR Binomial pricer against the BSM pricer
    for a European option and shows the value of an American option.
    """
    S = 100.0
    K = 100.0
    T = 1.0  # 1 year
    r = 0.05 # 5%
    sigma = 0.20 # 20%
    
    print("--- 1. BSM vs. CRR Convergence Test (European Call) ---")
    print(f"Parameters: S={S}, K={K}, T={T}, r={r}, sigma={sigma}\n")

    bsm_call_price = m.bsm_price(S, K, T, r, sigma, option_type='call')
    print(f"BSM Price (Target): {bsm_call_price:.6f}\n")
    N_steps = [25, 50, 100, 250, 500, 1000]
    results = []
    
    print("Running CRR Model with increasing steps (N):")
    
    for n in N_steps:
        start_time = time.time()
        
        crr_price = m.crr_binomial_pricer(
            S, K, T, r, sigma, 
            N=n, 
            option_type='call', 
            exercise_style='european'
        )
        
        end_time = time.time()
        
        results.append({
            "N_Steps": n,
            "CRR_Price": crr_price,
            "Error (CRR - BSM)": crr_price - bsm_call_price,
            "Time (sec)": end_time - start_time
        })
    results_df = pd.DataFrame(results).set_index("N_Steps")
    print(results_df.to_string(float_format="%.6f"))
    print("\nNotice how the 'Error' gets closer to 0 as N_Steps increases.")
    print("\n\n--- 2. American vs. European Put Option Value ---")
    bsm_eur_put = m.bsm_price(S, K, T, r, sigma, option_type='put')
    

    N_high = 500
    crr_eur_put = m.crr_binomial_pricer(S, K, T, r, sigma, N_high, 'put', 'european')
    crr_ame_put = m.crr_binomial_pricer(S, K, T, r, sigma, N_high, 'put', 'american')
    
    print(f"BSM European Put:   {bsm_eur_put:.6f} (BSM can't price American)")
    print(f"CRR European Put:   {crr_eur_put:.6f} (Matches BSM, as expected)")
    print(f"CRR American Put:   {crr_ame_put:.6f} (Notice this is *higher*)")
    
    early_exercise_premium = crr_ame_put - crr_eur_put
    print(f"\nValue of Early Exercise: {early_exercise_premium:.6f}")
    print("This premium is why the binomial model is necessary for American options.")

if __name__ == "__main__":
    run_convergence_test()