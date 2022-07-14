from typing import Any, Dict, List, Optional, Tuple

import draymed
from dictdiffer import diff
from flask import g
from flask_batteries_included.helpers.error_handler import (
    DuplicateResourceException,
    EntityNotFoundException,
    UnprocessibleEntityException,
)
from flask_batteries_included.helpers.security.jwt import current_jwt_user
from flask_batteries_included.helpers.timestamp import parse_iso8601_to_datetime
from flask_batteries_included.sqldb import db
from she_logging import logger
from sqlalchemy import and_, bindparam, case, cast, distinct, func, literal, or_, orm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.query import Query

from dhos_encounters_api.blueprint_api import publish
from dhos_encounters_api.models.encounter import Encounter
from dhos_encounters_api.models.score_system_history import ScoreSystemHistory

LOCAL_ENCOUNTER = "Local Encounter"
WARD_LOCATION_TYPE = draymed.codes.code_from_name("ward", category="location")
HOSPITAL_LOCATION_TYPE = draymed.codes.code_from_name("hospital", category="location")


def create_encounter(encounter_data: Dict) -> Dict:
    # validate patient
    patient_uuid = encounter_data.get("patient_uuid", None)
    if not patient_uuid:
        raise UnprocessibleEntityException(f"Patient UUID not given")

    epr_encounter_id = encounter_data.get("epr_encounter_id", None)
    # Prevent duplicate local encounters
    if not epr_encounter_id:
        local_encounters = get_open_local_encounters_for_patient(patient_uuid)
        if local_encounters:
            raise DuplicateResourceException(
                f"A local encounter '{local_encounters[0]}' already exists"
            )

    if encounter_data.get("spo2_scale", None) not in [None, 1] and not g.jwt_claims.get(
        "can_edit_ews", False
    ):
        raise PermissionError(
            f"Cannot create encounter with spo2_scale set to {encounter_data['spo2_scale']}"
        )

    encounter = Encounter.new(**encounter_data)
    try:
        db.session.commit()
    except IntegrityError as e:
        if "epr_encounter_id_deleted_at" in str(e):
            raise DuplicateResourceException(
                f"An EPR encounter '{epr_encounter_id}' already exists"
            )
        raise

    encounter_dict = encounter.to_dict()
    publish.publish_encounter_update(encounter_dict)

    return encounter_dict


def get_encounter(encounter_id: str, show_deleted: bool = None) -> Dict:
    encounter: Encounter = (
        db.session.query(Encounter)
        .options(
            joinedload("score_system_history"),
            joinedload("location_history"),
        )
        .get_or_404(encounter_id)
    )
    # Allow opening of deleted encounters specifically by ID
    if show_deleted is not True and encounter.is_deleted:
        raise EntityNotFoundException("Encounter not found")
    return encounter.to_dict()


def get_child_encounters(parent_encounter: str, show_deleted: bool = None) -> List[str]:
    """
    Example of generated SQL:

        WITH RECURSIVE combined(uuid) AS
        (SELECT CAST(%(param_1)s AS VARCHAR(36)) AS uuid UNION ALL SELECT child.uuid AS child_uuid
        FROM encounter AS child JOIN combined AS parent ON parent.uuid = child.parent_uuid AND child.deleted_at IS NULL)
         SELECT combined.uuid AS combined_uuid
        FROM combined
        WHERE combined.uuid != %(param_1)s
    """

    param_parent = literal(parent_encounter)
    rec = db.session.query(cast(param_parent, Encounter.uuid.type).label("uuid")).cte(
        recursive=True, name="combined"
    )
    parent_alias = orm.aliased(rec, name="parent")
    child_alias = orm.aliased(Encounter, name="child")

    join_condition = parent_alias.c.uuid == child_alias.parent_uuid
    if show_deleted is not True:
        join_condition = and_(join_condition, child_alias.deleted_at == None)

    combined = rec.union_all(
        db.session.query(child_alias.uuid).join(parent_alias, join_condition)
    )
    query = db.session.query(combined).filter(combined.c.uuid != param_parent)
    results = [uuid for (uuid,) in query.all()]
    logger.debug(
        "Found %d child encounters for encounter %s",
        len(results),
        parent_encounter,
    )
    return results


