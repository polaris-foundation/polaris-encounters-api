from typing import Callable, Dict, List

import pytest
from flask import Flask

from dhos_encounters_api.blueprint_api.controller import (
    get_open_encounters_for_patients,
)


@pytest.mark.parametrize(
    "uuids_in,expect_uuids",
    [
        (["patient_uuid"], ["patient_uuid"]),
        (["not_a_patient"], []),
        (["patient_uuid", "not_a_patient"], ["patient_uuid"]),
    ],
)
def test_get_open_encounters_for_patients(
    app: Flask,
    encounter_factory: Callable,
    location_uuid: str,
    dh_product_uuid: str,
    record_uuid: str,
    patient_uuid: str,
    uuids_in: List[str],
    expect_uuids: List[str],
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
    uuids_in = [patient_uuid if s == "patient_uuid" else s for s in uuids_in]
    expect_uuids = [patient_uuid if s == "patient_uuid" else s for s in expect_uuids]

    open_encounters: List[Dict] = get_open_encounters_for_patients(
        patient_ids=uuids_in, open_as_of="2019-01-01T00:00:00.000Z"
    )
    assert [e["patient_uuid"] for e in open_encounters] == expect_uuids
