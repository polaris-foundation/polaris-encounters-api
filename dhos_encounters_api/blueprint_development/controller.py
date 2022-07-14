# -*- coding: utf-8 -*-
from typing import Any, Dict, List

from flask import g
from flask_batteries_included.helpers.error_handler import UnprocessibleEntityException
from flask_batteries_included.sqldb import db
from she_logging.logging import logger

from dhos_encounters_api.models.encounter import Encounter
from dhos_encounters_api.models.location_history import LocationHistory
from dhos_encounters_api.models.score_system_history import ScoreSystemHistory


def reset_database() -> None:
    """Drops SQL data"""
    try:
        for model in (ScoreSystemHistory, LocationHistory, Encounter):
            db.session.query(model).delete()
        db.session.commit()
    except Exception:
        logger.exception("Drop SQL data failed")
        db.session.rollback()


def create_many_encounters(encounter_list: List[Dict[str, Any]]) -> Dict[str, int]:
    objects: List[Encounter] = []
    for details in encounter_list:
        # validate patient
        patient_uuid = details.get("patient_uuid", None)
        if not patient_uuid:
            raise UnprocessibleEntityException(f"Patient UUID not given")

        details.get("epr_encounter_id", None)

        if details.get("spo2_scale", None) not in [None, 1] and not g.jwt_claims.get(
            "can_edit_ews", False
        ):
            raise PermissionError(
                f"Cannot create encounter with spo2_scale set to {details['spo2_scale']}"
            )
        if "epr_encounter_id" in details and details["epr_encounter_id"] == "":
            details["epr_encounter_id"] = None
        objects.append(Encounter(**details))

    db.session.bulk_save_objects(objects)
    db.session.commit()
    return {"created": len(encounter_list)}
