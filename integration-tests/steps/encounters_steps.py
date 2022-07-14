import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import uuid4

from behave import step, use_step_matcher
from behave.runner import Context
from clients import dhos_encounters_client as encounters_client
from clients.rabbitmq_client import RABBITMQ_MESSAGES, get_rabbitmq_message
from dateutil.parser import isoparse
from faker import Faker
from helpers import encounter as encounter_helper
from requests import Response
from she_logging import logger

use_step_matcher("re")

fake: Faker = Faker()


@step(
    "the clinician creates? a child encounter of encounter (?P<created_encounter_order>\d+)"
)
def create_child_encounter_od(context: Context, created_encounter_order: str) -> None:
    logger.debug("encounters: %s", json.dumps(context.encounters, indent=4))

    assert len(context.encounters) > 0

    encounter_body: dict = encounter_helper.encounter_body(
        context=context,
        **{
            "child_of_encounter_uuid": context.encounters[
                int(created_encounter_order) - 1
            ]["uuid"],
            "location_uuid": context.location["uuid"],
            "patient_record_uuid": context.patients[-1]["record"]["uuid"],
            "patient_uuid": context.patients[-1]["uuid"],
            "score_system": "news2",
        },
    )
    logger.debug("create encounter body: %s", encounter_body)

    response: Response = encounters_client.create_encounter(
        jwt=context.current_jwt, request_body=encounter_body
    )
    response.raise_for_status()
    api_response = response.json()
    assert api_response.get("uuid") is not None

    context.encounters.append(api_response)
    context.encounter_requests.append(encounter_body)


@step("the clinician creates? (?:an?\w*) (?P<encounter_type>\w+) encounter")
def create_new_encounter(context: Context, encounter_type: str) -> None:
    request: dict = {
        "encounter_type": "INPATIENT",
        "admitted_at": datetime.now(tz=timezone.utc).isoformat(timespec="milliseconds"),
        "dh_product_uuid": context.patients[-1]["dh_products"][0]["uuid"],
        "location_uuid": context.location["uuid"],
        "patient_record_uuid": context.patients[-1]["record"]["uuid"],
        "patient_uuid": context.patients[-1]["uuid"],
        "score_system": "news2",
    }

    if encounter_type.lower() == "epr":
        request["epr_encounter_id"] = fake.pystr(min_chars=5, max_chars=10)

    logger.debug("create encounter body: %s", request)

    response: Response = encounters_client.create_encounter(
        jwt=context.current_jwt, request_body=request
    )
    response.raise_for_status()
    api_response = response.json()
    assert api_response.get("uuid") is not None

    setattr(context, f"{encounter_type.lower()}_encounter", api_response)
    context.encounters.append(api_response)
    context.encounter_requests.append(request)


@step(
    "(?:the\s)(?:clinician can retrieve the encounter|encounter (?P<created_encounter_order>\d*)\s*is retrieved) by its uuid(?P<include_deleted> if deleted encounters are included)?"
)
def get_encounter_by_uuid(
    context: Context, created_encounter_order: str = None, include_deleted: str = None
) -> None:
    encounter = context.encounters[
        encounter_helper.to_object_index(created_encounter_order)
    ]
    response: Response = encounters_client.get_encounter(
        jwt=context.current_jwt,
        encounter_uuid=encounter["uuid"],
        show_deleted=include_deleted is not None,
    )
    response.raise_for_status()
    api_response: Dict[str, Any] = response.json()
    logger.debug("get encounter by uuid returned: %s", api_response)
    assert api_response["uuid"] == encounter["uuid"]
    context.current_encounter = api_response


@step(
    "(?P<encounter_position>t?h?e?\s*encounter\s*\d*) can not be retrieved by its uuid"
)
def assert_can_not_be_retrieved_by_uuid(
    context: Context, encounter_position: str
) -> None:
    uuid = context.encounters[encounter_helper.to_object_index(encounter_position)][
        "uuid"
    ]
    response: Response = encounters_client.get_encounter(
        jwt=context.current_jwt,
        encounter_uuid=uuid,
    )
    assert response.status_code == 404