def get_open_local_encounters_for_patient(patient_id: str) -> List[str]:
    """
    Get uuids of all local encounters linked to that patient.
    Does not get child encounter records
    """
    query = (
        Encounter.query.filter(Encounter.patient_uuid == patient_id)
        .filter(Encounter.parent_uuid.is_(None))
        .filter(Encounter.discharged_at.is_(None))
        .filter(Encounter.deleted_at.is_(None))
        .filter(
            or_(Encounter.epr_encounter_id.is_(None), Encounter.epr_encounter_id == "")
        )
        .order_by(Encounter.admitted_at.desc())
        .with_entities(Encounter.uuid)
    )
    results = [uuid for (uuid,) in query.all()]
    logger.debug(
        "Found %d open local encounters for patient with UUID %s",
        len(results),
        patient_id,
    )
    return results


def update_encounter(encounter_id: str, encounter_data: Dict) -> Dict:
    encounter = Encounter.query.get_or_404(encounter_id)
    epr_encounter_id = (
        encounter.epr_encounter_id if encounter.epr_encounter_id else LOCAL_ENCOUNTER
    )
    previous_spo2_scale = encounter.spo2_scale
    previous_score_system = encounter.score_system
    new_spo2_scale = encounter_data.get("spo2_scale")
    new_score_system = encounter_data.get("score_system")
    if not g.jwt_claims.get("can_edit_ews", False) and (
        (previous_spo2_scale != new_spo2_scale and new_spo2_scale)
        or (previous_score_system != new_score_system and new_score_system)
    ):
        publish.publish_audit_event(
            event_type="ews_change_failure",
            event_data={
                "clinician_id": current_jwt_user(),
                "encounter_id": encounter.uuid,
                "epr_encounter_id": epr_encounter_id,
                "previous_spo2_scale": previous_spo2_scale,
                "previous_score_system": previous_score_system,
                "new_spo2_scale": new_spo2_scale,
                "new_score_system": new_score_system,
            },
        )
        raise PermissionError("User does not have permission to change EWS")

    initial_encounter_dict = encounter.to_dict()
    encounter.update(**encounter_data)
    db.session.commit()
    if (new_spo2_scale and new_spo2_scale != previous_spo2_scale) or (
        new_score_system and new_score_system != previous_score_system
    ):

        publish.publish_audit_event(
            event_type="score_system_changed",
            event_data={
                "clinician_id": current_jwt_user(),
                "encounter_id": encounter.uuid,
                "epr_encounter_id": epr_encounter_id,
                "previous_score_system": previous_score_system,
                "previous_spo2_scale": previous_spo2_scale,
                "new_score_system": new_score_system,
                "new_spo2_scale": new_spo2_scale,
                "modified_by": encounter.modified_by,
                "modified": encounter.modified,
            },
        )
        publish.publish_score_system_change(encounter.to_dict(expanded=True))

    encounter_dict = encounter.to_dict()

    if encounter_has_changed(initial_encounter_dict, encounter_dict):
        publish.publish_encounter_update(encounter_dict)
        if encounter.modified_by != "dhos-async-adapter":
            modifications = list(diff(initial_encounter_dict, encounter_dict))
            publish.publish_audit_event(
                event_type="encounter_modified",
                event_data={
                    "clinician_id": current_jwt_user(),
                    "encounter_id": encounter.uuid,
                    "modifications": modifications,
                },
            )

    return encounter_dict


def encounter_has_changed(initial_encounter: Dict, encounter_updated: Dict) -> bool:
    has_changed = False
    for field in Encounter.schema()["updatable"]:
        if initial_encounter.get(field) != encounter_updated.get(field):
            has_changed = True
            return has_changed
    return has_changed


def remove_from_encounter(encounter_id: str, details_to_delete: Dict) -> Dict:
    encounter = Encounter.query.get_or_404(encounter_id)
    encounter.remove(**details_to_delete)
    db.session.commit()

    encounter_dict = encounter.to_dict()
    publish.publish_encounter_update(encounter_dict)
    return encounter_dict


def update_score_system_history(
    score_system_history_id: str, score_system_history_data: Dict
) -> Dict:
    score_system_history = ScoreSystemHistory.query.get_or_404(score_system_history_id)
    score_system_history.update(**score_system_history_data)
    db.session.commit()

    return score_system_history.to_dict()


