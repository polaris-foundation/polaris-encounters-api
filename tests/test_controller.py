from datetime import datetime
from typing import Callable, Dict, Generator, List, Optional, Tuple

import pytest
from dateutil.parser import parse
from flask import g
from flask_batteries_included.helpers import generate_uuid
from flask_batteries_included.helpers.error_handler import DuplicateResourceException
from flask_batteries_included.sqldb import db
from pytest_mock import MockFixture

import dhos_encounters_api.blueprint_api.controller
from dhos_encounters_api.blueprint_api import controller, publish
from dhos_encounters_api.blueprint_development import reset_database
from dhos_encounters_api.models.api_spec import EncounterResponse
from dhos_encounters_api.models.encounter import Encounter


@pytest.mark.usefixtures("mock_publish_msg", "app")
class TestController:
    @pytest.fixture
    def open_encounters(
        self, encounter_factory: Callable, dh_product_uuid: str
    ) -> Generator[List[str], None, None]:
        """Fixture creates multiple open encounters"""
        # patient uuid, encounter uuid, epr id, record, admitted date, discharged, deleted, parent
        data: List[
            Tuple[
                str,
                str,
                Optional[str],
                str,
                str,
                str,
                Optional[str],
                Optional[str],
                Optional[str],
            ]
        ] = [
            ("P1", "E1P1", None, "P1R1", "L1", "2020-01-01", None, None, None),
            (
                "P1",
                "E2P1",
                None,
                "P1R1",
                "L2",
                "2020-01-01",
                "2020-02-01",
                "2020-02-01",
                None,
            ),
            ("P2", "E1P2", None, "P2R1", "L1", "2019-12-01", None, None, None),
            ("P2", "E4P2", None, "P2R1", "L1", "2019-12-04", None, None, None),
            ("P2", "E3P2", None, "P2R1", "L1", "2019-12-04", None, None, "E4P2"),
            (
                "P2",
                "E2P2",
                None,
                "P2R1",
                "L1",
                "2019-12-02",
                None,
                "2019-12-31",
                "E3P2",
            ),
        ]

        for (
            patient,
            encounter,
            epr,
            record,
            locn,
            admitted,
            discharged,
            deleted,
            parent,
        ) in data:
            encounter_factory(
                patient_uuid=patient,
                uuid=encounter,
                location_uuid=locn,
                dh_product_uuid=dh_product_uuid,
                epr_encounter_id=epr,
                patient_record_uuid=record,
                admitted_at=admitted,
                discharged_at=None if discharged is None else discharged,
                deleted_at=None if deleted is None else deleted,
                child_of_encounter_uuid=parent,
            )

        yield [
            encounter
            for patient, encounter, epr, record, locn, admitted, discharged, deleted, parent in data
        ]

        # Clear fixtures after test
        reset_database()

    @pytest.mark.parametrize(
        "patient,expected", [("P1", ["E1P1"]), ("P2", ["E4P2", "E1P2"])]
    )
    def test_get_open_local_encounters_for_patient(
        self, open_encounters: List[str], patient: str, expected: List[str]
    ) -> None:
        result = controller.get_open_local_encounters_for_patient(patient)
        assert result == expected

    @pytest.mark.parametrize(
        "parent_encounter,show_deleted,expected",
        [("E4P2", False, ["E3P2"]), ("E4P2", True, ["E3P2", "E2P2"])],
    )
    def test_get_child_encounters_1(
        self,
        open_encounters: List[str],
        parent_encounter: str,
        show_deleted: bool,
        expected: List[str],
    ) -> None:
        result = controller.get_child_encounters(
            parent_encounter, show_deleted=show_deleted
        )
        assert result == expected

    def test_create_encounter_duplicate_epr_id(
        self,
        encounter_factory: Callable,
        record_uuid: str,
        patient_uuid: str,
        location_uuid: str,
        dh_product_uuid: str,
    ) -> None:
        encounter: Dict = {
            "location_uuid": location_uuid,
            "epr_encounter_id": "thisisanencounterid1",
            "patient_record_uuid": record_uuid,
            "patient_uuid": patient_uuid,
            "dh_product_uuid": dh_product_uuid,
        }
        controller.create_encounter(encounter)

        with pytest.raises(DuplicateResourceException):
            controller.create_encounter(encounter_data=encounter)

    def test_create_encounter_success(
        self,
        location_uuid: str,
        dh_product_uuid: str,
        record_uuid: str,
        patient_uuid: str,
        assert_valid_schema: Callable,
    ) -> None:
        encounter_data: Dict = {
            "location_uuid": location_uuid,
            "epr_encounter_id": "thisisanencounteri2",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "discharged_at": "2018-01-01T00:00:00.000Z",
            "patient_record_uuid": record_uuid,
            "patient_uuid": patient_uuid,
            "dh_product_uuid": dh_product_uuid,
            "location_history": [
                {
                    "location_uuid": location_uuid,
                    "arrived_at": "2018-01-01T00:00:00.000Z",
                }
            ],
        }
        actual_encounter: Dict = controller.create_encounter(
            encounter_data=encounter_data
        )
        assert_valid_schema(EncounterResponse, actual_encounter)
        assert (
            actual_encounter["epr_encounter_id"] == encounter_data["epr_encounter_id"]
        )

    def test_get_encounter_success(
        self,
        location_uuid: str,
        dh_product_uuid: str,
        record_uuid: str,
        patient_uuid: str,
        encounter_factory: Callable,
        assert_valid_schema: Callable,
    ) -> None:
        encounter = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="thisisanencounterid3",
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
        db.session.commit()
        actual_encounter: Dict = controller.get_encounter(encounter_id=encounter.uuid)
        assert_valid_schema(EncounterResponse, actual_encounter)

        assert encounter.epr_encounter_id == actual_encounter["epr_encounter_id"]
        assert encounter.is_deleted is False
        assert encounter.is_local is False
        assert encounter.to_dict().get("modified") is None
        assert isinstance(encounter.to_dict(expanded=True).get("modified"), datetime)
        assert (
            encounter.to_dict(expanded=True).get("created")
            == actual_encounter["created"]
        )
        location_history = encounter.to_dict()["location_history"]
        assert len(location_history) == 1
        assert location_history[0]["location_uuid"] == location_uuid
        assert isinstance(location_history[0]["created_at"], datetime)
        assert location_history[0]["arrived_at"] == parse("2018-01-01T00:00:00.000Z")

    def test_get_open_encounters(
        self,
        location_uuid: str,
        dh_product_uuid: str,
        record_uuid: str,
        patient_uuid: str,
        encounter_factory: Callable,
        assert_valid_schema: Callable,
    ) -> None:
        encounter: Encounter = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="thisisanencounterid",
            encounter_type="INPATIENT",
            admitted_at="2018-01-02T00:00:00.000Z",
            discharged_at=None,
            patient_record_uuid=record_uuid,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
            score_system="meows",
        )

        open_encounters: List[
            Dict
        ] = dhos_encounters_api.blueprint_api.controller.get_open_encounters_for_patient(
            patient_id=patient_uuid, open_as_of="2018-01-01T00:00:00.000Z"
        )
        assert len(open_encounters) == 1
        assert_valid_schema(EncounterResponse, open_encounters, many=True)

        assert open_encounters[0]["uuid"] == encounter.uuid

    def test_get_encounters_for_patient(
        self,
        location_uuid: str,
        dh_product_uuid: str,
        record_uuid: str,
        patient_uuid: str,
        encounter_factory: Callable,
        assert_valid_schema: Callable,
    ) -> None:
        """Tests that we get the expected encounters."""
        encounter_older = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="thisisanencounterid9",
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
        encounter_newer = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="thisisanencounterid10",
            encounter_type="INPATIENT",
            admitted_at="2018-01-02T00:00:00.000Z",
            discharged_at="2018-01-02T00:00:00.000Z",
            patient_record_uuid=record_uuid,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
        )
        encounter_newer_just = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="thisisanencounterid11",
            encounter_type="INPATIENT",
            admitted_at="2018-01-02T00:00:00.000Z",
            discharged_at="2018-01-02T00:00:00.000Z",
            patient_record_uuid=record_uuid,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
        )

        actual_encounters: List[
            Dict
        ] = dhos_encounters_api.blueprint_api.controller.get_encounters_by_patient_or_epr_id(
            patient_id=patient_uuid
        )

        assert_valid_schema(EncounterResponse, actual_encounters, many=True)

        assert len(actual_encounters) == 3
        assert actual_encounters[0]["uuid"] == encounter_newer_just.uuid
        assert actual_encounters[1]["uuid"] == encounter_newer.uuid
        assert actual_encounters[2]["uuid"] == encounter_older.uuid

    def test_get_child_encounters_2(
        self,
        encounter_factory: Callable,
        location_uuid: str,
        dh_product_uuid: str,
        record_uuid: str,
        patient_uuid: str,
    ) -> None:
        encounter_parent = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="epr_encounter_id_parent",
            encounter_type="INPATIENT",
            admitted_at="2018-01-01T00:00:00.000Z",
            patient_record_uuid=record_uuid,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
        )
        db.session.commit()

        encounter_child = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="epr_encounter_id_child",
            encounter_type="INPATIENT",
            admitted_at="2018-01-02T00:00:00.000Z",
            discharged_at="2018-01-02T00:00:00.000Z",
            patient_record_uuid=record_uuid,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
            child_of_encounter_uuid=encounter_parent.uuid,
        )
        db.session.commit()

        encounter_grandchild = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="epr_encounter_id_grandchild",
            encounter_type="INPATIENT",
            admitted_at="2018-01-02T00:00:00.000Z",
            discharged_at="2018-01-02T00:00:00.000Z",
            patient_record_uuid=record_uuid,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
            child_of_encounter_uuid=encounter_child.uuid,
        )
        db.session.commit()

        child_uuids: List[str] = controller.get_child_encounters(encounter_parent.uuid)
        assert set(child_uuids) == {encounter_child.uuid, encounter_grandchild.uuid}

    def test_get_child_encounters_unknown(self) -> None:
        # Unknown encounter returns an empty list of children
        child_uuids: List[str] = controller.get_child_encounters(generate_uuid())
        assert child_uuids == []

    def test_get_encounters_for_epr_encounter_id_nested(
        self,
        encounter_factory: Callable,
        assert_valid_schema: Callable,
        location_uuid: str,
        dh_product_uuid: str,
        record_uuid: str,
        patient_uuid: str,
    ) -> None:
        """Tests that we get the expected result with nested child encounters."""
        encounter_parent = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="epr_encounter_id_parent_1",
            encounter_type="INPATIENT",
            admitted_at="2018-01-01T00:00:00.000Z",
            patient_record_uuid=record_uuid,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
        )
        db.session.commit()
        encounter_child = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="epr_encounter_id_child_1",
            encounter_type="INPATIENT",
            admitted_at="2018-01-02T00:00:00.000Z",
            discharged_at="2018-01-02T00:00:00.000Z",
            patient_record_uuid=record_uuid,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
            child_of_encounter_uuid=encounter_parent.uuid,
        )
        db.session.commit()
        encounter_grandchild = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="epr_encounter_id_grandchild_1",
            encounter_type="INPATIENT",
            admitted_at="2018-01-02T00:00:00.000Z",
            discharged_at="2018-01-02T00:00:00.000Z",
            patient_record_uuid=record_uuid,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
            child_of_encounter_uuid=encounter_child.uuid,
        )
        db.session.commit()
        actual_encounters: List[
            Dict
        ] = dhos_encounters_api.blueprint_api.controller.get_encounters_by_patient_or_epr_id(
            epr_encounter_id="epr_encounter_id_parent_1"
        )
        assert_valid_schema(EncounterResponse, actual_encounters, many=True)
        assert len(actual_encounters) == 1

    def test_create_multiple_local_encounters(
        self,
        encounter_factory: Callable,
        dh_product_uuid: str,
        patient_uuid: str,
    ) -> None:
        test_ward = generate_uuid()

        record_uuid1: str = generate_uuid()
        record_uuid2: str = generate_uuid()
        patient_uuid1: str = generate_uuid()
        patient_uuid2: str = generate_uuid()

        encounter1 = encounter_factory(
            location_uuid=test_ward,
            epr_encounter_id="",
            encounter_type="INPATIENT",
            admitted_at="2018-01-01T00:00:00.000Z",
            discharged_at="2018-01-01T00:00:00.000Z",
            patient_record_uuid=record_uuid1,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
            location_history=[
                {"location_uuid": test_ward, "arrived_at": "2018-01-01T00:00:00.000Z"}
            ],
        )
        encounter2 = encounter_factory(
            location_uuid=test_ward,
            epr_encounter_id="",
            encounter_type="INPATIENT",
            admitted_at="2018-01-01T00:00:00.000Z",
            discharged_at="2018-01-01T00:00:00.000Z",
            patient_record_uuid=record_uuid1,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
            location_history=[
                {"location_uuid": test_ward, "arrived_at": "2018-01-01T00:00:00.000Z"}
            ],
        )
        db.session.commit()
        assert encounter1.uuid != encounter2.uuid

    def test_update_encounter_controller_success(
        self,
        app_context: None,
        assert_valid_schema: Callable,
        location_uuid: str,
        dh_product_uuid: str,
        record_uuid: str,
        patient_uuid: str,
        mocker: MockFixture,
    ) -> None:
        # Arrange
        encounter = Encounter.new(
            location_uuid=location_uuid,
            epr_encounter_id=generate_uuid(),
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
        db.session.commit()

        old_modified_date = encounter.modified
        g.jwt_claims = {"clinician_id": "some-user-uuid"}
        mock_publish_audit_event = mocker.patch.object(publish, "publish_audit_event")

        # Act
        result: Dict = controller.update_encounter(
            encounter_id=encounter.uuid, encounter_data={"encounter_type": "SOME_TYPE"}
        )

        # Assert
        assert_valid_schema(EncounterResponse, result)

        assert result["encounter_type"] == "SOME_TYPE"

        updated_encounter = Encounter.query.get(encounter.uuid)
        assert updated_encounter.modified != old_modified_date
        assert updated_encounter.modified_by == "some-user-uuid"
        mock_publish_audit_event.assert_called_once_with(
            event_type="encounter_modified",
            event_data={
                "clinician_id": "some-user-uuid",
                "encounter_id": encounter.uuid,
                "modifications": [
                    ("change", "encounter_type", ("INPATIENT", "SOME_TYPE"))
                ],
            },
        )

    def test_retrieve_patient_count_for_locations(
        self, open_encounters: List[str]
    ) -> None:
        result = controller.retrieve_patient_count_for_locations(
            ["L1", "L3"], open_as_of=None
        )

        assert result == {"L1": 2}
