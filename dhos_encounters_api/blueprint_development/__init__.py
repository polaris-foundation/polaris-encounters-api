import time
from typing import Dict, List, Optional

from flask import Blueprint, Response, current_app, jsonify, request
from flask_batteries_included.helpers.security import protected_route
from flask_batteries_included.helpers.security.endpoint_security import (
    key_present,
    scopes_present,
)

from .controller import create_many_encounters, reset_database

development_blueprint = Blueprint("dhos/dev", __name__)


@development_blueprint.route("/drop_data", methods=["POST"])
@protected_route(key_present("system_id"))
def drop_data_route() -> Response:
    if current_app.config["ALLOW_DROP_DATA"] is not True:
        raise PermissionError("Cannot drop data in this environment")

    start = time.time()

    reset_database()

    total_time = time.time() - start

    return jsonify({"complete": True, "time_taken": str(total_time) + "s"})


@development_blueprint.route("/encounter/bulk", methods=["POST"])
@protected_route(scopes_present(required_scopes="write:send_encounter"))
def bulk_create_encounter() -> Response:
    """
    ---
    post:
      summary: Create encounters
      description: Bulk creation of many encounters
      tags: [encounter]
      requestBody:
        description: List of encounter details
        required: true
        content:
          application/json:
            schema:
              type: array
              items:
                $ref: '#/components/schemas/EncounterRequestV2'
      responses:
        '200':
          description: Count of encounters created
          content:
            application/json:
              schema:
                type: object
                properties:
                    created:
                        type: integer
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    json: Optional[List[Dict]] = request.json
    if not json:
        raise ValueError("Request requires a JSON body")
    response: Dict = create_many_encounters(encounter_list=json)
    return jsonify(response)
