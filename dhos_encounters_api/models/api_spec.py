from datetime import datetime
from typing import List, Optional, TypedDict

from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec_webframeworks.flask import FlaskPlugin
from flask_batteries_included.helpers.apispec import (
    FlaskBatteriesPlugin,
    Identifier,
    initialise_apispec,
    openapi_schema,
)
from marshmallow import EXCLUDE, INCLUDE, Schema, fields
from marshmallow.utils import RAISE

PRODUCT_UUID_DESCRIPTION = "UUID of the product the encounter is associated with"

dhos_encounter_api_spec: APISpec = APISpec(
    version="1.0.0",
    openapi_version="3.0.3",
    title="DHOS Encounters API",
    info={
        "description": "A service for storing and retrieving patient encounters (hospital stays)."
    },
    plugins=[FlaskPlugin(), MarshmallowPlugin(), FlaskBatteriesPlugin()],
)

initialise_apispec(dhos_encounter_api_spec)


@openapi_schema(dhos_encounter_api_spec)
class EncounterRequest(Schema):
    class Meta:
        title = "Encounter request"
        unknown = EXCLUDE
        ordered = True

        class Dict(TypedDict, total=False):
            encounter_type: str
            admitted_at: datetime
            location_uuid: str
            patient_record_uuid: str
            dh_product_uuid: str
            score_system: str
            discharged_at: Optional[datetime]
            deleted_at: Optional[datetime]
            epr_encounter_id: Optional[str]
            child_of_encounter_uuid: Optional[str]
            spo2_scale: Optional[int]

    # Required fields
    encounter_type = fields.String(required=False, allow_none=True, example="INPATIENT")
    admitted_at = fields.AwareDateTime(
        required=True, example="2019-01-23T08:31:19.123+00:00"
    )
    location_uuid = fields.String(
        required=True,
        example="7f03efbe-5828-49dc-a777-7f6952b9cea7",
        description="UUID of the encounter's location",
    )
    patient_record_uuid = fields.String(
        required=True,
        example="47f9a1d6-80f3-4f3d-92f5-4136cd60d2bd",
        description="UUID of the patient record the encounter is associated with",
    )
    dh_product_uuid = fields.String(
        required=True,
        example="144873d2-8eb4-4b89-8d38-7650e6012504",
        description=PRODUCT_UUID_DESCRIPTION,
    )
    score_system = fields.String(
        required=True,
        example="news2",
        description="Early warning score system used by the encounter",
    )

    # Optional fields
    discharged_at = fields.AwareDateTime(
        required=False, allow_none=True, example="2019-01-23T08:31:19.123+00:00"
    )
    deleted_at = fields.AwareDateTime(
        required=False, allow_none=True, example="2019-01-23T08:31:19.123+00:00"
    )
    epr_encounter_id = fields.String(
        required=False, allow_none=True, example="2017L2387461278"
    )
    child_of_encounter_uuid = fields.String(
        required=False,
        allow_none=True,
        example="46f41d57-05de-42b6-9cab-6fbb7c916d82",
        description="UUID of the parent encounter",
    )
    spo2_scale = fields.Integer(required=False, allow_none=True, example=2, default=1)


@openapi_schema(dhos_encounter_api_spec)
class EncounterRemoveRequest(Schema):
    class Meta:
        title = "Encounter removal request"
        unknown = EXCLUDE
        ordered = True

        class Dict(TypedDict, total=False):
            child_of_encounter_uuid: str

    child_of_encounter_uuid = fields.String(
        required=False, allow_none=True, example="46f41d57-05de-42b6-9cab-6fbb7c916d82"
    )


