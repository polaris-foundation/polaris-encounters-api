import itertools
import time
from datetime import datetime, timezone
from typing import Dict, List
from uuid import uuid4

from behave import given, step, use_step_matcher, when
from behave.runner import Context
from clients import dhos_encounters_client as encounters_client
from faker import Faker

# -- SELECT DEFAULT STEP MATCHER: Use "re" matcher as default.
use_step_matcher("re")

fake: Faker = Faker()


def encounter_at_location(
    context: Context,
    encounter_type: str = "INPATIENT",
    location_uuid: str = None,
    admitted_at: datetime = None,
    dh_product_uuid: str = None,
    patient_record_uuid: str = None,
    patient_uuid: str = None,
    score_system: str = "new2",
    epr_encounter_id: str = None,
) -> Dict:

    if location_uuid is None:
        location_uuid = context.location["uuid"]

    if admitted_at is None:
        admitted_at = datetime.now(timezone.utc)

    if dh_product_uuid is None:
        dh_product_uuid = str(uuid4())

    if patient_record_uuid is None:
        patient_record_uuid = str(uuid4())

    if patient_uuid is None:
        patient_uuid = str(uuid4())

    request: dict = {
        "encounter_type": "INPATIENT",
        "admitted_at": admitted_at.isoformat(timespec="milliseconds"),
        "dh_product_uuid": dh_product_uuid,
        "location_uuid": location_uuid,
        "patient_record_uuid": patient_record_uuid,
        "patient_uuid": patient_uuid,
        "score_system": score_system,
        "epr_encounter_id": epr_encounter_id,
    }

    if encounter_type.lower() == "epr":
        request["epr_encounter_id"] = fake.pystr(min_chars=5, max_chars=10)

    if encounter_type.lower() == "child":
        assert context.current_encounter is not None
        request["child_of_encounter_uuid"] = context.current_encounter["uuid"]

    return request


def parse_int(s: str) -> int:
    units = {"k": 1_000, "M": 1_000_000, "G": 1_000_000_000}
    multiplier = units.get(s[-1], 1)
    if s[-1] in units:
        s = s[:-1]
    return int(s) * multiplier


@given(
    "there exist (?P<encounter_count_str>\d+[kMG]?) encounters at (?P<location_count_str>\d+[kMG]?) different locations"
)
def bulk_create(
    context: Context, encounter_count_str: str, location_count_str: str
) -> None:
    context.encounter_count, context.location_count = (
        parse_int(encounter_count_str),
        parse_int(location_count_str),
    )
    context.locations = [str(uuid4()) for i in range(context.location_count)]

    encounters = [
        encounter_at_location(
            context, location_uuid=uuid, epr_encounter_id=f"id-{index}"
        )
        for index, uuid in enumerate(
            itertools.islice(
                itertools.cycle(context.locations), context.encounter_count
            )
        )
    ]
    encounters_client.bulk_create_encounters(context.current_jwt, encounters)


@when("timing this step")
def timing_step(context: Context) -> None:
    context.start_time = time.time()


@step(
    "it took less than (?P<max_time>\d+(?:.\d*)?) second(?:s)? to complete",
)
def it_took_less_than(context: Context, max_time: str) -> None:
    limit = float(max_time)

    end_time = time.time()
    assert (
        end_time - context.start_time < limit
    ), f"Max time for test exceeded {max_time} seconds took {end_time - context.start_time:.1}"


@step("we retrieve the encounters at all of the locations")
def get_encounter_by_uuid(context: Context) -> None:
    encounters: List[Dict] = encounters_client.get_encounters_at_locations(
        jwt=context.current_jwt, location_uuids=context.locations
    )
    context.all_encounters = encounters


@step("we received all of the expected encounters")
def validate_encounter_response(context: Context) -> None:
    assert len(context.all_encounters) == context.encounter_count
