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


def _positive_finite(value, name):
    """Parse a positive finite measurement; reject booleans and nonnumbers."""
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a positive finite number.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive finite number.") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{name} must be a positive finite number.")
    return number


def calculate_homa_ir(glucose_mmol: float, insulin_mu_u_ml: float) -> dict:
    """Calculate the HOMA1-IR approximation from paired fasting values.

    The 2.5 threshold is a legacy illustrative flag, NOT a diagnostic cutoff.
    HOMA indices have no universal normal/reference cutoff.
    """
    glucose = _positive_finite(glucose_mmol, "Glucose")
    insulin = _positive_finite(insulin_mu_u_ml, "Insulin")
    score = glucose * insulin / 22.5
    if not math.isfinite(score):
        raise ValueError("HOMA-IR exceeds the supported numeric range.")
    return {
        "homa_ir": round(score, 2),
        "glucose_mmol": round(glucose, 2),
        "insulin_mu_u_ml": round(insulin, 2),
        "insulin_resistance": score > 2.5,  # deprecated legacy example flag
        "interpretation_note": "HOMA1 estimate; the legacy 2.5 flag is not diagnostic.",
    }

def calculate_homa_b(glucose_mmol: float, insulin_mu_u_ml: float) -> dict:
    """Calculate HOMA1-%B; valid only when fasting glucose exceeds 3.5 mmol/L."""
    glucose = _positive_finite(glucose_mmol, "Glucose")
    insulin = _positive_finite(insulin_mu_u_ml, "Insulin")
    if glucose <= 3.5:
        raise ValueError("Glucose must be > 3.5 mmol/L for HOMA-B calculation.")
    score = (20 * insulin) / (glucose - 3.5)
    if not math.isfinite(score):
        raise ValueError("HOMA-B exceeds the supported numeric range.")
    return {
        "homa_b": round(score, 2),
        "glucose_mmol": round(glucose, 2),
        "insulin_mu_u_ml": round(insulin, 2),
    }

def convert_glucose_mgdl_to_mmol(mgdl: float) -> float:
    """Convert glucose from mg/dL to mmol/L."""
    return _positive_finite(mgdl, "Glucose") / 18.0


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
    """Calculate historical MELD-Na (not MELD 3.0); values in conventional units.

    Bilirubin/creatinine in mg/dL, sodium in mmol/L. Albumin and sex are
    accepted for legacy callers but do not enter the historical MELD-Na formula.
    """
    try:
        bili = _positive_finite(bilirubin, "Bilirubin")
        creat = _positive_finite(creatinine, "Creatinine")
        inr_val = _positive_finite(inr, "INR")
        na = _positive_finite(sodium, "Sodium")
        dial = dialysis if isinstance(dialysis, bool) else str(dialysis).lower() in {"1", "true", "yes"}
        bili = max(1.0, bili)
        creat = 4.0 if dial else min(4.0, max(1.0, creat))
        inr_val = max(1.0, inr_val)
        na = min(137.0, max(125.0, na))
        meld = 10 * (0.957 * math.log(creat) + 0.378 * math.log(bili) + 1.120 * math.log(inr_val) + 0.643)
        meld = min(40.0, max(6.0, meld))
        adjusted = meld + 1.32 * (137 - na) - 0.033 * meld * (137 - na) if meld > 11 else meld
        score = min(40.0, max(6.0, adjusted))
    except (ValueError, TypeError, OverflowError) as exc:
        return {"error": f"Invalid input for MELD-Na: {exc}"}
    return {
        "meld_na": round(score, 1),
        "severity": "high" if score >= 30 else "moderate" if score >= 20 else "low",
    }

def calculate_qtc(qt_ms, rr_ms=None, hr_bpm=None):
    """QTc in milliseconds, with RR expressed in seconds within the formula."""
    try:
        qt = _positive_finite(qt_ms, "QT")
        if rr_ms is not None:
            rr = _positive_finite(rr_ms, "RR") / 1000.0
        elif hr_bpm is not None:
            rr = 60.0 / _positive_finite(hr_bpm, "Heart rate")
        else:
            return {"error": "Either RR interval or heart rate is required."}
        bazett = qt / math.sqrt(rr)
        fridericia = qt / (rr ** (1 / 3))
        if not (math.isfinite(bazett) and math.isfinite(fridericia)):
            raise ValueError("Calculated QTc is not finite.")
    except (ValueError, TypeError, OverflowError) as exc:
        return {"error": f"Invalid input for QTc: {exc}"}
    return {
        "qtc_bazett_ms": round(bazett, 1),
        "qtc_fridericia_ms": round(fridericia, 1),
        "prolonged": bazett > 440,  # legacy illustrative cutoff, not a clinical diagnosis
    }

def calculate_bmi_z(weight_kg, height_cm, age_months, sex="M"):
    """Calculate BMI only; do not fabricate a growth-reference z-score.

    Valid BMI-for-age z-scores require sex/age-specific validated LMS tables.
    """
    try:
        wt = _positive_finite(weight_kg, "Weight")
        ht = _positive_finite(height_cm, "Height") / 100.0
        age = float(age_months)
        if not math.isfinite(age) or age < 0:
            raise ValueError("Age must be a nonnegative finite number.")
        bmi = wt / (ht * ht)
        if not math.isfinite(bmi):
            raise ValueError("BMI exceeds the supported numeric range.")
    except (TypeError, ValueError, OverflowError) as exc:
        return {"error": f"Invalid input for BMI: {exc}"}
    return {
        "bmi": round(bmi, 2),
        "z_score": None,
        "category": "not assessed",
        "warning": "BMI-for-age z-score requires a validated sex- and age-specific growth reference.",
    }

