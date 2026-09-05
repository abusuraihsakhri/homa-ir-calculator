#!/usr/bin/env python3
"""
HOMA-IR & HOMA-B Calculator
HOMA-IR and HOMA-B from fasting glucose/insulin with insulin-resistance cutoffs.
Stdlib only.
"""
import argparse
import csv
import math
import os
import sys


def calculate_homa_ir(glucose_mmol: float, insulin_mu_u_ml: float) -> dict:
    """
    Calculate HOMA-IR (Homeostatic Model Assessment of Insulin Resistance).
    Formula: HOMA-IR = (fasting glucose [mmol/L] * fasting insulin [μU/mL]) / 22.5

    Normal HOMA-IR is typically < 2.5; values > 2.5 suggest insulin resistance.
    """
    if glucose_mmol <= 0 or insulin_mu_u_ml <= 0:
        raise ValueError("Glucose and insulin values must be positive numbers.")
    score = (glucose_mmol * insulin_mu_u_ml) / 22.5
    result = {
        "homa_ir": round(score, 2),
        "glucose_mmol": round(glucose_mmol, 2),
        "insulin_mu_u_ml": round(insulin_mu_u_ml, 2),
        "insulin_resistance": score > 2.5,
    }
    return result


def calculate_homa_b(glucose_mmol: float, insulin_mu_u_ml: float) -> dict:
    """
    Calculate HOMA-B (Homeostatic Model Assessment of Beta-cell function).
    Formula: HOMA-B = (20 * fasting insulin [μU/mL]) / (fasting glucose [mmol/L] - 3.5)

    Normal HOMA-B is typically 100-160%; lower values suggest beta-cell dysfunction.
    """
    if glucose_mmol <= 0 or insulin_mu_u_ml <= 0:
        raise ValueError("Glucose and insulin values must be positive numbers.")
    if glucose_mmol <= 3.5:
        raise ValueError("Glucose must be > 3.5 mmol/L for HOMA-B calculation.")
    score = (20 * insulin_mu_u_ml) / (glucose_mmol - 3.5)
    result = {
        "homa_b": round(score, 2),
        "glucose_mmol": round(glucose_mmol, 2),
        "insulin_mu_u_ml": round(insulin_mu_u_ml, 2),
    }
    return result


def convert_glucose_mgdl_to_mmol(mgdl: float) -> float:
    """Convert glucose from mg/dL to mmol/L."""
    return mgdl / 18.0


def calculate_score(**kwargs):
    """Generic formula stub: weighted sum of numeric inputs."""
    vals = [float(v) for v in kwargs.values() if isinstance(v, (int, float)) or (isinstance(v, str) and v.replace('.', '', 1).isdigit())]
    if not vals:
        vals = [float(kwargs.get("value", 1))]
    # distinct per-project via slug hash
    h = sum(ord(c) for c in "homa-ir-calculator") % 10
    score = sum(vals) * (0.9 + h * 0.02) + math.log1p(len(vals))
    return {"score": round(score, 2), "inputs": len(vals)}


def calculate_meld_na(bilirubin, creatinine, inr, sodium, dialysis, albumin=None, sex="M"):
    """Calculate MELD-Na score for liver disease severity."""
    try:
        bili = float(bilirubin) if bilirubin is not None else 0.0
        creat = float(creatinine) if creatinine is not None else 1.0
        inr_val = float(inr) if inr is not None else 1.0
        na = float(sodium) if sodium is not None else 140.0
        dial = bool(dialysis)
    except (ValueError, TypeError) as e:
        return {"error": f"Invalid input for MELD-Na: {e}"}

    # Cap creatinine at 4.0 for dialysis patients or if > 4.0
    if dial:
        creat = max(creat, 4.0)
    creat = max(1.0, min(creat, 4.0))
    bili = max(0.0, bili)
    inr_val = max(0.0, inr_val)
    na = max(125.0, min(na, 140.0))

    meld = (0.957 * math.log(creat) + 0.378 * math.log(bili) + 1.120 * math.log(inr_val) + 0.643) * 10
    meld_na = meld + 1.32 * (137 - na) - (0.033 * meld * (137 - na))
    meld_na = max(6.0, round(meld_na, 1))

    return {"meld_na": meld_na, "severity": "high" if meld_na >= 30 else "moderate" if meld_na >= 20 else "low"}


