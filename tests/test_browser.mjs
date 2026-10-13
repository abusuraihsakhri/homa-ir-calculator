import test from 'node:test';
import assert from 'node:assert/strict';
import {calculateHoma, parseCsv, toCsv} from '../web/app.mjs';

test('HOMA1 reference example and unit parity', () => {
  const a = calculateHoma('90', 'mgdl', '10');
  const b = calculateHoma('5', 'mmol', '10');
  assert.deepEqual(a, b);
  assert.equal(a.homa_ir, 2.22);
  assert.equal(a.homa_b, 133.33);
});

test('undefined HOMA-B still reports HOMA-IR', () => {
  assert.equal(calculateHoma(3.5, 'mmol', 10).homa_b, null);
  assert.equal(calculateHoma(3.5, 'mmol', 10).homa_ir, 1.56);
});

test('invalid values and units are rejected', () => {
  for (const v of ['', 0, -1, 'nan', 'Infinity']) {
    assert.throws(() => calculateHoma(v, 'mmol', 10));
    assert.throws(() => calculateHoma(5, 'mmol', v));
  }
  assert.throws(() => calculateHoma(5, 'other', 10));
});

test('CSV parser supports quotes and rejects invalid records', () => {
  const rows = parseCsv('sample,glucose_mmol,insulin_mu_u_ml\r\n"A,1",5,10\r\n');
  assert.deepEqual(rows, [{sample:'A,1',glucose_mmol:'5',insulin_mu_u_ml:'10'}]);
  assert.throws(() => parseCsv('a,b\na,"unterminated'));
  assert.throws(() => parseCsv('a,b\na'));
  assert.throws(() => parseCsv('a,a\n1,2'));
});

test('CSV export escapes formula injection and quotes', () => {
  const output = toCsv([{sample:'=HYPERLINK("bad")',homa_ir:2.22}], ['sample','homa_ir']);
  assert.ok(output.includes('\'=HYPERLINK('));
  assert.ok(output.includes('2.22'));
  assert.deepEqual(parseCsv(output)[0], {sample:'\'=HYPERLINK("bad")',homa_ir:'2.22'});
});
