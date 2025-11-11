

import numpy as np
from scipy.stats import norm

#1. Core BSM Pricer

def bsm_price(S, K, T, r, sigma, option_type='call'):
    """
    Calculates the Black-Scholes-Merton price for a European option.
    
    :param S: Current stock price
    :param K: Strike price
    :param T: Time to expiration (in years)
    :param r: Risk-free interest rate
    :param sigma: Volatility (annualized)
    :param option_type: 'call' or 'put'
    :return: Price of the option
    """
    
    if T <= 0:
        if option_type == 'call':
            return max(0.0, S - K)
        elif option_type == 'put':
            return max(0.0, K - S)
    
    if sigma <= 0:
        sigma = 1e-6

    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if option_type == 'call':
        price = (S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2))
    elif option_type == 'put':
        price = (K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1))
    else:
        raise ValueError("option_type must be 'call' or 'put'")
        
    return price

#2. The Greeks

def bsm_greeks(S, K, T, r, sigma, option_type='call'):
    """
    Calculates the BSM Greeks for a European option.
    """
    
    if T <= 0:
        return {'delta': 0, 'gamma': 0, 'vega': 0, 'theta': 0, 'rho': 0}

    if sigma <= 0:
        sigma = 1e-6

    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    pdf_d1 = norm.pdf(d1)
    
    greeks = {}

    greeks['gamma'] = pdf_d1 / (S * sigma * np.sqrt(T))
    
    greeks['vega'] = (S * pdf_d1 * np.sqrt(T)) * 0.01

    if option_type == 'call':
        greeks['delta'] = norm.cdf(d1)
        greeks['theta'] = (-(S * pdf_d1 * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365.25
        greeks['rho'] = (K * T * np.exp(-r * T) * norm.cdf(d2)) * 0.01
    
    elif option_type == 'put':
        greeks['delta'] = norm.cdf(d1) - 1
        greeks['theta'] = (-(S * pdf_d1 * sigma) / (2 * np.sqrt(T)) + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365.25
        greeks['rho'] = (-K * T * np.exp(-r * T) * norm.cdf(-d2)) * 0.01
    
    else:
        raise ValueError("option_type must be 'call' or 'put'")
        
    return greeks

#3. Implied Volatility (IV) Solver

def implied_volatility(market_price, S, K, T, r, option_type='call', max_iter=100, tolerance=1e-6):
    """
    Calculates the implied volatility (IV) using the Newton-Raphson method.
    
    Finds the 'sigma' that makes the BSM price equal to the market price.
    """
    sigma = 0.5
    
    for i in range(max_iter):

        price_guess = bsm_price(S, K, T, r, sigma, option_type)
        

        greeks = bsm_greeks(S, K, T, r, sigma, option_type)
        
        vega = greeks['vega'] / 0.01 
        

        price_diff = price_guess - market_price
        
        if abs(price_diff) < tolerance:
            return sigma
            
        
        if vega == 0:
            sigma = sigma * 0.99
            continue
            
        sigma = sigma - price_diff / vega

        if sigma < 1e-3:
            sigma = 1e-3
        elif sigma > 5:
            sigma = 5

    return None

#4. CRR Binomial Tree Pricer

def crr_binomial_pricer(S, K, T, r, sigma, N, option_type='call', exercise_style='european'):
    """
    Calculates the option price using the Cox-Ross-Rubinstein (CRR) binomial tree.
    
    :param S: Current stock price
    :param K: Strike price
    :param T: Time to expiration (in years)
    :param r: Risk-free interest rate
    :param sigma: Volatility (annualized)
    :param N: Number of steps in the binomial tree (e.g., 100)
    :param option_type: 'call' or 'put'
    :param exercise_style: 'european' or 'american'
    :return: Price of the option
    """
    

    dt = T / N 
    u = np.exp(sigma * np.sqrt(dt))
    d = 1 / u
    p = (np.exp(r * dt) - d) / (u - d)
    
    discount = np.exp(-r * dt)

    #2. Build the Stock Price Tree (Forward)
    stock_prices_at_expiry = np.zeros(N + 1)
    for i in range(N + 1):
        stock_prices_at_expiry[i] = S * (u**(N - i)) * (d**i)

    #3. Calculate Option Value at Expiration (Backward)
    option_values = np.zeros(N + 1)
    if option_type == 'call':
        option_values = np.maximum(0, stock_prices_at_expiry - K)
    elif option_type == 'put':
        option_values = np.maximum(0, K - stock_prices_at_expiry)

    #4. Work Backward Through the Tree
    for step in range(N - 1, -1, -1):
        new_option_values = np.zeros(step + 1)
        
        for i in range(step + 1):
            expected_value = discount * (p * option_values[i] + (1 - p) * option_values[i + 1])
            
            if exercise_style == 'european':
                new_option_values[i] = expected_value
            
            elif exercise_style == 'american':
                
                current_stock_price = S * (u**(step - i)) * (d**i)
                
                if option_type == 'call':
                    intrinsic_value = max(0.0, current_stock_price - K)
                elif option_type == 'put':
                    intrinsic_value = max(0.0, K - current_stock_price)
                    
                new_option_values[i] = max(expected_value, intrinsic_value)
                
        option_values = new_option_values

    return option_values[0]