from typing import Dict, List, Optional

from flask import Blueprint, Response, jsonify, request
from flask_batteries_included.helpers import schema
from flask_batteries_included.helpers.error_handler import EntityNotFoundException
from flask_batteries_included.helpers.security import protected_route
from flask_batteries_included.helpers.security.endpoint_security import (
    and_,
    key_present,
    scopes_present,
)

from ..models.encounter import Encounter
from ..models.score_system_history import ScoreSystemHistory
from . import controller

api_blueprint = Blueprint("api", __name__)


@api_blueprint.route("/dhos/v2/encounter", methods=["POST"])
@protected_route(scopes_present(required_scopes="write:send_encounter"))
def create_encounter(encounter_data: Dict) -> Response:
    """---
    post:
      summary: Create an encounter
      description: Create a new encounter with the details in the request body.
      tags: [encounter]
      requestBody:
        description: An encounter
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/EncounterRequestV2'
              x-body-name: encounter_data
      responses:
        '200':
          description: New encounter
          content:
            application/json:
              schema: EncounterResponse
        default:
          description: >-
              Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    return jsonify(controller.create_encounter(encounter_data))


@api_blueprint.route("/dhos/v1/encounter/<encounter_id>", methods=["GET"])
@protected_route(scopes_present(required_scopes="read:send_encounter"))
def get_encounter_by_uuid(
    encounter_id: str, show_deleted: Optional[bool] = None
) -> Response:
    """---
    get:
      summary: Get encounter by UUID
      description: Get an encounter by its UUID
      tags: [encounter]
      parameters:
        - name: encounter_id
          in: path
          required: true
          description: UUID of the encounter
          schema:
            type: string
            example: '2126393f-c86b-4bf2-9f68-42bb03a7b68a'
        - name: show_deleted
          in: query
          required: false
          description: allow a deleted encounter to be returned
          schema:
            type: boolean
            default: false
      responses:
        '200':
          description: An encounter
          content:
            application/json:
              schema: EncounterResponse
        default:
          description: Error, e.g. 404 Not Found, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    if request.is_json:
        raise ValueError("Request should not contain a JSON body")
    return jsonify(controller.get_encounter(encounter_id, show_deleted))


@api_blueprint.route("/dhos/v1/encounter/<encounter_id>/children", methods=["GET"])
@protected_route(scopes_present(required_scopes="read:send_encounter"))
def get_child_encounters(
    encounter_id: str, show_deleted: Optional[bool] = None
) -> Response:
    """---
    get:
      summary: Get child encounters
      description: Gets the child encounter UUIDs of the encounter with the provided UUID
      tags: [encounter]
      parameters:
        - name: encounter_id
          in: path
          required: true
          description: The encounter UUID
          schema:
            type: string
            example: '2126393f-c86b-4bf2-9f68-42bb03a7b68a'
        - name: show_deleted
          in: query
          required: false
          description: Include deleted child encounters in response
          schema:
            type: boolean
            default: false
      responses:
        '200':
          description: List of child encounter UUIDs
          content:
            application/json:
              schema:
                x-body-name: child_encounter_uuids
                type: array
                items:
                  description: A list of child encounter UUIDs
                  type: string
                  example: '2126393f-c86b-4bf2-9f68-42bb03a7b68a'
        default:
          description: Error, e.g. 404 Not Found, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    if request.is_json:
        raise ValueError("Request should not contain a JSON body")
    return jsonify(controller.get_child_encounters(encounter_id, show_deleted))


@api_blueprint.route("/dhos/v1/encounter/<encounter_id>", methods=["PATCH"])
@protected_route(scopes_present(required_scopes="write:send_encounter"))
def update_encounter(encounter_id: str) -> Response:
    """---
    patch:
      summary: Update an encounter by UUID
      description: Update an encounter by UUID using the detail provided in the request body.
      tags: [encounter]
      parameters:
        - name: encounter_id
          in: path
          required: true
          description: The encounter UUID
          schema:
            type: string
            example: '2126393f-c86b-4bf2-9f68-42bb03a7b68a'
      requestBody:
        description: JSON body containing what has changed in an encounter
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/EncounterUpdateRequest'
      responses:
        '200':
          description: Updated encounter
          content:
            application/json:
              schema: EncounterResponse
        default:
          description: >-
              Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    if not request.is_json:
        raise ValueError("Request requires a JSON body")
    encounter_data: Dict = schema.update(**Encounter.schema())
    return jsonify(controller.update_encounter(encounter_id, encounter_data))


