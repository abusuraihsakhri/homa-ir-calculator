/** HOMA1 browser calculator. All processing is local to this page. */
export function calculateHoma(glucose, unit, insulin) {
  if (String(glucose).trim() === '' || String(insulin).trim() === '') {
    throw new Error('Enter both fasting glucose and fasting insulin.');
  }
  const decimal = /^\+?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/;
  const gText = String(glucose).trim();
  const iText = String(insulin).trim();
  if (!decimal.test(gText) || !decimal.test(iText)) {
    throw new Error('Enter decimal glucose and insulin measurements.');
  }
  const g = Number(gText);
  const i = Number(iText);
  if (!Number.isFinite(g) || g <= 0 || !Number.isFinite(i) || i <= 0) {
    throw new Error('Glucose and insulin must be positive finite numbers.');
  }
  if (unit !== 'mmol' && unit !== 'mgdl') {
    throw new Error('Select a supported glucose unit.');
  }
  const mmol = unit === 'mgdl' ? g / 18 : g;
  const ir = mmol * i / 22.5;
  const b = mmol > 3.5 ? (20 * i) / (mmol - 3.5) : null;
  if (!Number.isFinite(ir) || (b !== null && !Number.isFinite(b))) {
    throw new Error('The calculation exceeds the numeric range.');
  }
  const round2 = (n) => Math.round((n + Number.EPSILON) * 100) / 100;
  return {
    homa_ir: round2(ir),
    homa_b: b === null ? null : round2(b),
    glucose_mmol: round2(mmol),
    insulin_mu_u_ml: round2(i)
  };
}

/** RFC 4180-compatible quoted fields and line endings; reject malformed quotes. */
export function parseCsv(input) {
  const text = input.replace(/^\uFEFF/, '');
  const records = [];
  let record = [], field = '', inside = false, quotedEnd = false;
  for (let p = 0; p < text.length; p++) {
    const ch = text[p];
    if (inside) {
      if (ch === '"') {
        if (text[p + 1] === '"') { field += '"'; p++; }
        else { inside = false; quotedEnd = true; }
      } else { field += ch; }
    } else if (ch === ',') {
      record.push(field); field = ''; quotedEnd = false;
    } else if (ch === '\r' || ch === '\n') {
      if (ch === '\r' && text[p + 1] === '\n') p++;
      record.push(field); field = ''; quotedEnd = false;
      if (record.some(x => x !== '') || records.length) records.push(record);
      record = [];
    } else if (ch === '"' && !quotedEnd && field === '') {
      inside = true;
    } else if (ch === '"' || (quotedEnd && ch !== ' ')) {
      throw new Error('Malformed CSV quoting.');
    } else if (quotedEnd && ch === ' ') {
      // Ignore whitespace after a closing quoted field.
    } else { field += ch; }
  }
  if (inside) throw new Error('Unterminated quoted CSV field.');
  if (field !== '' || record.length) { record.push(field); records.push(record); }
  if (!records.length) throw new Error('CSV is empty.');
  const headings = records.shift().map(x => x.trim());
  if (headings.some(x => !x) || new Set(headings).size !== headings.length) {
    throw new Error('CSV headers must be nonempty and unique.');
  }
  if (records.length > 5000) throw new Error('CSV exceeds the 5,000-row limit.');
  return records.map((values, n) => {
    if (values.length !== headings.length) {
      throw new Error('CSV row ' + (n + 2) + ' has the wrong column count.');
    }
    return Object.fromEntries(headings.map((heading, j) => [heading, values[j]]));
  });
}

