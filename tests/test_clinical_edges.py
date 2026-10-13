"""Regression tests for clinically important numerical and CSV edge cases."""
import csv
import math

import pytest

import homa


@pytest.mark.parametrize("bad", [0, -1, math.nan, math.inf, -math.inf, "n/a", True])
def test_reject_invalid_homa_measurements(bad):
    with pytest.raises(ValueError):
        homa.calculate_homa_ir(bad, 10)
    with pytest.raises(ValueError):
        homa.calculate_homa_b(5, bad)


def test_known_homa_pair_and_mgdl_conversion():
    measured = homa.assess_row({"glucose_mgdl": "90", "insulin_mu_u_ml": "10"})
    assert measured["homa_ir"] == 2.22
    assert measured["homa_b"] == 133.33
    assert measured["glucose_mmol"] == 5


def test_homa_b_undefined_without_losing_homa_ir():
    measured = homa.assess_row({"glucose_mmol": "3.5", "insulin_mu_u_ml": "10"})
    assert measured["homa_ir"] == 1.56
    assert measured["homa_b"] is None
    assert "homa_b_note" in measured


def test_qtc_units_and_invalid_rr():
    a = homa.calculate_qtc(qt_ms=400, hr_bpm=60)
    b = homa.calculate_qtc(qt_ms=400, rr_ms=1000)
    assert a["qtc_bazett_ms"] == a["qtc_fridericia_ms"] == 400.0
    assert b["qtc_bazett_ms"] == b["qtc_fridericia_ms"] == 400.0
    assert "error" in homa.calculate_qtc(qt_ms=400, rr_ms=0)


def test_meld_baseline_and_log_domain():
    a = homa.calculate_meld_na(0.7, 0.8, 0.9, 140, False)
    assert a["meld_na"] == 6.4
    assert "error" in homa.calculate_meld_na(1, 1, None, 140, False)
    assert "error" in homa.calculate_meld_na(1, 1, 1, float("nan"), False)


def test_do_not_fabricate_bmi_z_score():
    result = homa.calculate_bmi_z(70, 175, 240)
    assert result["bmi"] == 22.86
    assert result["z_score"] is None
    assert result["category"] == "not assessed"


def test_require_measured_platelets_and_alt():
    assert "error" in homa.calculate_apri_fib4(ast_u_l=40)
    assert "error" in homa.calculate_apri_fib4(ast_u_l=40, platelets_109=100, age_years=50)


def test_unknown_fields_do_not_return_fake_clinical_score():
    assert "error" in homa.assess_row({"value": 10, "qty": 2})
    assert "error" in homa.assess_row({"glucose_mmol": "", "insulin_mu_u_ml": "10"})


def test_csv_batch_no_corruption_of_empty_input_and_stable_fields(tmp_path):
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output.csv"
    input_path.write_text("sample,glucose_mmol,insulin_mu_u_ml\nA,5,10\nB,3.5,10\n", encoding="utf-8")
    rows = homa.process_csv(str(input_path), str(output_path))
    assert len(rows) == 2
    assert rows[1]["homa_b"] == "None"
    with output_path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames[:3] == ["sample", "glucose_mmol", "insulin_mu_u_ml"]
        assert len(list(reader)) == 2
    with pytest.raises(ValueError):
        homa.process_csv(str(input_path), str(input_path))


def test_csv_formula_injection_is_escaped(tmp_path):
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output.csv"
    input_path.write_text("sample,glucose_mmol,insulin_mu_u_ml\n=1+1,5,10\n", encoding="utf-8")
    homa.process_csv(str(input_path), str(output_path))
    with output_path.open(newline="", encoding="utf-8") as stream:
        result = next(csv.DictReader(stream))
    assert result["sample"] == "'=1+1"
