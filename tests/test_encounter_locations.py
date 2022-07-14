from datetime import datetime, timezone
from typing import Callable, ContextManager, Dict, Generator, List

import pytest
from dateutil.parser import parse
from flask_batteries_included.sqldb import db
from sqlalchemy.orm import Session

from dhos_encounters_api.blueprint_api.controller import (
    get_open_encounters_for_locations,
)
from dhos_encounters_api.models.encounter import Encounter
from dhos_encounters_api.models.location_history import LocationHistory
from dhos_encounters_api.models.score_system_history import ScoreSystemHistory


@pytest.fixture(autouse=True)
def pre_existing_nodes() -> Generator[None, None, None]:
    yield
    LocationHistory.query.delete()
    ScoreSystemHistory.query.delete()
    Encounter.query.delete()
    db.session.commit()


@pytest.mark.parametrize("compact", [True, False])
def test_get_open_encounters_for_locations(
    app_context: None,
    encounter_factory: Callable,
    statement_counter: Callable[[Session], ContextManager],
    location_uuid: str,
    dh_product_uuid: str,
    record_uuid: str,
    patient_uuid: str,
    compact: bool,
) -> None:
    encounter_factory(
        location_uuid=location_uuid,
        epr_encounter_id="thisisanencounterid7",
        encounter_type="INPATIENT",
        admitted_at="2018-01-01T00:00:00.000Z",
        discharged_at="2018-01-01T00:00:00.000Z",
        patient_record_uuid=record_uuid,
        patient_uuid=patient_uuid,
        dh_product_uuid=dh_product_uuid,
        location_history=[
            {"location_uuid": location_uuid, "arrived_at": "2018-01-01T00:00:00.000Z"}
        ],
    )
    db.session.commit()
    # Older encounter for the patient should be ignored
    encounter_factory(
        location_uuid=location_uuid,
        epr_encounter_id="thisisanencounterid9",
        encounter_type="INPATIENT",
        admitted_at="2017-01-02T00:00:00.000Z",
        discharged_at=None,
        patient_record_uuid=record_uuid,
        patient_uuid=patient_uuid,
        dh_product_uuid=dh_product_uuid,
    )
    db.session.commit()

    encounter_factory(
        location_uuid=location_uuid,
        epr_encounter_id="thisisanencounterid8",
        encounter_type="INPATIENT",
        admitted_at="2018-01-02T00:00:00.000Z",
        discharged_at=None,
        patient_record_uuid=record_uuid,
        patient_uuid=patient_uuid,
        dh_product_uuid=dh_product_uuid,
    )
    db.session.commit()

    with statement_counter(db.session) as ctr:
        open_encounters: List[Dict] = get_open_encounters_for_locations(
            location_ids=[location_uuid],
            open_as_of=datetime(2018, 1, 1, 0, 0, 0, tzinfo=timezone.utc).isoformat(
                timespec="milliseconds"
            ),
            compact=compact,
        )
    assert ctr.count == 1

    assert len(open_encounters) == 1
    assert open_encounters[0]["epr_encounter_id"] == "thisisanencounterid8"
    assert open_encounters[0]["admitted_at"] == parse("2018-01-02T00:00:00.000Z")
    assert open_encounters[0]["discharged_at"] is None
    assert open_encounters[0]["deleted_at"] is None
    assert open_encounters[0]["location_uuid"] == location_uuid
    assert open_encounters[0]["patient_record_uuid"] == record_uuid
    if not compact:
        assert open_encounters[0]["encounter_type"] == "INPATIENT"
        assert open_encounters[0]["spo2_scale"] == 1
        assert open_encounters[0]["dh_product"][0]["uuid"] == dh_product_uuid
        assert open_encounters[0]["score_system_history"] == []
