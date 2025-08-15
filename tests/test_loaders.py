import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from loaders import load_data


def test_load_data_columns():
    df = load_data("sample_data/keepa_sample.xlsx")
    df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")]
    assert len(df.columns) >= 40
    assert not any(str(col).startswith("Unnamed") for col in df.columns)
