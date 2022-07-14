from typing import Dict

import requests
from behave.runner import Context
from environs import Env


def _get_base_url() -> str:
    base_url: str = Env().str("DHOS_SERVICES_BASE_URL", "http://dhos-services-api:5000")
    return f"{base_url}/dhos/v1"


def post_patient(context: Context, patient: Dict) -> Dict:
    response = requests.post(
        f"{_get_base_url()}/patient",
        params={"type": "SEND"},
        headers={"Authorization": f"Bearer {context.system_jwt}"},
        json=patient,
        timeout=15,
    )
    assert response.status_code == 200
    return response.json()


def get_patient(context: Context, patient_uuid: str) -> Dict:
    response = requests.get(
        f"{_get_base_url()}/patient/{patient_uuid}",
        params={"type": "SEND"},
        headers={"Authorization": f"Bearer {context.superclinician_jwt}"},
        timeout=15,
    )
    assert response.status_code == 200
    return response.json()
