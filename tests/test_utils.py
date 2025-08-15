import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from utils import save_preset, load_preset


def test_save_and_load_preset(tmp_path, monkeypatch):
    monkeypatch.setattr('utils.PRESET_DIR', tmp_path)
    data = {
        'weights_pillars': {'wP': 1, 'wK': 2},
        'weights_core': {'Alpha': 1.0, 'Beta': 2.0},
        'filters': {'min_profit_eur': 5.0, 'max_rank': 1000},
    }
    save_preset('sample', data['weights_pillars'], data['weights_core'], data['filters'])
    loaded = load_preset('sample')
    assert loaded == data