@api_blueprint.route(
    "/dhos/v1/score_system_history/<score_system_history_id>", methods=["PATCH"]
)
@protected_route(
    and_(
        key_present("system_id"), scopes_present(required_scopes="write:send_encounter")
    )
)
def update_score_system_history(score_system_history_id: str) -> Response:
    """---
    patch:
      summary: Update score system history by UUID
      description: >-
        Update a score system history by UUID. The score system history contains details of the
        different score systems used for an encounter over time.
      tags: [encounter]
      parameters:
        - name: score_system_history_id
          in: path
          required: true
          description: The score system history UUID
          schema:
            type: string
            example: '2126393f-c86b-4bf2-9f68-42bb03a7b68a'
      requestBody:
        description: Details to change in the score system history
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
               changed_time:
                 type: string
                 example: '2017-09-23T08:29:19.123+00:00'
      responses:
        '200':
          description: The score system history of the patient
          content:
            application/json:
              schema: ScoreSystemHistoryResponse
        default:
          description: >-
              Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    if not request.is_json:
        raise ValueError("Request requires a JSON body")

    _json = schema.update(**ScoreSystemHistory.schema())

    return jsonify(
        controller.update_score_system_history(
            score_system_history_id=score_system_history_id,
            score_system_history_data=_json,
        )
    )


@api_blueprint.route("/dhos/v1/encounter/<encounter_id>", methods=["DELETE"])
@protected_route(scopes_present(required_scopes="write:send_encounter"))
def remove_from_encounter(encounter_id: str) -> Response:
    """---
    delete:
      summary: Delete data from an encounter
      description: Delete data from an encounter. Only specific fields can be deleted.
      tags: [encounter]
      parameters:
        - name: encounter_id
          in: path
          required: true
          description: The encounter UUID
          schema:
            type: string
            example: '2126393f-c86b-4bf2-9f68-42bb03a7b68a'
      requestBody:
        description: Details to delete in the encounter
        required: true
        content:
          application/json:
            schema: EncounterRemoveRequest
      responses:
        '200':
          description: An encounter
          content:
            application/json:
              schema: EncounterResponse
        default:
          description: >-
              Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    encounter_details_to_delete: Optional[Dict] = request.get_json()
    if encounter_details_to_delete is None:
        raise ValueError("Request requires a JSON body")

    return jsonify(
        controller.remove_from_encounter(encounter_id, encounter_details_to_delete)
    )


