import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy.stats import norm

# Black-Scholes formula
def black_scholes(S, K, T, r, sigma, option_type="call"):
    """
    Calculate Black-Scholes option price.
    S: Current stock price
    K: Strike price
    T: Time to expiration (in years)
    r: Risk-free interest rate
    sigma: Implied volatility
    option_type: 'call' or 'put'
    """
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if option_type == "call":
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    elif option_type == "put":
        return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

# Define the list of stocks to analyze for optimal options trades
stocks = ["QQQ", "SPY"]

# Initialize an empty list to store option data
option_data = []

# Define the date range for expiration (70 to 100 days from today)
start_date = datetime.today() + timedelta(days=1)
end_date = datetime.today() + timedelta(days=30)

# Fetch the option chains for the defined stocks
for stock in stocks:
    ticker = yf.Ticker(stock)
    # Filter expiration dates within the desired range
    exp_dates = [date for date in ticker.options if start_date <= datetime.strptime(date, '%Y-%m-%d') <= end_date]
    
    for exp_date in exp_dates:
        options = ticker.option_chain(exp_date)
        calls = options.calls
        calls['Stock'] = stock
        calls['Expiration'] = exp_date
        option_data.append(calls)

# Concatenate all option data into a single DataFrame
all_options = pd.concat(option_data, ignore_index=True)

# Define constants for Black-Scholes model
risk_free_rate = 0.05  # Approximate 5% annual risk-free rate

# Add theoretical Black-Scholes price and profit probability
all_options["TimeToExpiration"] = all_options["Expiration"].apply(
    lambda x: (datetime.strptime(x, "%Y-%m-%d") - datetime.today()).days / 365
)
all_options["BlackScholesPrice"] = all_options.apply(
    lambda row: black_scholes(
        S=yf.Ticker(row["Stock"]).history(period="1d")["Close"].iloc[-1],
        K=row["strike"],
        T=row["TimeToExpiration"],
        r=risk_free_rate,
        sigma=row["impliedVolatility"],
        option_type="call"
    ),
    axis=1
)
all_options["ProfitabilityScale"] = all_options["BlackScholesPrice"] / all_options["lastPrice"]

# Filter options for high upside potential using profitability scale and liquidity
filtered_options = all_options[
    (all_options["volume"] > 500) &
    (all_options["impliedVolatility"] > 0.15) &
    (all_options["inTheMoney"] == False) &
    (all_options["lastPrice"] < 1.0) &
    (all_options["ProfitabilityScale"] > 1.2)  # Only options with >= 20% theoretical undervaluation
]

# Display the filtered options
print(filtered_options)

# Save the filtered options to a CSV file
current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
filename = f"filtered_options_{current_time}.csv"
filtered_options.to_csv(filename, index=False)