from core.crop_fit import crop_fit

RICE_LIKE = {"N": 90, "P": 42, "K": 43, "temperature": 20.9, "humidity": 82, "ph": 6.5}  # row 1 of the dataset


def test_dataset_row_matches_its_own_crop():
    r = crop_fit(RICE_LIKE, crop="rice")
    assert r["best_matches"][0]["crop"] == "rice"
    assert r["selected_crop"]["in_range"] == 6
    assert r["selected_crop"]["outside_typical_range"] == {}


def test_out_of_range_features_are_explained():
    r = crop_fit({**RICE_LIKE, "humidity": 30}, crop="rice")
    assert "humidity" in r["selected_crop"]["outside_typical_range"]


def test_crop_not_in_dataset():
    r = crop_fit(RICE_LIKE, crop="tomato")
    assert r["selected_crop"] is None and r["selected_crop_in_dataset"] is False


def test_needs_enough_readings():
    assert crop_fit({"N": 40, "P": 20})["available"] is False