def merge_encounters(
    child_record_uuid: str,
    parent_record_uuid: str,
    parent_patient_uuid: str,
    message_uuid: str,
) -> Dict:
    """
    Called when two patients are merged.
    Update the patient_uuid and patient_record_uuid with the new values,
    the old values are saved in encounter.merge_history

    Returns a count of updated encounters
    """
    updated = 0

    encounter: Encounter
    for encounter in Encounter.query.filter(
        Encounter.patient_record_uuid == child_record_uuid
    ).all():
        old_history: List = encounter.merge_history  # type:ignore
        encounter.merge_history = old_history + [
            {
                "record_uuid": encounter.patient_record_uuid,
                "patient_uuid": encounter.patient_uuid,
                "message_uuid": message_uuid,
            }
        ]
        encounter.patient_uuid = parent_patient_uuid
        encounter.patient_record_uuid = parent_record_uuid
        db.session.add(encounter)
        extra = {
            "child_record_uuid": child_record_uuid,
            "parent_record_uuid": parent_record_uuid,
            "parent_patient_uuid": parent_patient_uuid,
            "message_uuid": message_uuid,
        }
        if encounter.epr_encounter_id:
            logger.info(
                "Merged encounter %s(%s)",
                encounter.epr_encounter_id,
                encounter.uuid,
                extra=extra,
            )
        else:
            logger.info(
                "Merged local encounter (%s)",
                encounter.uuid,
                extra=extra,
            )

        updated += 1

    db.session.commit()

    return {"total": updated}


def get_open_encounters_for_locations(
    location_ids: List[str],
    open_as_of: Optional[str] = None,
    compact: bool = False,
) -> List[Dict]:
    """
    Return a list of encounters that are located in any of the listed parent locations,
    which are open (possibly after a specified date)

    :param location_ids: The uuid of all target locations (includes parent location and all its children)
    :param open_as_of: Latest date that an encounter can still be considered open
    :param compact: Return a shorter structure
    :return: An array of encounters
    """
    query = _build_latest_encounter_query(
        search_field=Encounter.location_uuid,
        values=location_ids,
        open_as_of=open_as_of,
        compact=compact,
    )

    return [encounter.to_dict(compact=compact) for encounter in query.all()]


def get_open_encounters_for_patients(
    patient_ids: List[str],
    open_as_of: Optional[str] = None,
    compact: Optional[bool] = False,
    expanded: Optional[bool] = False,
) -> List[Dict]:
    """
    Return a list of encounters that for the specified patients

    :param patient_ids: The uuids of the relevant patients
    :param open_as_of: Latest date that an encounter can still be considered open
    :param compact: Return a shorter structure
    :return: An array of encounters
    """
    query = _build_latest_encounter_query(
        Encounter.patient_uuid, patient_ids, open_as_of
    )

    return [
        encounter.to_dict(compact=compact, expanded=expanded)
        for encounter in query.all()
    ]


def retrieve_patient_count_for_locations(
    location_ids: List[str], open_as_of: Optional[str]
) -> Dict[str, int]:
    """
    Returns a dict of location: patient count for all of the given locations that have at least one patient.
    :param location_ids: A list of locations to be returned.
    :param open_as_of:
    :return:
    """
    query = (
        _build_encounter_query([(Encounter.location_uuid, location_ids)], open_as_of)
        .with_entities(
            Encounter.location_uuid, func.count(distinct(Encounter.patient_uuid))
        )
        .group_by(Encounter.location_uuid)
    )
    return {
        location_uuid: patient_count for (location_uuid, patient_count) in query.all()
    }


def get_encounters_by_patient_or_epr_id(
    patient_id: str = None,
    epr_encounter_id: str = None,
    compact: bool = False,
    show_deleted: bool = False,
    show_children: bool = False,
    expanded: bool = False,
) -> List[Dict]:

    filters: List[Tuple[Any, List[str]]] = []
    if patient_id:
        filters += [(Encounter.patient_uuid, [patient_id])]
    if epr_encounter_id:
        filters += [(Encounter.epr_encounter_id, [epr_encounter_id])]
    if not filters:
        raise TypeError("At least one of patient id or epr id must be specified")

    query: orm.Query = _build_encounter_query(
        filters,
        show_discharged=True,
        show_deleted=show_deleted,
        show_children=show_children,
    )

    query = query.order_by(
        # sort encounters that are open to the top of list
        case(
            [
                (
                    and_(
                        Encounter.discharged_at.is_(None),
                        Encounter.deleted_at.is_(None),
                    ),
                    0,
                )
            ],
            else_=1,
        ),
        Encounter.admitted_at.desc(),
        Encounter.created.desc(),
    )

    result = [
        encounter.to_dict(compact=compact, expanded=expanded)
        for encounter in query.all()
    ]

    logger.debug("Found %d encounters", len(result))
    if compact is not True:
        for encounter in result:
            encounter["child_encounter_uuids"] = get_child_encounters(
                encounter["uuid"], show_deleted=True
            )
    return result


