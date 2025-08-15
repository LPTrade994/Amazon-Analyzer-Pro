import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pandas as pd
from score import (
    compute_profits,
    compute_opportunity_score,
    aggregate_opportunities,
)


def test_compute_profits_and_opportunity_score_smoke():
    df = pd.DataFrame(
        {
            "Price_Base": [10.0] * 10,
            "BuyBoxPrice": [15.0] * 10,
            "Locale": ["IT"] * 10,
        }
    )
    result = compute_profits(df, "Price_Base", "BuyBoxPrice")
    scores = compute_opportunity_score(result, {}, {})
    assert pd.api.types.is_numeric_dtype(result["ProfitAmazonEUR"])
    assert pd.api.types.is_numeric_dtype(result["ProfitSiteEUR"])
    assert len(scores) == 10


def test_aggregate_opportunities():
    df = pd.DataFrame(
        {
            "ASIN": ["A1", "A1", "A2"],
            "Opportunity_Score": [10, 20, 15],
            "Locale (comp)": ["DE", "FR", "IT"],
        }
    )
    agg = aggregate_opportunities(df)
    assert len(agg) == 2
    a1 = agg[agg["ASIN"] == "A1"].iloc[0]
    assert a1["Opportunity_Score"] == 20
    assert a1["Best_Market"] == "FR"