def convert_hba1c(hba1c_percent=None, eag_mgdl=None):
    """ADAG estimated average glucose/HbA1c conversion, not a diagnosis."""
    if hba1c_percent is None and eag_mgdl is None:
        return {"error": "Either hba1c_percent or eag_mgdl must be provided."}
    try:
        if hba1c_percent is not None:
            hba1c = _positive_finite(hba1c_percent, "HbA1c")
            eag = 28.7 * hba1c - 46.7
            if eag <= 0:
                raise ValueError("HbA1c is outside the formula's usable range.")
        else:
            eag = _positive_finite(eag_mgdl, "Estimated average glucose")
            hba1c = (eag + 46.7) / 28.7
        if not (math.isfinite(eag) and math.isfinite(hba1c)):
            raise ValueError("Calculated value is not finite.")
    except (TypeError, ValueError, OverflowError) as exc:
        return {"error": f"Invalid HbA1c/eAG value: {exc}"}
    return {
        "hba1c_percent": round(hba1c, 1),
        "eag_mgdl": round(eag, 1),
        "eag_mmol": round(eag / 18.0, 2),
    }

def calculate_apri_fib4(ast_u_l, alt_u_l=None, platelets_109=None, age_years=None, ast_uln=40.0):
    """Compute FIB-4 when age and ALT are supplied, otherwise APRI.

    Platelet count is mandatory for both; AST ULN defaults to 40 U/L for APRI.
    """
    try:
        ast = _positive_finite(ast_u_l, "AST")
        platelets = _positive_finite(platelets_109, "Platelets")
        if age_years is not None:
            age = _positive_finite(age_years, "Age")
            alt = _positive_finite(alt_u_l, "ALT")
            score = age * ast / (platelets * math.sqrt(alt))
            if not math.isfinite(score):
                raise ValueError("FIB-4 is not finite.")
            return {
                "fib4": round(score, 2),
                "fibrosis_risk": "high" if score > 3.25 else "intermediate" if score > 1.45 else "low",
            }
        uln = _positive_finite(ast_uln, "AST upper limit of normal")
        score = (ast / uln) * 100.0 / platelets
        if not math.isfinite(score):
            raise ValueError("APRI is not finite.")
        return {
            "apri": round(score, 2),
            "fibrosis_risk": "significant" if score > 1.5 else "moderate" if score > 0.5 else "mild",
        }
    except (TypeError, ValueError, OverflowError) as exc:
        return {"error": f"Invalid APRI/FIB-4 input: {exc}"}

def assess_row(row):
    """Select a supported calculation using explicit fields, never a pseudo-score."""
    try:
        if not isinstance(row, dict):
            return {"error": "A JSON object or CSV row is required."}
        has_glucose = any(k in row for k in ("glucose_mmol", "glucose_mgdl", "fasting_glucose"))
        has_insulin = any(k in row for k in ("insulin_mu_u_ml", "fasting_insulin", "insulin"))
        if has_glucose or has_insulin:
            glucose = next((row[k] for k in ("glucose_mmol", "fasting_glucose") if row.get(k) not in (None, "")), None)
            if glucose is None and row.get("glucose_mgdl") not in (None, ""):
                glucose = convert_glucose_mgdl_to_mmol(row["glucose_mgdl"])
            insulin = next((row[k] for k in ("insulin_mu_u_ml", "fasting_insulin", "insulin") if row.get(k) not in (None, "")), None)
            if glucose is None or insulin is None:
                return {"error": "Fasting glucose and insulin are both required."}
            result = calculate_homa_ir(glucose, insulin)
            if float(glucose) > 3.5:
                result.update(calculate_homa_b(glucose, insulin))
            else:
                result["homa_b"] = None
                result["homa_b_note"] = "HOMA-B is undefined at glucose <= 3.5 mmol/L."
            return result
        if "bilirubin" in row and "creatinine" in row:
            return calculate_meld_na(row.get("bilirubin"), row.get("creatinine"), row.get("inr"), row.get("sodium"), row.get("dialysis", False), row.get("albumin"), row.get("sex", "M"))
        if "qt_ms" in row or "qt" in row:
            return calculate_qtc(row.get("qt_ms", row.get("qt")), row.get("rr_ms"), row.get("hr_bpm", row.get("heart_rate")))
        if "weight_kg" in row:
            return calculate_bmi_z(row.get("weight_kg"), row.get("height_cm"), row.get("age_months", row.get("age")), row.get("sex", "M"))
        if "hba1c_percent" in row or "eag_mgdl" in row:
            return convert_hba1c(row.get("hba1c_percent"), row.get("eag_mgdl"))
        if "ast_u_l" in row:
            return calculate_apri_fib4(row.get("ast_u_l"), row.get("alt_u_l"), row.get("platelets_109"), row.get("age_years", row.get("age")))
        return {"error": "Unsupported input fields; supply a documented clinical calculator schema."}
    except (ValueError, TypeError, OverflowError) as exc:
        return {"error": str(exc)}

def _validate_safe_path(path_str: str) -> str:
    """Normalize a user-chosen local path; this is not a sandbox boundary."""
    # Check for null bytes
    if '\x00' in path_str:
        raise ValueError("Path contains null bytes.")
    # Command-line callers deliberately select their own filesystem paths.
    safe_path = os.path.abspath(path_str)
    return safe_path


def process_csv(inp, out):
    safe_inp = _validate_safe_path(inp)
    safe_out = _validate_safe_path(out)

    if safe_inp == safe_out:
        raise ValueError("Input and output CSV paths must differ.")
    with open(safe_inp, newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        rows = list(r)
        fieldnames = r.fieldnames
    if not fieldnames:
        raise ValueError("CSV input must include a header row.")
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
    extra = sorted(k for k in all_keys if k not in fieldnames)
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