@openapi_schema(dhos_encounter_api_spec)
class EncounterRequestV2(EncounterRequest):
    class Meta:
        title = "Encounter request"
        unknown = EXCLUDE
        ordered = True

        class Dict(TypedDict, total=False):
            encounter_type: str
            admitted_at: datetime
            location_uuid: str
            patient_uuid: str
            patient_record_uuid: str
            dh_product_uuid: str
            score_system: str
            discharged_at: Optional[datetime]
            deleted_at: Optional[datetime]
            epr_encounter_id: Optional[str]
            child_of_encounter_uuid: Optional[str]
            spo2_scale: Optional[int]

    # Required fields
    patient_uuid = fields.String(
        required=True,
        example="47f9a1d6-80f3-4f3d-92f5-4136cd60d2bd",
        description="UUID of the patient the encounter is associated with",
    )


@openapi_schema(dhos_encounter_api_spec)
class EncounterResponse(Identifier):
    """Similar to EncounterRequest, but includes Identifier schema and some fields are in a different form."""

    class Meta:
        title = "Encounter response"
        unknown = RAISE
        ordered = True

    encounter_type = fields.String(required=True, example="INPATIENT")
    admitted_at = fields.AwareDateTime(
        required=True, example="2019-01-23T08:31:19.123+00:00"
    )
    location_uuid = fields.String(
        required=True,
        example="7f03efbe-5828-49dc-a777-7f6952b9cea7",
        description="UUID of the encounter's location",
    )
    patient_uuid = fields.String(
        required=False,
        allow_none=True,
        example="47f9a1d6-80f3-4f3d-92f5-4136cd60d2bd",
        description="UUID of the patient the encounter is associated with",
    )
    patient_record_uuid = fields.String(
        required=True,
        example="47f9a1d6-80f3-4f3d-92f5-4136cd60d2bd",
        description="UUID of the patient record the encounter is associated with",
    )
    score_system = fields.String(
        required=True,
        allow_none=True,
        example="news2",
        description="Early warning score system used by the encounter",
    )
    discharged_at = fields.AwareDateTime(
        required=False, allow_none=True, example="2019-01-23T08:31:19.123+00:00"
    )
    deleted_at = fields.AwareDateTime(
        required=False, allow_none=True, example="2019-01-23T08:31:19.123+00:00"
    )
    epr_encounter_id = fields.String(
        required=False, allow_none=True, example="2017L2387461278"
    )
    child_encounter_uuids = fields.List(
        fields.String(
            example="46f41d57-05de-42b6-9cab-6fbb7c916d82",
            description="UUID of the parent encounter",
        ),
        required=False,
        allow_none=True,
    )
    spo2_scale = fields.Integer(required=False, allow_none=True, default=1)
    dh_product = fields.List(fields.Dict)
    score_system_history = fields.List(fields.Dict)
    location_history = fields.List(fields.Dict)


@openapi_schema(dhos_encounter_api_spec)
class EncounterUpdateRequest(Schema):
    """Very similar to EncounterRequest, but fields aren't required."""

    class Meta:
        title = "Encounter update request"
        unknown = EXCLUDE
        ordered = True

        class Dict(TypedDict, total=False):
            encounter_type: Optional[str]
            admitted_at: Optional[datetime]
            location_uuid: Optional[str]
            patient_record_uuid: Optional[str]
            dh_product_uuid: Optional[str]
            score_system: Optional[str]
            discharged_at: Optional[datetime]
            deleted_at: Optional[datetime]
            epr_encounter_id: Optional[str]
            child_of_encounter_uuid: Optional[str]
            spo2_scale: Optional[int]

    encounter_type = fields.String(required=False, example="INPATIENT")
    admitted_at = fields.AwareDateTime(
        required=False, example="2019-01-23T08:31:19.123+00:00"
    )
    location_uuid = fields.String(
        required=False,
        example="7f03efbe-5828-49dc-a777-7f6952b9cea7",
        description="UUID of the encounter's location",
    )
    patient_record_uuid = fields.String(
        required=False,
        example="47f9a1d6-80f3-4f3d-92f5-4136cd60d2bd",
        description="UUID of the patient record the encounter is associated with",
    )
    dh_product_uuid = fields.String(
        required=False,
        example="144873d2-8eb4-4b89-8d38-7650e6012504",
        description=PRODUCT_UUID_DESCRIPTION,
    )
    score_system = fields.String(
        required=False,
        example="news2",
        description="Early warning score system used by the encounter",
    )
    discharged_at = fields.AwareDateTime(
        required=False, allow_none=True, example="2019-01-23T08:31:19.123+00:00"
    )
    deleted_at = fields.AwareDateTime(
        required=False, allow_none=True, example="2019-01-23T08:31:19.123+00:00"
    )
    epr_encounter_id = fields.String(
        required=False, allow_none=True, example="2017L2387461278"
    )
    child_of_encounter_uuid = fields.String(
        required=False,
        allow_none=True,
        example="46f41d57-05de-42b6-9cab-6fbb7c916d82",
        description="UUID of the parent encounter",
    )
    spo2_scale = fields.Integer(required=False, allow_none=True, default=1)


