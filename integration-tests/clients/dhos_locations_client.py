from typing import Dict

import requests
from behave.runner import Context
from environs import Env


def _get_base_url() -> str:
    base_url: str = Env().str(
        "DHOS_LOCATIONS_BASE_URL", "http://dhos-locations-api:5000"
    )
    return f"{base_url}/dhos/v1"


def post_location(context: Context, location: Dict) -> Dict:
    response = requests.post(
        f"{_get_base_url()}/location",
        headers={"Authorization": f"Bearer {context.system_jwt}"},
        json=location,
        timeout=15,
    )
    assert response.status_code == 200
    return response.json()