def get_open_encounters_for_patient(
    patient_id: str, open_as_of: str, compact: bool = None, expanded: bool = False
) -> List[Dict[str, Any]]:
    # This query retrieves open encounters for a given patient, and also gets the UUIDs of child encounters (if not
    # compact).
    result: List[Dict] = get_open_encounters_for_patients(
        [patient_id], open_as_of=open_as_of, compact=compact, expanded=expanded
    )
    if compact is not True:
        for encounter in result:
            encounter["child_encounter_uuids"] = get_child_encounters(
                encounter["uuid"], show_deleted=True
            )

    return result


def _build_latest_encounter_query(
    search_field: Any,
    values: List[str],
    open_as_of: Optional[str],
    show_children: bool = False,
    show_deleted: bool = False,
    compact: bool = False,
) -> orm.Query:
    """
    Returns a Query that will find only the latest matching encounter for each patient.

    :param search_field:
    :param values:
    :param open_as_of:
    :param show_children:
    :param show_deleted:
    :return:
    """
    base_query = Encounter.query.distinct(Encounter.patient_uuid)
    if not compact:
        base_query = base_query.options(
            joinedload("score_system_history"),
            joinedload("location_history"),
        )

    query = _build_encounter_query(
        [(search_field, values)],
        open_as_of,
        show_deleted,
        show_children,
        base_query=base_query,
    ).order_by(
        Encounter.patient_uuid,
        # sort encounters that are open to the top of list
        case(
            [
                (
                    and_(
                        Encounter.discharged_at.is_(None),
                        Encounter.deleted_at.is_(None),
                    ),
                    0,
                )
            ],
            else_=1,
        ),
        Encounter.admitted_at.desc(),
        Encounter.created.desc(),
    )
    return query


def _build_encounter_query(
    field_value_pairs: List[Tuple[Any, List[str]]],
    open_as_of: Optional[str] = None,
    show_discharged: bool = False,
    show_children: bool = False,
    show_deleted: bool = False,
    base_query: orm.Query = None,
) -> orm.Query:
    """
    Returns a Query that will find all matching encounters.
    By default child encounters and deleted encounters are not included.
    """
    params: Dict[str, Any] = {}
    search_filters: List[Any] = []

    for index, (search_field, values) in enumerate(field_value_pairs):
        if len(values) == 1:
            search_filters.append(search_field == bindparam(f"param{index}"))
            params[f"param{index}"] = values[0]
        else:
            search_filters.append(
                search_field.in_(bindparam(f"param{index}", expanding=True))
            )
            params[f"param{index}"] = values

    discharged_at = parse_iso8601_to_datetime(open_as_of)
    if base_query is None:
        base_query = Encounter.query

    query: orm.Query = base_query.filter(*search_filters,).filter(
        True
        if show_discharged
        else or_(
            Encounter.discharged_at.is_(None),
            False if discharged_at is None else Encounter.discharged_at > discharged_at,
        ),
        True if show_deleted else Encounter.deleted_at.is_(None),
        True if show_children else Encounter.parent_uuid.is_(None),
    )

    query = query.params(**params)
    return query


def get_encounters(
    modified_since: str,
    compact: bool = False,
    show_deleted: bool = False,
    show_children: bool = False,
    expanded: bool = False,
) -> List[Dict]:
    conditions: List = [Encounter.modified > modified_since]
    options: List = []

    if show_deleted is False:
        conditions.append(Encounter.deleted_at.is_(None))

    if show_children is False:
        conditions.append(Encounter.parent_uuid.is_(None))

    if compact is False:
        options.append(joinedload(Encounter.score_system_history))
        options.append(joinedload(Encounter.location_history))

    query: Query = (
        db.session.query(Encounter)
        .filter(*conditions)
        .options(*options)
        .order_by(Encounter.modified.desc())
    )

    return [enc.to_dict(compact=compact, expanded=expanded) for enc in query]
