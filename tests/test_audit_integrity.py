"""Audit trail signature validation tests."""
from agents.base import AuditTrail


def test_tampering_is_detected():
    audit = AuditTrail(secret_key="not-a-production-secret")
    audit.log("worker", "supervisor", "TASK_EVALUATION_COMPLETED", {"status": "SUCCESS"})
    assert audit.verify_integrity()
    audit.logs[0]["actor"] = "malicious"
    assert not audit.verify_integrity()


def test_hash_modification_is_detected():
    audit = AuditTrail(secret_key="not-a-production-secret")
    audit.log("worker", "supervisor", "OK", {"data": 1})
    audit.logs[0]["current_hash"] = "0" * 64
    assert not audit.verify_integrity()