@api_blueprint.route("/dhos/v1/encounter/merge", methods=["POST"])
@protected_route(scopes_present(required_scopes="write:send_encounter"))
def merge_encounters(merge_data: Dict) -> Response:
    """---
    post:
      summary: Change patient and record for matching encounters.
      description: >-
        Changes the patient uuid and patient record uuid for all encounters that match the given
        child record uuid. The old values are saved in the encounter merge history along with the
        message uuid. This endpoint is used when merging patients.
      tags: [encounter]
      requestBody:
        description: Details of the encounters to merge
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/EncounterMergeRequest'
              x-body-name: merge_data
      responses:
        '200':
          description: Merge results
          content:
            application/json:
              schema:
                type: object
                properties:
                  total:
                    type: integer
                    description: Number of merged child encounters
                    example: 4
        default:
          description: >-
              Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    if merge_data["child_record_uuid"] == merge_data["parent_record_uuid"]:
        raise ValueError(f"Cannot merge identical patient records")

    return jsonify(
        controller.merge_encounters(
            child_record_uuid=merge_data["child_record_uuid"],
            parent_record_uuid=merge_data["parent_record_uuid"],
            parent_patient_uuid=merge_data["parent_patient_uuid"],
            message_uuid=merge_data["message_uuid"],
        )
    )


## V2 Endpoints
@api_blueprint.route("/dhos/v2/encounters", methods=["GET"])
@protected_route(scopes_present(required_scopes="read:send_encounter"))
def get_encounters(
    modified_since: str,
    compact: bool = False,
    show_deleted: bool = False,
    show_children: bool = False,
    expanded: bool = False,
) -> Response:
    """
    ---
    get:
      summary: Get encounters by modified after date
      description: Get encounters which have been modified after the supplied date
      tags: [encounter]
      parameters:
        - name: modified_since
          in: query
          required: true
          description: Get a list of observations sets which have been modified after
            the specified date and time i.e modified_since=2020-12-30 will include an
            encounter from 2020-12-30 00:00:00.000001
          schema:
            type: string
            example: '2020-12-30'
        - name: compact
          in: query
          required: false
          description: Whether to make the response compact
          schema:
            type: boolean
            default: false
        - name: show_deleted
          in: query
          required: false
          description: show deleted data in response
          schema:
            type: boolean
            default: false
        - name: show_children
          in: query
          required: false
          description: show children data in response
          schema:
            type: boolean
            default: false
        - name: expanded
          in: query
          required: false
          description: Whether to expand the indentifier
          schema:
            type: boolean
            default: false
      responses:
        '200':
          description: A list of encounters
          content:
            application/json:
              schema:
                type: array
                items:
                  EncounterResponse
        default:
          description: Error, e.g. 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    results = controller.get_encounters(
        modified_since, compact, show_deleted, show_children, expanded
    )
    return jsonify(results)


@api_blueprint.route("/dhos/v2/encounter", methods=["GET"])
@protected_route(scopes_present(required_scopes="read:send_encounter"))
def get_encounters_by_filters(
    patient_id: Optional[str] = None,
    epr_encounter_id: Optional[str] = None,
    compact: bool = False,
    open_as_of: Optional[str] = None,
    show_deleted: bool = False,
    show_children: bool = False,
    expanded: bool = False,
) -> Response:
    """---
    get:
      summary: Get encounters by filter
      description: Get encounters matching a patient UUID or EPR encounter ID
      tags: [encounter]
      parameters:
        - name: patient_id
          in: query
          required: false
          description: The patient UUID (at least one of patient_id and epr_encounter_id must be present)
          schema:
            type: string
            example: '2126393f-c86b-4bf2-9f68-42bb03a7b68a'
        - name: epr_encounter_id
          in: query
          required: false
          description: The EPR encounter ID (at least one of patient_id and epr_encounter_id must be present)
          schema:
            type: string
            example: '2126393f-c86b-4bf2-9f68-42bb03a7b68a'
        - name: compact
          in: query
          required: false
          description: Whether to make the response compact
          schema:
            type: boolean
            default: false
        - name: open_as_of
          in: query
          required: false
          description: Include only encounters open as of the ISO8601 datetime provided (patient_id required)
          schema:
            type: string
            example: '2017-09-23T08:29:19.123+00:00'
        - name: show_deleted
          in: query
          required: false
          description: show deleted data in response
          schema:
            type: boolean
            default: false
        - name: show_children
          in: query
          required: false
          description: show children data in response
          schema:
            type: boolean
            default: false
        - name: expanded
          in: query
          required: false
          description: Whether to expand the indentifier
          schema:
            type: boolean
            default: false
      responses:
        '200':
          description: A list of encounters
          content:
            application/json:
              schema:
                type: array
                items:
                  EncounterResponse
        default:
          description: Error, e.g. 404 Not Found, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    if request.is_json:
        raise ValueError("Request should not contain a JSON body")
    if patient_id is None and epr_encounter_id is None:
        raise ValueError("Request should contain a patient_id or epr_encounter_id")

    if open_as_of:
        if patient_id is None:
            raise ValueError("Request with open_as_of should contain a patient_id")
        results = controller.get_open_encounters_for_patient(
            patient_id, open_as_of, compact, expanded
        )
    else:
        results = controller.get_encounters_by_patient_or_epr_id(
            patient_id, epr_encounter_id, compact, show_deleted, show_children, expanded
        )
    return jsonify(results)


@api_blueprint.route("/dhos/v2/encounter/latest", methods=["GET"])
@protected_route(scopes_present(required_scopes="read:send_encounter"))
def get_latest_encounter_by_patient_id(
    patient_id: str, open_as_of: Optional[str] = None, compact: bool = False
) -> Response:
    """---
    get:
      summary: Get latest encounter by patient UUID
      description: Get the latest encounter for the patient with the provided UUID
      tags: [encounter]
      parameters:
        - name: patient_id
          in: query
          required: true
          description: The patient UUID.
          schema:
            type: string
            example: '2126393f-c86b-4bf2-9f68-42bb03a7b68a'
        - name: open_as_of
          in: query
          required: false
          description: Include only encounters open as of the ISO8601 datetime provided
          schema:
            type: string
            example: '2017-09-23T08:29:19.123+00:00'
        - name: compact
          in: query
          required: false
          description: Whether to make the response compact
          schema:
            type: boolean
            default: false
      responses:
        '200':
          description: An encounter
          content:
            application/json:
              schema: EncounterResponse
        default:
          description: Error, e.g. 404 Not Found, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    if request.is_json:
        raise ValueError("Request should not contain a JSON body")
    if open_as_of:
        encounters = controller.get_open_encounters_for_patient(
            patient_id=patient_id, compact=compact, open_as_of=open_as_of
        )
    else:
        encounters = controller.get_encounters_by_patient_or_epr_id(
            patient_id=patient_id, compact=compact
        )
    if len(encounters) == 0:
        raise EntityNotFoundException(
            f"No open encounters found for patient with uuid '{patient_id}'"
        )
    return jsonify(encounters[0])


