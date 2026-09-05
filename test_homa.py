"""
Tests for HOMA-IR & HOMA-B Calculator core functions.
"""
import homa as m


def test_smoke():
    r = m.assess_row({'value': 10})
    assert isinstance(r, dict)


def test_homa_ir_calculation():
    """Test HOMA-IR calculation with known values."""
    # Normal: glucose 5.0 mmol/L, insulin 5.0 μU/mL -> HOMA-IR = (5*5)/22.5 = 1.11
    result = m.calculate_homa_ir(5.0, 5.0)
    assert result["homa_ir"] == round(25.0 / 22.5, 2)
    assert result["insulin_resistance"] is False
    assert result["glucose_mmol"] == 5.0
    assert result["insulin_mu_u_ml"] == 5.0


def test_homa_ir_insulin_resistance():
    """Test HOMA-IR detects insulin resistance."""
    # Elevated: glucose 6.0 mmol/L, insulin 15.0 μU/mL -> HOMA-IR = (6*15)/22.5 = 4.0
    result = m.calculate_homa_ir(6.0, 15.0)
    assert result["homa_ir"] == 4.0
    assert result["insulin_resistance"] is True


def test_homa_b_calculation():
    """Test HOMA-B calculation with known values."""
    # glucose 5.0 mmol/L, insulin 5.0 μU/mL -> HOMA-B = (20*5)/(5-3.5) = 66.67
    result = m.calculate_homa_b(5.0, 5.0)
    assert result["homa_b"] == round(100.0 / 1.5, 2)
    assert result["glucose_mmol"] == 5.0
    assert result["insulin_mu_u_ml"] == 5.0


def test_homa_ir_invalid_input():
    """Test HOMA-IR rejects invalid inputs."""
    try:
        m.calculate_homa_ir(-1.0, 5.0)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

    try:
        m.calculate_homa_ir(5.0, 0)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_homa_b_invalid_glucose():
    """Test HOMA-B rejects glucose <= 3.5."""
    try:
        m.calculate_homa_b(3.0, 5.0)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_glucose_conversion():
    """Test mg/dL to mmol/L conversion."""
    # 90 mg/dL = 5.0 mmol/L
    result = m.convert_glucose_mgdl_to_mmol(90.0)
    assert result == 5.0

    # 180 mg/dL = 10.0 mmol/L
    result = m.convert_glucose_mgdl_to_mmol(180.0)
    assert result == 10.0


def test_assess_row_homa_ir():
    """Test assess_row with HOMA-IR inputs."""
    result = m.assess_row({"glucose_mmol": 5.0, "insulin_mu_u_ml": 5.0})
    assert "homa_ir" in result
    assert "homa_b" in result
    assert result["insulin_resistance"] is False


def test_assess_row_homa_ir_mgdl():
    """Test assess_row with glucose in mg/dL."""
    result = m.assess_row({"glucose_mgdl": 90.0, "insulin_mu_u_ml": 5.0})
    assert "homa_ir" in result
    assert result["insulin_resistance"] is False


def test_assess_row_homa_ir_with_aliases():
    """Test assess_row with alternative field names."""
    result = m.assess_row({"fasting_glucose": 5.0, "fasting_insulin": 5.0})
    assert "homa_ir" in result

    result = m.assess_row({"fasting_glucose": 5.0, "insulin": 5.0})
    assert "homa_ir" in result


def test_meld_na_calculation():
    """Test MELD-Na calculation."""
    result = m.calculate_meld_na(bilirubin=1.0, creatinine=1.0, inr=1.0, sodium=140, dialysis=False)
    assert "meld_na" in result
    assert "severity" in result


def test_qtc_calculation():
    """Test QTc calculation."""
    result = m.calculate_qtc(qt_ms=400, hr_bpm=60)
    assert "qtc_bazett_ms" in result
    assert "qtc_fridericia_ms" in result


def test_bmi_z_calculation():
    """Test BMI z-score calculation."""
    result = m.calculate_bmi_z(weight_kg=70, height_cm=175, age_months=240)
    assert "bmi" in result
    assert "z_score" in result
    assert "category" in result


def test_hba1c_conversion():
    """Test HbA1c conversion."""
    result = m.convert_hba1c(hba1c_percent=7.0)
    assert "hba1c_percent" in result
    assert "eag_mgdl" in result
    assert "eag_mmol" in result

    # Reverse conversion
    result = m.convert_hba1c(eag_mgdl=154.0)
    assert "hba1c_percent" in result


def test_apri_calculation():
    """Test APRI calculation."""
    result = m.calculate_apri_fib4(ast_u_l=80, platelets_109=200)
    assert "apri" in result
    assert "fibrosis_risk" in result


def test_fib4_calculation():
    """Test FIB-4 calculation."""
    result = m.calculate_apri_fib4(ast_u_l=80, alt_u_l=40, platelets_109=200, age_years=50)
    assert "fib4" in result
    assert "fibrosis_risk" in result


def test_calculate_score():
    """Test generic score calculation."""
    result = m.calculate_score(a=10, b=20)
    assert "score" in result
    assert "inputs" in result
    assert result["inputs"] == 2


def test_process_csv_path_validation():
    """Test that process_csv rejects null bytes in paths."""
    try:
        m.process_csv("test\x00.csv", "out.csv")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
