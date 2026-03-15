# The max dollar risk allowed by the strategy.  
MAX_RISK = 80_000

# The range of allowed Delta (absolute value) when choosing puts or calls to sell.  
# The goal is to balance low assignment risk (lower Delta) with high premiums (higher Delta).
DELTA_MIN = 0.15 
DELTA_MAX = 0.30