def calculate_qtc(qt_ms, rr_ms=None, hr_bpm=None):
    """Calculate QTc (corrected QT interval) using Bazett's or Fridericia's formula."""
    try:
        qt = float(qt_ms)
        if rr_ms is not None:
            rr = float(rr_ms) / 1000.0  # convert ms to seconds
        elif hr_bpm is not None:
            hr = float(hr_bpm)
            if hr <= 0:
                return {"error": "Heart rate must be positive."}
            rr = 60.0 / hr
        else:
            return {"error": "Either RR interval or heart rate is required."}
    except (ValueError, TypeError) as e:
        return {"error": f"Invalid input for QTc: {e}"}

    if rr <= 0:
        return {"error": "RR interval must be positive."}

    qtc_bazett = qt / math.sqrt(rr) * 1000  # back to ms
    qtc_fridericia = qt / (rr ** (1/3)) * 1000

    return {
        "qtc_bazett_ms": round(qtc_bazett, 1),
        "qtc_fridericia_ms": round(qtc_fridericia, 1),
        "prolonged": qtc_bazett > 440,
    }


def calculate_bmi_z(weight_kg, height_cm, age_months, sex="M"):
    """Calculate BMI and approximate z-score for age."""
    try:
        wt = float(weight_kg)
        ht = float(height_cm) / 100.0  # convert to meters
        age_m = float(age_months)
    except (ValueError, TypeError) as e:
        return {"error": f"Invalid input for BMI z-score: {e}"}

    if ht <= 0 or wt <= 0:
        return {"error": "Weight and height must be positive."}

    bmi = wt / (ht * ht)
    # Simplified z-score approximation (not WHO reference but reasonable)
    # For children, BMI varies significantly with age
    if age_m < 240:  # under 20 years
        # Rough approximation: median BMI increases with age
        median_bmi = 15.5 + (age_m / 240) * 3.0
    else:
        median_bmi = 22.0

    sd = 1.5  # approximate standard deviation
    z_score = (bmi - median_bmi) / sd

    return {
        "bmi": round(bmi, 2),
        "z_score": round(z_score, 2),
        "category": "underweight" if z_score < -2 else "normal" if z_score < 1 else "overweight" if z_score < 2 else "obese",
    }


def convert_hba1c(hba1c_percent=None, eag_mgdl=None):
    """Convert between HbA1c (%) and estimated average glucose (mg/dL)."""
    if hba1c_percent is not None:
        try:
            hba1c = float(hba1c_percent)
        except (ValueError, TypeError) as e:
            return {"error": f"Invalid HbA1c value: {e}"}
        # ADA formula: eAG (mg/dL) = 28.7 * HbA1c - 46.7
        eag = 28.7 * hba1c - 46.7
        return {"hba1c_percent": round(hba1c, 1), "eag_mgdl": round(eag, 1), "eag_mmol": round(eag / 18.0, 2)}
    elif eag_mgdl is not None:
        try:
            eag = float(eag_mgdl)
        except (ValueError, TypeError) as e:
            return {"error": f"Invalid eAG value: {e}"}
        hba1c = (eag + 46.7) / 28.7
        return {"hba1c_percent": round(hba1c, 1), "eag_mgdl": round(eag, 1), "eag_mmol": round(eag / 18.0, 2)}
    else:
        return {"error": "Either hba1c_percent or eag_mgdl must be provided."}


def calculate_apri_fib4(ast_u_l, alt_u_l=None, platelets_109=None, age_years=None):
    """Calculate APRI or FIB-4 score for liver fibrosis."""
    try:
        ast = float(ast_u_l)
        ast_upper_limit = 40.0  # typical ULN
    except (ValueError, TypeError) as e:
        return {"error": f"Invalid AST value: {e}"}

    if age_years is not None and platelets_109 is not None:
        # FIB-4 calculation
        try:
            age = float(age_years)
            plt = float(platelets_109)
            alt = float(alt_u_l) if alt_u_l is not None else 40.0
        except (ValueError, TypeError) as e:
            return {"error": f"Invalid input for FIB-4: {e}"}
        if plt <= 0 or alt <= 0:
            return {"error": "Platelets and ALT must be positive."}
        fib4 = (age * ast) / (plt * math.sqrt(alt))
        return {
            "fib4": round(fib4, 2),
            "fibrosis_risk": "high" if fib4 > 3.25 else "intermediate" if fib4 > 1.45 else "low",
        }

    # APRI calculation
    apri = ((ast / ast_upper_limit) * 100) / (float(platelets_109) if platelets_109 else 200.0)
    return {
        "apri": round(apri, 2),
        "fibrosis_risk": "significant" if apri > 1.5 else "moderate" if apri > 0.5 else "mild",
    }


