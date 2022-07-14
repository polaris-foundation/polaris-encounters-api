from typing import Any, Dict, List

import requests
from environs import Env
from requests import Response

base_url: str = Env().str("DHOS_ENCOUNTERS_BASE_URL", "http://dhos-encounters-api:5000")


def get_encounter(
    jwt: str, encounter_uuid: str, show_deleted: bool = False
) -> requests.Response:
    return requests.get(
        f"{base_url}/dhos/v1/encounter/{encounter_uuid}",
        params={"show_deleted": show_deleted},
        headers={"Authorization": f"Bearer {jwt}"},
        timeout=15,
    )


def get_encounters_by_filter(
    jwt: str,
    patient_id: str = None,
    epr_encounter_id: str = None,
    show_children: bool = False,
    show_deleted: bool = False,
) -> requests.Response:
    params: Dict[str, Any] = {
        "show_children": show_children,
        "show_deleted": show_deleted,
    }
    if patient_id is not None:
        params["patient_id"] = patient_id
    elif epr_encounter_id is not None:
        params["epr_encounter_id"] = epr_encounter_id
    else:
        raise ValueError("One of `patient_id` or `epr_encounter_id` must be specified")

    return requests.get(
        f"{base_url}/dhos/v2/encounter",
        params=params,
        headers={"Authorization": f"Bearer {jwt}"},
        timeout=15,
    )


def get_encounters_at_locations(
    jwt: str, location_uuids: List[str], compact: bool = False
) -> List[Dict]:
    params: Dict[str, Any] = {
        "compact": compact,
    }

    response: Response = requests.post(
        f"{base_url}/dhos/v1/encounter/locations",
        params=params,
        json=location_uuids,
        headers={"Authorization": f"Bearer {jwt}"},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def get_latest_encounter_by_patient_id(
    jwt: str, patient_uuid: str
) -> requests.Response:
    return requests.get(
        f"{base_url}/dhos/v2/encounter/latest",
        params={"patient_id": patient_uuid},
        headers={"Authorization": f"Bearer {jwt}"},
        timeout=15,
    )


def retrieve_latest_encounters_by_patient_ids(
    jwt: str, patient_uuids: List[str]
) -> requests.Response:
    return requests.post(
        f"{base_url}/dhos/v2/encounter/latest",
        headers={"Authorization": f"Bearer {jwt}"},
        json=patient_uuids,
        timeout=15,
    )


def create_encounter(jwt: str, request_body: Dict) -> requests.Response:
    return requests.post(
        f"{base_url}/dhos/v2/encounter",
        headers={"Authorization": f"Bearer {jwt}"},
        json=request_body,
        timeout=15,
    )


def bulk_create_encounters(jwt: str, request_body: List[Dict]) -> requests.Response:
    response = requests.post(
        f"{base_url}/encounter/bulk",
        headers={"Authorization": f"Bearer {jwt}"},
        json=request_body,
        timeout=15,
    )
    response.raise_for_status()
    return response


def update_encounter(
    jwt: str, encounter_uuid: str, update_body: Dict[str, Any]
) -> requests.Response:
    return requests.patch(
        f"{base_url}/dhos/v1/encounter/{encounter_uuid}",
        headers={"Authorization": f"Bearer {jwt}"},
        json=update_body,
        timeout=15,
    )


# Note: this endpoint doesn't actually create a parent<->child relationship but merely
# copies some fields from `parent_encounter` to `child_encounter`. `parent` and `child`
# naming, respectively, has been kept in keeping with the API documentation naming.
def merge_encounters(
    jwt: str,
    child_encounter: Dict[str, Any],
    parent_encounter: Dict[str, Any],
    message_uuid: str,
) -> requests.Response:
    return requests.post(
        f"{base_url}/dhos/v1/encounter/merge",
        headers={"Authorization": f"Bearer {jwt}"},
        json={
            "child_record_uuid": child_encounter["patient_record_uuid"],
            "message_uuid": message_uuid,
            "parent_record_uuid": parent_encounter["patient_record_uuid"],
            "parent_patient_uuid": parent_encounter["patient_uuid"],
        },
        timeout=15,
    )