@api_blueprint.route("/dhos/v2/encounter/latest", methods=["POST"])
@protected_route(scopes_present(required_scopes="read:send_encounter"))
def retrieve_latest_encounters_by_patient_ids(
    patient_ids: List[str], compact: bool = False, open_as_of: Optional[str] = None
) -> Response:
    """---
    post:
      summary: Retrieve latest encounters for a list of patient UUIDs
      description: Retrieve latest encounters for the list of patient UUIDs provided in the request body
      tags: [encounter]
      parameters:
        - name: compact
          in: query
          required: false
          description: Whether to make the response compact
          schema:
            type: boolean
            default: false
        - name: open_as_of
          in: query
          required: false
          description: Include only encounters open as of the ISO8601 datetime provided
          schema:
            type: string
            example: '2017-09-23T08:29:19.123+00:00'
      requestBody:
        description: List of patient UUIDs
        required: true
        content:
          application/json:
            schema:
              x-body-name: patient_ids
              type: array
              items:
                description: A list of patient UUIDs
                type: string
                example: '2126393f-c86b-4bf2-9f68-42bb03a7b68a'
                description: patient UUID
      responses:
        '200':
          description: A map of patient UUID to latest encounter
          content:
            application/json:
              schema:
                type: object
                additionalProperties:
                  $ref: '#/components/schemas/EncounterResponse'
        default:
          description: >-
              Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    response: Dict[str, Dict] = {}
    for patient_id in patient_ids:
        if open_as_of:
            encounters = controller.get_open_encounters_for_patient(
                patient_id=patient_id, compact=compact, open_as_of=open_as_of
            )
        else:
            encounters = controller.get_encounters_by_patient_or_epr_id(
                patient_id=patient_id, compact=compact
            )
        if len(encounters) > 0:
            response[patient_id] = encounters[0]
    return jsonify(response)


@api_blueprint.route("/dhos/v1/encounter/locations", methods=["POST"])
@protected_route(scopes_present(required_scopes="read:send_encounter"))
def retrieve_open_encounters_by_locations(
    location_ids: List[str],
    open_as_of: Optional[str] = None,
    compact: bool = False,
) -> Response:
    """---
    post:
      summary: Retrieve open encounters for a list of locations
      description: Retrieve open encounters for the list of location UUIDs provided in the request body
      tags: [encounter]
      parameters:
        - name: open_as_of
          in: query
          required: false
          description: Include only encounters open as of the ISO8601 datetime provided
          schema:
            type: string
            format: date-time
            example: '2017-09-23T08:29:19.123+00:00'
        - name: compact
          in: query
          required: false
          description: Whether to make the response compact
          schema:
            type: boolean
            default: false
      requestBody:
        description: List of location UUIDs
        required: true
        content:
          application/json:
            schema:
              x-body-name: location_ids
              type: array
              items:
                type: string
                example: '2126393f-c86b-4bf2-9f68-42bb03a7b68a'
                description: location UUID
      responses:
        '200':
          description: A list of encounters
          content:
            application/json:
              schema:
                type: array
                items: EncounterResponse
        default:
          description: >-
              Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    response: List[Dict] = controller.get_open_encounters_for_locations(
        location_ids=location_ids, compact=compact, open_as_of=open_as_of
    )
    return jsonify(response)


