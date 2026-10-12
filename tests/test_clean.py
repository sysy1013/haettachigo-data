from pipeline.clean import remove_spikes


def test_drops_isolated_fx_glitch():
    closes = {"2015-01": 1100.0, "2015-02": 0.11, "2015-03": 1105.0}
    cleaned, dropped = remove_spikes(closes)
    assert cleaned == {"2015-01": 1100.0, "2015-03": 1105.0}
    assert dropped == ["2015-02"]


def test_keeps_real_crash_when_neighbors_disagree():
    closes = {"2020-01": 855.0, "2020-02": 396.0, "2020-03": 669.0}
    cleaned, dropped = remove_spikes(closes)
    assert cleaned == closes
    assert dropped == []


def test_first_and_last_months_never_dropped():
    closes = {"2015-01": 0.11, "2015-02": 1100.0, "2015-03": 1105.0, "2015-04": 0.12}
    cleaned, dropped = remove_spikes(closes)
    assert cleaned == closes
    assert dropped == []


def test_multiple_glitches_unsorted_input():
    closes = {
        "2015-10": 0.114,
        "2015-09": 1194.0,
        "2015-11": 1155.0,
        "2015-01": 1101.0,
        "2015-02": 0.110,
        "2015-03": 1105.0,
    }
    cleaned, dropped = remove_spikes(closes)
    assert dropped == ["2015-02", "2015-10"]
    assert cleaned == {"2015-01": 1101.0, "2015-03": 1105.0, "2015-09": 1194.0, "2015-11": 1155.0}


def test_input_not_mutated():
    closes = {"2015-01": 1100.0, "2015-02": 0.11, "2015-03": 1105.0}
    snapshot = dict(closes)
    remove_spikes(closes)
    assert closes == snapshot