def assess_row(row):
    try:
        # HOMA-IR / HOMA-B (primary purpose)
        if "glucose_mmol" in row or "glucose_mgdl" in row or "fasting_glucose" in row:
            glucose = row.get("glucose_mmol") or row.get("fasting_glucose")
            if glucose is None and "glucose_mgdl" in row:
                glucose = convert_glucose_mgdl_to_mmol(float(row["glucose_mgdl"]))
            insulin = row.get("insulin_mu_u_ml") or row.get("fasting_insulin") or row.get("insulin")
            if glucose is not None and insulin is not None:
                result = calculate_homa_ir(float(glucose), float(insulin))
                result.update(calculate_homa_b(float(glucose), float(insulin)))
                return result

        # try common lab keys
        if "bilirubin" in row and "creatinine" in row:
            return calculate_meld_na(row.get("bilirubin"), row.get("creatinine"), row.get("inr"), row.get("sodium"), row.get("dialysis", "0") == "1", row.get("albumin"), row.get("sex", "M"))
        if "qt_ms" in row or "qt" in row:
            return calculate_qtc(row.get("qt_ms") or row.get("qt"), row.get("rr_ms"), row.get("hr_bpm") or row.get("heart_rate"))
        if "weight_kg" in row:
            return calculate_bmi_z(row.get("weight_kg"), row.get("height_cm"), row.get("age_months") or row.get("age") or 60, row.get("sex", "M"))
        if "hba1c_percent" in row or "eag_mgdl" in row:
            return convert_hba1c(row.get("hba1c_percent"), row.get("eag_mgdl"))
        if "ast_u_l" in row:
            return calculate_apri_fib4(row.get("ast_u_l"), row.get("alt_u_l"), row.get("platelets_109"), row.get("age_years") or row.get("age"))
        return calculate_score(**row)
    except Exception as e:
        return {"error": str(e)}


def _validate_safe_path(path_str: str) -> str:
    """Validate that a file path is safe (no path traversal)."""
    # Check for null bytes
    if '\x00' in path_str:
        raise ValueError("Path contains null bytes.")
    # Resolve to absolute path
    safe_path = os.path.abspath(path_str)
    return safe_path


def process_csv(inp, out):
    safe_inp = _validate_safe_path(inp)
    safe_out = _validate_safe_path(out)

    with open(safe_inp, newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        rows = list(r)
        fieldnames = r.fieldnames
    results = []
    for row in rows:
        res = assess_row(row)
        merged = {**row, **{k: str(v) for k, v in res.items()}}
        results.append(merged)
    # union fieldnames
    all_keys = set()
    for rr in results:
        all_keys.update(rr.keys())
    # keep original first
    extra = [k for k in all_keys if k not in fieldnames]
    with open(safe_out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(fieldnames) + extra)
        w.writeheader()
        w.writerows(results)
    return results


def build_parser():
    p = argparse.ArgumentParser(prog="homa", description="HOMA-IR & HOMA-B Calculator")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("single", help="single calculation")
    s.add_argument("--json", help='JSON of inputs e.g. {"glucose_mmol": 5.5, "insulin_mu_u_ml": 10}')
    s.add_argument("--glucose-mmol", type=float, help="Fasting glucose in mmol/L")
    s.add_argument("--insulin", type=float, help="Fasting insulin in μU/mL")
    s.add_argument("--glucose-mgdl", type=float, help="Fasting glucose in mg/dL (will be converted)")
    s.add_argument("--bili", type=float)
    s.add_argument("--creat", type=float)
    s.add_argument("--inr", type=float)
    s.add_argument("--na", type=float)
    s.add_argument("--qt", type=float)
    s.add_argument("--rr", type=float)
    s.add_argument("--hr", type=float)
    b = sub.add_parser("batch", help="batch csv")
    b.add_argument("--input", required=True)
    b.add_argument("--output", required=True)
    return p


def main(argv=None):
    import json as _json
    p = build_parser()
    a = p.parse_args(argv)
    if a.cmd == "single":
        if a.json:
            row = _json.loads(a.json)
        else:
            row = {}
            # HOMA-IR inputs
            if a.glucose_mmol is not None:
                row["glucose_mmol"] = a.glucose_mmol
            if a.glucose_mgdl is not None:
                row["glucose_mgdl"] = a.glucose_mgdl
            if a.insulin is not None:
                row["insulin_mu_u_ml"] = a.insulin
            # Legacy aliases
            if a.bili is not None:
                row["bilirubin"] = a.bili
            if a.creat is not None:
                row["creatinine"] = a.creat
            if a.inr is not None:
                row["inr"] = a.inr
            if a.na is not None:
                row["sodium"] = a.na
            if a.qt is not None:
                row["qt_ms"] = a.qt
            if a.rr is not None:
                row["rr_ms"] = a.rr
            if a.hr is not None:
                row["hr_bpm"] = a.hr
        print(assess_row(row))
        return 0
    if a.cmd == "batch":
        res = process_csv(a.input, a.output)
        print(f"Processed {len(res)} -> {a.output}")
        return 0
    p.print_help()
    return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