@api_blueprint.route("/dhos/v1/encounter/patients", methods=["POST"])
@protected_route(scopes_present(required_scopes="read:send_encounter"))
def retrieve_encounters_for_patients(
    patient_ids: List[str],
    open_as_of: Optional[str] = None,
    compact: Optional[bool] = None,
) -> Response:
    """---
    post:
      summary: Retrieve open encounters for a list of patients
      description: Retrieve open encounters for the list of patient UUIDs provided in the request body
      tags: [encounter]
      parameters:
        - name: open_as_of
          in: query
          required: false
          description: Include only encounters open as of the ISO8601 datetime provided
          schema:
            type: string
            format: date-time
            example: '2017-09-23T08:29:19.123+00:00'
        - name: compact
          in: query
          required: false
          description: Whether to make the response compact
          schema:
            type: boolean
            default: false
      requestBody:
        description: List of patient UUIDs
        required: true
        content:
          application/json:
            schema:
              x-body-name: patient_ids
              type: array
              items:
                type: string
                example: '2126393f-c86b-4bf2-9f68-42bb03a7b68a'
                description: patient UUID
      responses:
        '200':
          description: A list of encounters
          content:
            application/json:
              schema:
                type: array
                items: EncounterResponse
        default:
          description: >-
              Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    response: List[Dict] = controller.get_open_encounters_for_patients(
        patient_ids=patient_ids, compact=compact, open_as_of=open_as_of
    )
    return jsonify(response)


@api_blueprint.route("/dhos/v1/encounter/locations/patient_count", methods=["POST"])
@protected_route(scopes_present(required_scopes="read:send_encounter"))
def retrieve_patient_count_for_locations(
    location_ids: List[str], open_as_of: Optional[str] = None
) -> Response:
    """---
    post:
      summary: Retrieve count of patients with open encounters for a list of locations
      description: Retrieve count of patients for the list of location UUIDs provided in the request body
      tags: [encounter]
      parameters:
        - name: open_as_of
          in: query
          required: false
          description: Include only encounters open as of the ISO8601 datetime provided
          schema:
            type: string
            format: date-time
            example: '2017-09-23T08:29:19.123+00:00'
      requestBody:
        description: List of location UUIDs
        required: true
        content:
          application/json:
            schema:
              x-body-name: location_ids
              type: array
              items:
                type: string
                example: '2126393f-c86b-4bf2-9f68-42bb03a7b68a'
                description: location UUID
      responses:
        '200':
          description: A map of location uuid to patient count
          content:
            application/json:
              schema:
                type: object
                additionalProperties:
                  type: integer
        default:
          description: >-
              Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    response: Dict = controller.retrieve_patient_count_for_locations(
        location_ids=location_ids, open_as_of=open_as_of
    )
    return jsonify(response)
