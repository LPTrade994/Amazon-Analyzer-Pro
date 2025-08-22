VAT_RATES = {
    'IT': 0.22,
    'DE': 0.19,
    'FR': 0.20,
    'ES': 0.21
}

SCORING_WEIGHTS = {
    'profit': 0.40,
    'velocity': 0.25,
    'competition': 0.10,
    'momentum': 0.10,
    'risk': 0.10,
    'ops': 0.05
}

DEFAULT_DISCOUNT = 0.21

# Production mode settings
DEBUG_MODE = False  # Produzione
SHOW_PROGRESS = True  # Solo indicatori essenziali

PURCHASE_STRATEGIES = [
    "Buy Box Current",
    "Amazon Current", 
    "New FBA Current",
    "New FBM Current"
]

# Cross-market markup configuration for price estimation
CROSS_MARKET_MARKUP = {
    'it': 1.0,   # Base (Italy)
    'de': 1.05,  # 5% premium (Germany)
    'fr': 1.08,  # 8% premium (France) 
    'es': 1.03   # 3% premium (Spain)
}

# Hidden costs for realistic ROI calculation
HIDDEN_COSTS = {
    'shipping_avg': 2.5,      # € Average shipping costs
    'returns_rate': 0.02,     # 2% Return rate loss
    'misc_costs': 1.0,        # € Miscellaneous costs (currency, handling, etc.)
    'storage_rate': 0.008     # 0.8% Monthly storage rate (annual ~10%)
}