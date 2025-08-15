import pandas as pd


def test_prezzo_sito_fallback_missing_column():
    dfp = pd.DataFrame({"SitePriceGross": [1.0, None]}, index=[0, 1])
    fallback = dfp.get(
        "Buy Box 🚚: Current",
        pd.Series(index=dfp.index, dtype=dfp["SitePriceGross"].dtype),
    )
    assert fallback is not None
    assert fallback.index.equals(dfp.index)

    dfp["Prezzo Sito"] = dfp["SitePriceGross"].fillna(fallback)

    assert pd.isna(dfp.loc[1, "Prezzo Sito"])