export function toCsv(rows, fields) {
  const escapeCell = (value) => {
    let s = value === null || value === undefined ? '' : String(value);
    // Block spreadsheet formula execution when exported files are opened.
    const trimmed = s.trimStart();
    if (/^[=+@]/.test(trimmed) || (/^-/.test(trimmed) && !/^-?\d+(\.\d+)?(?:[eE][+-]?\d+)?$/.test(trimmed))) s = "'" + s;
    return '"' + s.replace(/"/g, '""') + '"';
  };
  return [fields.map(escapeCell).join(','), ...rows.map(row => fields.map(k => escapeCell(row[k])).join(','))].join('\r\n') + '\r\n';
}

const calculator = typeof document === 'undefined' ? null : document.getElementById('calculator');
if (calculator) {
  const $ = id => document.getElementById(id);
  const results = $('results');
  const error = $('error');
  const setError = text => { error.textContent = text; error.hidden = !text; };
  const setResult = result => {
    $('ir-value').textContent = result.homa_ir.toFixed(2);
    $('b-value').textContent = result.homa_b === null ? 'Not defined' : result.homa_b.toFixed(2) + '%';
    $('b-note').textContent = result.homa_b === null
      ? 'HOMA1-%B cannot be calculated at fasting glucose ≤ 3.5 mmol/L.'
      : 'HOMA1-%B is an estimated β-cell function index, not a direct measurement.';
    $('converted-glucose').textContent = result.glucose_mmol.toFixed(2) + ' mmol/L';
    results.hidden = false;
  };
  calculator.addEventListener('submit', e => {
    e.preventDefault();
    try {
      const result = calculateHoma($('glucose').value, $('glucose-unit').value, $('insulin').value);
      setError('');
      setResult(result);
    } catch (err) {
      results.hidden = true;
      setError(err.message);
    }
  });
  $('clear').addEventListener('click', () => {
    calculator.reset();
    results.hidden = true; setError('');
    $('glucose').focus();
  });
  $('example').addEventListener('click', () => {
    $('glucose-unit').value = 'mgdl';
    $('glucose').value = '90';
    $('insulin').value = '10';
    calculator.requestSubmit();
  });
  const batchInput = $('batch-file');
  const download = $('download');
  let batchRows = [], batchFields = [];
  batchInput.addEventListener('change', async () => {
    download.hidden = true;
    $('batch-status').textContent = '';
    $('batch-preview').replaceChildren();
    batchRows = []; batchFields = [];
    const file = batchInput.files?.[0];
    if (!file) return;
    if (file.size > 1024 * 1024) {
      $('batch-status').textContent = 'CSV must be 1 MB or smaller.';
      return;
    }
    try {
      const records = parseCsv(await file.text());
      if (!records.length) throw new Error('CSV contains no data rows.');
      batchRows = records.map(record => {
        const mmol = record.glucose_mmol || record.fasting_glucose;
        const mgdl = record.glucose_mgdl;
        const ins = record.insulin_mu_u_ml || record.fasting_insulin || record.insulin;
        try {
          const result = calculateHoma(mmol !== undefined && mmol !== '' ? mmol : mgdl,
            mmol !== undefined && mmol !== '' ? 'mmol' : 'mgdl', ins);
          return { ...record, homa_ir: result.homa_ir, homa_b: result.homa_b ?? '', error: '' };
        } catch (err) {
          return { ...record, homa_ir: '', homa_b: '', error: err.message };
        }
      });
      batchFields = [...new Set([...Object.keys(records[0]), 'homa_ir', 'homa_b', 'error'])];
      const valid = batchRows.filter(r => !r.error).length;
      $('batch-status').textContent = valid + ' of ' + batchRows.length + ' rows calculated. Download CSV for full results.';
      const table = document.createElement('table');
      const caption = document.createElement('caption');
      caption.textContent = 'Preview (first 10 rows)';
      table.append(caption);
      const header = document.createElement('tr');
      ['Row', 'HOMA1-IR', 'HOMA1-%B', 'Error'].forEach(s => {
        const th = document.createElement('th'); th.textContent = s; header.append(th);
      });
      const thead = document.createElement('thead'); thead.append(header); table.append(thead);
      const tbody = document.createElement('tbody');
      batchRows.slice(0, 10).forEach((r, i) => {
        const tr = document.createElement('tr');
        [String(i + 1), String(r.homa_ir), String(r.homa_b), r.error].forEach(s => {
          const td = document.createElement('td'); td.textContent = s; tr.append(td);
        });
        tbody.append(tr);
      });
      table.append(tbody);
      $('batch-preview').append(table);
      download.hidden = false;
    } catch (err) { $('batch-status').textContent = err.message; }
  });
  download.addEventListener('click', () => {
    if (!batchRows.length) return;
    const blob = new Blob([toCsv(batchRows, batchFields)], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url; anchor.download = 'homa-results.csv'; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
}