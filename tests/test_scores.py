import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pandas as pd
import pytest
from score import (
    compute_profits,
    compute_opportunity_score,
    aggregate_opportunities,
    compute_price_regime,
    compute_quality_metrics,
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


def test_compute_price_regime_basic():
    df = pd.DataFrame({"bb": range(1, 101)})
    reg = compute_price_regime(df, "bb")
    assert reg["BB_MA_30"] == pytest.approx(df["bb"].tail(30).mean())
    assert reg["BB_MA_90"] == pytest.approx(df["bb"].tail(90).mean())
    assert reg["BB_MA_180"] == pytest.approx(df["bb"].mean())
    assert reg["BB_MA_365"] == pytest.approx(df["bb"].mean())
    exp_std = df["bb"].std()
    assert reg["BB_STD"] == pytest.approx(exp_std)
    current = df["bb"].iloc[-1]
    z = (current - reg["BB_MA_365"]) / exp_std
    assert reg["BB_ZSCORE"] == pytest.approx(z)


def test_compute_quality_metrics():
    df = pd.DataFrame(
        {
            "Return Rate": ["5%"],
            "Reviews: Rating": [4.2],
            "Reviews: Rating Count": [120],
            "Reviews: Rating Count - 90 days avg.": [100],
        }
    )
    qm = compute_quality_metrics(df)
    assert qm["Return Rate"] == 5.0
    assert qm["Reviews: Rating"] == 4.2
    assert qm["ReviewsMomentum"] == 20