@openapi_schema(dhos_encounter_api_spec)
class ScoreSystemHistoryResponse(Schema):
    class Meta:
        title = "Score system history response"
        unknown = EXCLUDE
        ordered = True

    uuid = fields.String(example="b5edcd68-6d7a-4767-aac3-b47e7240d574")
    changed_time = fields.String(example="2019-01-01T00:00:00.000Z")
    score_system = fields.String(example="news2")
    previous_score_system = fields.String(example="meows")
    spo2_scale = fields.Integer(example=1)
    previous_spo2_scale = fields.Integer(example=2)
    changed_by = fields.Dict()


@openapi_schema(dhos_encounter_api_spec)
class SearchEncounterV2(Schema):
    """
    Encounter search response, includes only those fields available through
    Encounter API.
    """

    class Meta:
        title = "Patient Encounter detail"
        unknown = EXCLUDE
        ordered = True

        class Dict(TypedDict, total=False):
            patient_uuid: str
            encounter_uuid: Optional[str]
            admitted_at: datetime
            has_clinician_bookmark: bool
            discharged_at: datetime
            discharged: bool
            ward_uuid: Optional[str]
            hospital_uuid: Optional[str]

    patient_uuid = fields.String(required=True)
    encounter_uuid = fields.String(required=True, allow_none=True)
    admitted_at = fields.AwareDateTime(required=True, allow_none=True)
    has_clinician_bookmark = fields.Boolean(required=True)
    discharged_at = fields.AwareDateTime(required=True, allow_none=True)
    discharged = fields.Boolean(required=True)
    ward_uuid = fields.String(required=False, allow_none=True)
    hospital_uuid = fields.String(required=False, allow_none=True)


@openapi_schema(dhos_encounter_api_spec)
class SearchResultsResponseV2(Schema):
    class Meta:
        title = "Results from a search (encounter only)"
        unknown = EXCLUDE
        ordered = True

        class Dict(TypedDict):
            total: int
            results: List[SearchEncounterV2.Meta.Dict]

    total = fields.Integer(example=2)
    results = fields.Nested(SearchEncounterV2, many=True)


@openapi_schema(dhos_encounter_api_spec)
class EncounterMergeRequest(Schema):
    class Meta:
        title = "Encounter merge request"
        unknown = INCLUDE
        ordered = True

        class Dict(TypedDict, total=False):
            child_record_uuid: str
            parent_record_uuid: str
            parent_patient_uuid: str
            message_uuid: str

    child_record_uuid = fields.String(
        required=True,
        example="c62aa4f6-39fd-4df2-8d31-62f1a560ca6e",
        description="The UUID of the child encounter's patient record",
    )
    parent_record_uuid = fields.String(
        required=True,
        example="fb830128-2cbb-4086-9873-56e0a58614d3",
        description="The UUID of the parent encounter's patient record",
    )
    parent_patient_uuid = fields.String(
        required=True,
        example="fb830128-2cbb-4086-9873-56e0a58614d3",
        description="The UUID of the parent encounter's patient",
    )
    message_uuid = fields.String(
        required=True,
        example="ed2ac4d5-10c6-48f5-8f38-6be68dec988c",
        description="The UUID of the message causing the merge",
    )
