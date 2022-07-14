from typing import Dict

import requests
from behave.runner import Context
from environs import Env


def _get_base_url() -> str:
    base_url: str = Env().str("DHOS_USERS_BASE_URL", "http://dhos-users-api:5000")
    return f"{base_url}/dhos/v1"


def post_clinician(context: Context, clinician: Dict) -> Dict:
    response = requests.post(
        f"{_get_base_url()}/clinician",
        params={"send_reset_email": False},
        headers={"Authorization": f"Bearer {context.system_jwt}"},
        json=clinician,
        timeout=15,
    )
    assert response.status_code == 200
    return response.json()