@step(
    "the retrieved encounter (?P<created_encounter_order>\d*)\s*body matches that used to create it"
)
def assert_current_encounter_matches_request_body(
    context: Context, created_encounter_order: str
) -> None:
    encounter_index = encounter_helper.to_object_index(created_encounter_order)
    response: Response = encounters_client.get_encounter(
        jwt=context.current_jwt,
        encounter_uuid=context.encounters[encounter_index]["uuid"],
    )
    response.raise_for_status()
    api_response: Dict[str, Any] = response.json()

    for field in [
        "encounter_type",
        "location_uuid",
        "patient_record_uuid",
        "score_system",
    ]:
        assert context.encounter_requests[encounter_index][field] == api_response[field]

    assert (
        context.encounter_requests[encounter_index]["dh_product_uuid"]
        == api_response["dh_product"][0]["uuid"]
    )
    assert isoparse(
        context.encounter_requests[encounter_index]["admitted_at"]
    ) - isoparse(api_response["admitted_at"]) < timedelta(milliseconds=1)


@step("the patient has an? (?P<encounter_type>\w+) encounter")
def create_local_encouter(context: Context, encounter_type: str) -> None:
    create_new_encounter(context, encounter_type)
    get_rabbitmq_message(context, RABBITMQ_MESSAGES["ENCOUNTER_UPDATED_MESSAGE"])


@step("the clinician can see that the patient has (?P<encounters>\d+) encounter.?")
def assert_patient_has_number_of_encounters(context: Context, encounters: str) -> None:
    response: Response = encounters_client.get_encounters_by_filter(
        jwt=context.current_jwt,
        patient_id=context.patients[-1]["uuid"],
        show_children=True,
    )
    response.raise_for_status()
    assert int(encounters) == len(response.json())


@step("the clinician closes (?P<encounter_position>t?h?e?\s*encounter\s*\d*)")
def close_encounter(context: Context, encounter_position: str) -> None:
    uuid = context.encounters[encounter_helper.to_object_index(encounter_position)][
        "uuid"
    ]
    response: Response = encounters_client.update_encounter(
        jwt=context.current_jwt,
        encounter_uuid=uuid,
        update_body={
            "discharged_at": datetime.now(tz=timezone.utc).isoformat(
                timespec="milliseconds"
            )
        },
    )
    response.raise_for_status()
    response_json: Dict[str, Any] = response.json()
    assert response_json["discharged_at"] is not None


@step("the clinician deletes (?P<encounter_position>t?h?e?\s*encounter\s*\d*)")
def delete_encounter(context: Context, encounter_position: str) -> None:
    uuid = context.encounters[encounter_helper.to_object_index(encounter_position)][
        "uuid"
    ]
    response: Response = encounters_client.update_encounter(
        jwt=context.current_jwt,
        encounter_uuid=uuid,
        update_body={
            "deleted_at": datetime.now(tz=timezone.utc).isoformat(
                timespec="milliseconds"
            )
        },
    )
    response.raise_for_status()
    response_json: Dict[str, Any] = response.json()
    assert response_json["deleted_at"] is not None


@step("the message contained the encounter uuid")
def verify_message_content_encounter_uuid(context: Context) -> None:
    logger.debug("last created encounter: %s", context.encounters[-1])
    logger.debug("rabbitmq message: %s", context.rabbit_message)
    assert context.encounters[-1]["uuid"] == context.rabbit_message["encounter_id"]


@step(
    "(?:the\s+)encounter (?P<created_encounter_order>\d*)\s*details are merged with those of another encounter"
)
def merge_encounter_details(context: Context, created_encounter_order: str) -> None:
    context.merge_from_encounter = encounter_helper.encounter_body(context)
    logger.debug("merge from encounter: %s", context.merge_from_encounter)

    merge_to_encounter: dict = context.encounters[
        encounter_helper.to_object_index(created_encounter_order)
    ]
    logger.debug("merge to encounter: %s", merge_to_encounter)

    response: Response = encounters_client.merge_encounters(
        jwt=context.current_jwt,
        child_encounter=merge_to_encounter,
        parent_encounter=context.merge_from_encounter,
        message_uuid=str(uuid4()),
    )
    response.raise_for_status()

    response_json: Dict[str, Any] = response.json()
    logger.debug("merge encounters returned: %s", response_json)
    assert response_json["total"] == 1


@step("the retrieved encounter details match that of the merge parent")
def assert_merge_child_details_match_parent(context: Context) -> None:
    logger.debug("merged encounter: %s", context.current_encounter)
    logger.debug("merge from encounter: %s", context.merge_from_encounter)

    assert (
        context.current_encounter["patient_record_uuid"]
        == context.merge_from_encounter["patient_record_uuid"]
    )
    assert (
        context.current_encounter["patient_uuid"]
        == context.merge_from_encounter["patient_uuid"]
    )
