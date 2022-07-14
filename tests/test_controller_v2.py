from typing import Callable, Dict, Generator, List, Optional

import pytest
from dateutil.parser import parse
from flask_batteries_included.sqldb import db

import dhos_encounters_api.blueprint_api.controller
from dhos_encounters_api.models.api_spec import EncounterResponse
from dhos_encounters_api.models.encounter import Encounter
from dhos_encounters_api.models.location_history import LocationHistory
from dhos_encounters_api.models.score_system_history import ScoreSystemHistory


@pytest.mark.usefixtures("mock_publish_msg", "app")
class TestControllerV2:
    @pytest.fixture(autouse=True)
    def pre_existing_nodes(self) -> Generator[None, None, None]:
        yield
        LocationHistory.query.delete()
        ScoreSystemHistory.query.delete()
        Encounter.query.delete()
        db.session.commit()

    @pytest.mark.parametrize(
        "epr_id,expected",
        [
            (
                None,
                [
                    "thisisanencounterid7",
                    "thisisanencounterid6",
                    "thisisanencounterid5",
                    "thisisanencounterid4",
                ],
            ),
            ("thisisanencounterid5", ["thisisanencounterid5"]),
        ],
    )
    def test_get_encounters_for_patient_success(
        self,
        encounter_factory: Callable,
        location_uuid: str,
        dh_product_uuid: str,
        record_uuid: str,
        patient_uuid: str,
        assert_valid_schema: Callable,
        epr_id: Optional[str],
        expected: List[str],
    ) -> None:
        encounter_old_open = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="thisisanencounterid7",
            encounter_type="INPATIENT",
            admitted_at="2018-01-01T00:00:00.000Z",
            patient_record_uuid=record_uuid,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
            location_history=[
                {
                    "location_uuid": location_uuid,
                    "arrived_at": "2018-01-01T00:00:00.000Z",
                }
            ],
        )
        encounter_older = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="thisisanencounterid4",
            encounter_type="INPATIENT",
            admitted_at="2018-01-01T00:00:00.000Z",
            discharged_at="2018-01-01T00:00:00.000Z",
            patient_record_uuid=record_uuid,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
            location_history=[
                {
                    "location_uuid": location_uuid,
                    "arrived_at": "2017-12-31T00:00:00.000Z",
                }
            ],
        )
        db.session.commit()
        encounter_newer = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="thisisanencounterid5",
            encounter_type="INPATIENT",
            admitted_at="2018-01-02T00:00:00.000Z",
            discharged_at="2018-01-02T00:00:00.000Z",
            patient_record_uuid=record_uuid,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
        )
        db.session.commit()

        encounter_newer_just = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="thisisanencounterid6",
            encounter_type="INPATIENT",
            admitted_at="2018-01-02T00:00:00.000Z",
            discharged_at="2018-01-02T00:00:00.000Z",
            patient_record_uuid=record_uuid,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
        )
        db.session.commit()

        actual_encounters: List[
            Dict
        ] = dhos_encounters_api.blueprint_api.controller.get_encounters_by_patient_or_epr_id(
            patient_id=patient_uuid, epr_encounter_id=epr_id
        )

        assert_valid_schema(EncounterResponse, actual_encounters, many=True)

        assert len(actual_encounters) == len(expected)
        for i, enc in enumerate(actual_encounters):
            assert enc["epr_encounter_id"] == expected[i]
        assert actual_encounters[0]["child_encounter_uuids"] == []

    def test_get_open_encounters_for_patient_unknown(self) -> None:
        open_encounters = dhos_encounters_api.blueprint_api.controller.get_open_encounters_for_patient(
            patient_id="P1", open_as_of="2018-01-01T00:00:00.000Z"
        )
        assert open_encounters == []

    def test_get_open_encounters_for_patient_success(
        self,
        encounter_factory: Callable,
        location_uuid: str,
        dh_product_uuid: str,
        record_uuid: str,
        patient_uuid: str,
        assert_valid_schema: Callable,
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
                {
                    "location_uuid": location_uuid,
                    "arrived_at": "2018-01-01T00:00:00.000Z",
                }
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
        open_encounters: List[
            Dict
        ] = dhos_encounters_api.blueprint_api.controller.get_open_encounters_for_patient(
            patient_id=patient_uuid, open_as_of="2018-01-01T00:00:00.000Z"
        )
        assert_valid_schema(EncounterResponse, open_encounters, many=True)
        assert len(open_encounters) == 1

        assert open_encounters[0]["epr_encounter_id"] == "thisisanencounterid8"
        assert open_encounters[0]["encounter_type"] == "INPATIENT"
        assert open_encounters[0]["admitted_at"] == parse("2018-01-02T00:00:00.000Z")
        assert open_encounters[0]["discharged_at"] is None
        assert open_encounters[0]["deleted_at"] is None
        assert open_encounters[0]["spo2_scale"] == 1
        assert open_encounters[0]["location_uuid"] == location_uuid
        assert open_encounters[0]["dh_product"][0]["uuid"] == dh_product_uuid
        assert open_encounters[0]["score_system_history"] == []
        assert open_encounters[0]["patient_record_uuid"] == record_uuid
        assert open_encounters[0]["child_encounter_uuids"] == []

    def test_get_open_encounters_child_encounter_uuids(
        self,
        encounter_factory: Callable,
        location_uuid: str,
        dh_product_uuid: str,
        record_uuid: str,
        patient_uuid: str,
        assert_valid_schema: Callable,
    ) -> None:
        """Tests that the correct obs set count is given for an encounter with obs sets."""
        encounter = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="thisisanencounterid",
            encounter_type="INPATIENT",
            admitted_at="2018-01-02T00:00:00.000Z",
            discharged_at=None,
            patient_record_uuid=record_uuid,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
        )
        db.session.commit()

        child_encounter = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="thisisanencounterid_child",
            encounter_type="INPATIENT",
            admitted_at="2018-01-02T00:00:00.000Z",
            discharged_at=None,
            patient_record_uuid=record_uuid,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
            child_of_encounter_uuid=encounter.uuid,
        )
        db.session.commit()

        grandchild_encounter = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="thisisanencounterid_grandchild",
            encounter_type="INPATIENT",
            admitted_at="2018-01-02T00:00:00.000Z",
            discharged_at=None,
            patient_record_uuid=record_uuid,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
            child_of_encounter_uuid=child_encounter.uuid,
        )
        db.session.commit()

        open_encounters: List[
            Dict
        ] = dhos_encounters_api.blueprint_api.controller.get_open_encounters_for_patient(
            patient_id=patient_uuid,
            open_as_of="2018-01-01T00:00:00.000Z",
            expanded=True,
        )
        assert_valid_schema(EncounterResponse, open_encounters, many=True)

        assert len(open_encounters) == 1

        assert open_encounters[0]["uuid"] == encounter.uuid
        assert open_encounters[0]["child_encounter_uuids"] == [
            child_encounter.uuid,
            grandchild_encounter.uuid,
        ]
        assert open_encounters[0]["modified"] is not None

    def test_get_encounters_for_epr_encounter_id_no_results(
        self, patient_uuid: str
    ) -> None:
        actual_encounters: List[
            Dict
        ] = dhos_encounters_api.blueprint_api.controller.get_encounters_by_patient_or_epr_id(
            patient_id=patient_uuid, epr_encounter_id="some_unknown_id"
        )
        assert actual_encounters == []

    def test_get_encounters(
        self,
        encounter_factory: Callable,
        location_uuid: str,
        dh_product_uuid: str,
        record_uuid: str,
        patient_uuid: str,
    ) -> None:
        encounter_oldest = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="thisisanencounterid_oldest",
            encounter_type="INPATIENT",
            admitted_at="2020-01-01T00:00:00.001Z",
            discharged_at=None,
            patient_record_uuid=record_uuid,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
        )
        db.session.commit()

        encounter_old = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="thisisanencounterid_old",
            encounter_type="INPATIENT",
            admitted_at="2020-01-01T00:00:00.001Z",
            discharged_at=None,
            patient_record_uuid=record_uuid,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
        )
        db.session.commit()

        encounter = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="thisisanencounterid_main",
            encounter_type="INPATIENT",
            admitted_at="2020-01-02T00:00:00.001Z",
            discharged_at=None,
            patient_record_uuid=record_uuid,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
        )
        db.session.commit()

        encounter_deleted = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="thisisanencounterid_deleted",
            encounter_type="INPATIENT",
            admitted_at="2020-01-02T00:00:00.001Z",
            discharged_at=None,
            deleted_at="2020-01-03T00:00:00.001Z",
            patient_record_uuid=record_uuid,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
        )
        db.session.commit()

        child_encounter = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="thisisanencounterid_child",
            encounter_type="INPATIENT",
            admitted_at="2020-01-02T00:00:00.001Z",
            discharged_at=None,
            patient_record_uuid=record_uuid,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
            child_of_encounter_uuid=encounter.uuid,
        )
        db.session.commit()

        grandchild_encounter = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="thisisanencounterid_grandchild",
            encounter_type="INPATIENT",
            admitted_at="2020-01-02T00:00:00.001Z",
            discharged_at=None,
            patient_record_uuid=record_uuid,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
            child_of_encounter_uuid=child_encounter.uuid,
        )
        db.session.commit()

        encounters: List[
            Dict
        ] = dhos_encounters_api.blueprint_api.controller.get_encounters(
            modified_since=encounter_old.modified,
            compact=False,
            show_deleted=False,
            show_children=False,
            expanded=False,
        )

        assert len(encounters) == 1

        encounters = dhos_encounters_api.blueprint_api.controller.get_encounters(
            modified_since=encounter_oldest.modified,
            compact=False,
            show_deleted=False,
            show_children=False,
            expanded=False,
        )

        assert len(encounters) == 2

        encounters = dhos_encounters_api.blueprint_api.controller.get_encounters(
            modified_since=encounter_oldest.modified,
            compact=False,
            show_deleted=True,
            show_children=False,
            expanded=False,
        )

        assert len(encounters) == 3

        encounters = dhos_encounters_api.blueprint_api.controller.get_encounters(
            modified_since=encounter_oldest.modified,
            compact=False,
            show_deleted=True,
            show_children=True,
            expanded=False,
        )

        assert len(encounters) == 5
