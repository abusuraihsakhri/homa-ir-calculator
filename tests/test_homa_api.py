"""Exercise the public HOMA JSON endpoint without a test server."""
import pytest
from fastapi import HTTPException

from agents.api import HomaRequest, api_homa


def test_homa_json_endpoint_uses_same_clinical_calculation():
    result = api_homa(HomaRequest(glucose_mgdl=90, insulin_mu_u_ml=10))
    assert result["homa_ir"] == 2.22
    assert result["homa_b"] == 133.33
    assert "insulin_resistance" not in result


def test_homa_endpoint_rejects_incomplete_input():
    with pytest.raises(HTTPException) as captured:
        api_homa(HomaRequest(insulin_mu_u_ml=10))
    assert captured.value.status_code == 422
