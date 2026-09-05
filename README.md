# HOMA-IR & HOMA-B Calculator

> **Domain:** Clinical Decision Support & Biomedical Computing

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)

</div>

---

## 📖 What It Does

A clinical calculator for HOMA-IR (insulin resistance) and HOMA-B (beta-cell function) from fasting glucose and insulin measurements. Also supports additional clinical scores: MELD-Na, QTc, BMI z-score, HbA1c conversion, APRI, and FIB-4.

---

## ⚙️ Key Features

### 🔬 Clinical Calculations

- **HOMA-IR** — Insulin resistance: `(glucose_mmol * insulin_mu_u_ml) / 22.5`. Values > 2.5 suggest insulin resistance.
- **HOMA-B** — Beta-cell function: `(20 * insulin_mu_u_ml) / (glucose_mmol - 3.5)`.
- **MELD-Na** — Liver disease severity score.
- **QTc** — Corrected QT interval (Bazett's and Fridericia's formulas).
- **BMI z-score** — Body mass index with age-adjusted z-score.
- **HbA1c** — Convert between HbA1c (%) and estimated average glucose.
- **APRI / FIB-4** — Liver fibrosis scores.

---

## 💻 CLI Quickstart & Usage

### 1. Single HOMA-IR/HOMA-B Calculation

```bash
# Using mmol/L
python homa.py single --glucose-mmol 5.0 --insulin 10.0

# Using mg/dL (auto-converted)
python homa.py single --glucose-mgdl 90 --insulin 10.0

# Using JSON input
python homa.py single --json '{"glucose_mmol": 5.0, "insulin_mu_u_ml": 10.0}'
```

### 2. Batch CSV Processing

```bash
python homa.py batch --input sample.csv --output results.csv
```

### CSV Input Format

| Field | Description | Required |
|:------|:------------|:----------|
| `glucose_mmol` | Fasting glucose in mmol/L | * |
| `glucose_mgdl` | Fasting glucose in mg/dL (alternative) | * |
| `insulin_mu_u_ml` | Fasting insulin in μU/mL | * |

*One of `glucose_mmol` or `glucose_mgdl` is required, plus `insulin_mu_u_ml`.

---

## 🛡️ Security

- **Audit Trail:** HMAC-SHA256 tamper-evident logging for all calculations.
- **PHI Guard:** Optional outbound PHI detection (MRN, SSN, phone numbers, etc.).
- **Input Validation:** Path traversal protection on file operations.

Set a secure audit secret key:
```bash
export AUDIT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
```

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
# Set test secret key
export AUDIT_SECRET_KEY="test-secret-key-for-unit-tests"

# Run tests
pytest -v
```

---

## 🐳 Container Deployment

```bash
docker build -t homa-ir-calculator .
docker run -e AUDIT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))") -p 8000:8000 homa-ir-calculator
```

---

## 📁 Project Structure

```
homa-ir-calculator/
├── homa.py              # Core calculator (HOMA-IR, HOMA-B, clinical scores)
├── cli.py               # CLI entry point with agent system
├── test_homa.py         # Core calculator tests
├── agents/              # Enterprise agent system
│   ├── base.py          # Security, PHI guard, audit trail
│   ├── models.py        # Pydantic data models
│   ├── supervisor.py    # Multi-agent orchestrator
│   ├── workers.py       # Specialized clinical workers
│   └── api.py           # FastAPI REST server
├── tests/               # Integration tests
│   ├── test_homa_ir_calculator.py
│   └── test_enrichment.py
├── enrichment.py        # Enrichment feature modules
├── simulator.py         # High-throughput stress testing
└── Dockerfile           # Container build
```
