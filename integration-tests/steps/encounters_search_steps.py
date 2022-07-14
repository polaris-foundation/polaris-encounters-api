from typing import Any, Dict

from behave import step, use_step_matcher
from behave.runner import Context
from clients import dhos_encounters_client as encounters_client
from helpers import encounter as encounter_helper
from requests import Response
from she_logging import logger

use_step_matcher("re")


@step("the clinician searche?s? for latest encounter by patient uuid")
def get_latest_encounters_by_patient_uuid(context: Context) -> None:
    patient_uuid = context.patients[-1]["uuid"]
    response: Response = encounters_client.get_latest_encounter_by_patient_id(
        jwt=context.current_jwt, patient_uuid=patient_uuid
    )
    response.raise_for_status()
    search_result: Dict[str, Any] = response.json()
    assert search_result  # is there anything in the returned dict?
    context.search_result = search_result
    logger.debug("latest encounter for %s: %s", patient_uuid, search_result)


@step("the clinician searche?s? for latest encounter by a list of patient UUIDs")
def get_latest_encounters_by_patient_uuid_list(context: Context) -> None:
    ids_to_find = [p["uuid"] for p in context.patients]
    response: Response = encounters_client.retrieve_latest_encounters_by_patient_ids(
        jwt=context.current_jwt, patient_uuids=ids_to_find
    )
    response.raise_for_status()
    search_result: Dict[str, Any] = response.json()
    assert search_result  # is there anything in the returned dict?
    context.search_result = search_result
    logger.debug("latest encounters for %s: %s", ids_to_find, search_result)


@step("the clinician retrieves patients with encounters by a list of patient UUIDs")
def get_encounters_by_patient_uuid_list(context: Context) -> None:
    ids_to_find = [p["uuid"] for p in context.patients]
    response: Response = encounters_client.retrieve_latest_encounters_by_patient_ids(
        jwt=context.current_jwt, patient_uuids=ids_to_find
    )
    response.raise_for_status()
    search_result: Dict[str, Any] = response.json()
    assert search_result is not None
    context.search_result = search_result


@step("the search result returns (?P<encounter_position>t?h?e?\s*encounter\s*\d*)")
def assert_search_returned_last_encounter(
    context: Context, encounter_position: str
) -> None:
    expected_encounter = context.encounters[
        encounter_helper.to_object_index(encounter_position)
    ]
    assert context.search_result["uuid"] == expected_encounter["uuid"]


@step("search results contain (?P<number_of>\d+) (?P<what>\w+)")
def assert_search_result_count(context: Context, number_of: str, what: str) -> None:
    if context.search_result is not None:
        assert len(context.search_result) == int(number_of)
    else:
        raise ValueError(
            f"Unable to handle search result object {context.search_result}"
        )
