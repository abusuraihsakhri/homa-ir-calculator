# HOMA1-IR & HOMA1-%B Calculator

Compute the original HOMA1 insulin-resistance and estimated β-cell function indices from paired fasting glucose and insulin. The project provides a static browser application, a standard-library Python calculator and CSV CLI, plus an optional FastAPI service and separate demonstration agent workflows.

## Browser application

The static application is in [web/](web/index.html). A GitHub Pages deployment workflow is included; a public live URL should only be published after the Pages deployment has been enabled and verified.

- Enter fasting glucose in **mg/dL** or **mmol/L** and fasting insulin in **µU/mL** (numerically equivalent to mIU/L).
- View HOMA1-IR and HOMA1-%B. If glucose is **≤ 3.5 mmol/L**, HOMA1-%B is undefined but HOMA1-IR is still shown.
- Optionally process a CSV locally (up to 1 MB and 5,000 rows), preview its results, and download a CSV. Columns: `glucose_mmol` or `glucose_mgdl`, plus `insulin_mu_u_ml`; other columns are preserved.
- Computation takes place entirely in the browser, using JavaScript. No Pyodide, API connection, account, cookies, analytics or server-side upload is required. The optional Oxford documentation link navigates to an external website if clicked.

### Formulae and limitations

For fasting glucose **G** in mmol/L and insulin **I** in µU/mL:

- **HOMA1-IR** = G × I / 22.5
- **HOMA1-%B** = 20 × I / (G − 3.5)

These are **HOMA1 linear approximations**, not the nonlinear Oxford HOMA2 model. There is **no universal diagnostic HOMA-IR cutoff**: reference values vary with assay, population and context. The Python calculator preserves the legacy `insulin_resistance` boolean for backwards compatibility, using an illustrative 2.5 threshold. **Do not use that flag to diagnose insulin resistance or determine treatment.** See the [Oxford HOMA FAQ](https://www.rdm.ox.ac.uk/about/our-facilities-and-units/DTU/software/homa/faq).

## Python CLI

The HOMA calculator itself requires only the Python standard library (Python 3.10+).

~~~bash
python homa.py single --glucose-mmol 5 --insulin 10
python homa.py single --glucose-mgdl 90 --insulin 10
python homa.py single --json '{"glucose_mmol": 5, "insulin_mu_u_ml": 10}'
python homa.py batch --input sample.csv --output results.csv
~~~

The CLI also retains historical QTc, MELD-Na, HbA1c/eAG and APRI/FIB-4 helper routines. The BMI helper reports BMI but **does not invent a growth-reference z-score**: validated age- and sex-specific reference tables are necessary. Calculations must be checked for appropriate clinical indications before use. Unsupported input schemas return an error instead of a fabricated score.

## Optional REST service

~~~bash
python -m pip install -r requirements.txt
python cli.py serve
~~~

Open `http://127.0.0.1:8000/web/index.html` for the static interface, `http://127.0.0.1:8000/docs` for the generated OpenAPI documentation, or POST JSON to `/api/homa` (e.g. `{"glucose_mgdl":90,"insulin_mu_u_ml":10}`). The older `/api/audit`, `/api/chat` and related demonstration agent endpoints remain available. These agent workflows use mock components and generic rules; they do not provide validated clinical interpretation or independent language-model verification.

Agent audit operations require the environment variable `AUDIT_SECRET_KEY`, which is used for in-memory HMAC signing. Generate a unique key with:

~~~bash
python -c "import secrets; print(secrets.token_hex(32))"
~~~

Set the generated key in your environment before using the audit functions. Do not commit real keys.

## Container

~~~bash
cp .env.example .env
# Replace AUDIT_SECRET_KEY in .env with a new random value.
docker compose up --build
~~~

The container runs as a non-root user and binds to `127.0.0.1:8000` by default. Docker is optional for browser/CLI calculations.

## Tests

~~~bash
python -m pip install -r requirements.txt pytest
python -m pytest -q
node --test tests/test_browser.mjs
~~~

CI runs Python 3.10–3.12, browser module tests on Node 22, and a Docker build. The application uses plain HTML, CSS and modern ES modules compatible with current Chromium, Firefox and Safari browsers.

## Privacy and security

The static browser version performs all calculations and CSV processing locally; it does not transmit values or persist them. CSV exports escape potentially executable spreadsheet-formula cells. The optional API receives input on the configured server, so use a trusted local deployment for potentially sensitive values. The optional pattern-based identifier guard is limited and **does not guarantee complete PHI de-identification or HIPAA compliance**. The agent audit trail is tamper-evident in memory and is not a durable audit database.

## License

[MIT](LICENSE).
