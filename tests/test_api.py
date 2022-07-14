from datetime import datetime
from typing import Any, Callable, Dict, Generator, List, Optional

import draymed
import pytest
from flask.testing import FlaskClient
from flask_batteries_included.helpers import generate_uuid
from flask_batteries_included.helpers.error_handler import EntityNotFoundException
from flask_batteries_included.sqldb import db
from mock import Mock
from pytest_mock import MockFixture

from dhos_encounters_api.blueprint_api import publish
from dhos_encounters_api.models.api_spec import EncounterResponse
from dhos_encounters_api.models.encounter import Encounter
from dhos_encounters_api.models.location_history import LocationHistory
from dhos_encounters_api.models.score_system_history import ScoreSystemHistory

WARD_LOCATION_TYPE = draymed.codes.code_from_name("ward", category="location")
HOSPITAL_LOCATION_TYPE = draymed.codes.code_from_name("hospital", category="location")


@pytest.mark.usefixtures("app", "jwt_clinician", "mock_publish_msg")
class TestApi:
    @pytest.fixture(autouse=True)
    def pre_existing_nodes(self) -> Generator[None, None, None]:
        yield
        LocationHistory.query.delete()
        ScoreSystemHistory.query.delete()
        Encounter.query.delete()
        db.session.commit()

    def test_request_with_jwt(
        self, client: FlaskClient, patient_uuid: str, mock_bearer_validation: Any
    ) -> None:
        r = client.get(
            f"/dhos/v2/encounter/latest?patient_id={patient_uuid}&open_as_of=2018-01-01T00:00:00.000Z",
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert mock_bearer_validation.called_once_with("TOKEN")

    def test_post_encounter_invalid(self, client: FlaskClient) -> None:
        response = client.post(
            "/dhos/v2/encounter",
            headers={"Authorization": "Bearer TOKEN"},
            json={"test": "value"},
        )
        assert response.status_code == 400

    def test_post_encounter_success(
        self,
        client: FlaskClient,
        mocker: MockFixture,
        patient_uuid: str,
    ) -> None:
        payload = {
            "location_uuid": "L1",
            "epr_encounter_id": "thisisanencounterid",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "discharged_at": "2018-01-01T00:00:00.000Z",
            "patient_record_uuid": "R1",
            "patient_uuid": patient_uuid,
            "dh_product_uuid": "eae12da8-410b-4a60-858b-d554d511f26f",
            "score_system": "news2",
        }
        expected = {"some": "return"}
        mocker.patch(
            "dhos_encounters_api.blueprint_api.controller.create_encounter",
            headers={"Authorization": "Bearer TOKEN"},
            return_value=expected,
        )
        response = client.post(
            "/dhos/v2/encounter",
            headers={"Authorization": "Bearer TOKEN"},
            json=payload,
        )
        assert response.json == expected

    def test_get_encounter_invalid(self, client: FlaskClient) -> None:
        response = client.get(
            "/dhos/v1/encounter/something",
            json={"test": "value"},
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 400

    def test_post_encounter_success_2(
        self, client: FlaskClient, mocker: MockFixture
    ) -> None:
        payload = {
            "location_uuid": "L1",
            "epr_encounter_id": "thisisanencounterid",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "discharged_at": "2018-01-01T00:00:00.000Z",
            "patient_record_uuid": "R1",
            "patient_uuid": "P1",
            "dh_product_uuid": "eae12da8-410b-4a60-858b-d554d511f26f",
            "score_system": "news2",
        }
        expected = {"some": "return"}
        mocker.patch(
            "dhos_encounters_api.blueprint_api.controller.create_encounter",
            headers={"Authorization": "Bearer TOKEN"},
            return_value=expected,
        )
        response = client.post(
            "/dhos/v2/encounter",
            headers={"Authorization": "Bearer TOKEN"},
            json=payload,
        )
        assert response.json == expected

    def test_get_encounter_unknown(
        self, client: FlaskClient, mocker: MockFixture
    ) -> None:
        mock_get = mocker.patch(
            "dhos_encounters_api.blueprint_api.controller.get_encounter"
        )
        mock_get.side_effect = EntityNotFoundException()
        response = client.get(
            "/dhos/v1/encounter/unknown", headers={"Authorization": "Bearer TOKEN"}
        )
        assert response.status_code == 404

    def test_get_encounter_success(
        self, client: FlaskClient, mocker: MockFixture
    ) -> None:
        expected = {"some": "return"}
        mocker.patch(
            "dhos_encounters_api.blueprint_api.controller.get_encounter",
            return_value=expected,
        )
        response = client.get(
            "/dhos/v1/encounter/known-uuid", headers={"Authorization": "Bearer TOKEN"}
        )
        assert response.json == expected

    def test_get_child_encounters_invalid(self, client: FlaskClient) -> None:
        response = client.get(
            "/dhos/v1/encounter/something/children",
            headers={"Authorization": "Bearer TOKEN"},
            json={"test": "value"},
        )
        assert response.status_code == 400

    def test_get_child_encounters_success(
        self, client: FlaskClient, mocker: MockFixture
    ) -> None:
        expected = ["uuid1", "uuid2"]
        mocker.patch(
            "dhos_encounters_api.blueprint_api.controller.get_child_encounters",
            return_value=expected,
        )
        response = client.get(
            "/dhos/v1/encounter/known-uuid/children",
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.json == expected

    def test_patch_encounter_failure(self, client: FlaskClient) -> None:
        response = client.patch(
            "/dhos/v1/encounter/something",
            headers={"Authorization": "Bearer TOKEN"},
            json={"test": "value"},
        )
        assert response.status_code == 400

    def test_get_encounters_for_patient_missing_id(self, client: FlaskClient) -> None:
        response = client.get(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}
        )
        assert response.status_code == 400

    def test_get_encounters_for_patient_json_body(self, client: FlaskClient) -> None:
        response = client.get(
            "/dhos/v2/encounter?patient_id=something",
            json={"test": "value"},
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 400

    def test_get_encounters_for_patient_unknown(
        self, client: FlaskClient, mocker: MockFixture
    ) -> None:
        mock_get = mocker.patch(
            "dhos_encounters_api.blueprint_api.controller.get_encounters_by_patient_or_epr_id"
        )
        mock_get.side_effect = EntityNotFoundException()
        response = client.get(
            "/dhos/v2/encounter?patient_id=unknown",
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 404

    def test_get_encounters_for_patient_success(
        self, client: FlaskClient, mocker: MockFixture
    ) -> None:
        expected = [{"uuid": "encounter1"}, {"uuid": "encounter2"}]
        mocker.patch(
            "dhos_encounters_api.blueprint_api.controller.get_encounters_by_patient_or_epr_id",
            return_value=expected,
        )
        response = client.get(
            "/dhos/v2/encounter?patient_id=known",
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.json == expected

    def test_get_latest_encounter_for_patient(
        self, client: FlaskClient, mocker: MockFixture
    ) -> None:
        expected = [
            {"uuid": "encounter1", "discharged_at": None, "deleted_at": None},
            {"uuid": "encounter2", "discharged_at": None, "deleted_at": None},
        ]
        mocker.patch(
            "dhos_encounters_api.blueprint_api.controller.get_encounters_by_patient_or_epr_id",
            return_value=expected,
        )
        response = client.get(
            "/dhos/v2/encounter/latest?patient_id=X",
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 200
        assert response.json == expected[0]

    def test_get_encounter_by_id(
        self,
        client: FlaskClient,
        patient_uuid: str,
    ) -> None:
        data = {
            "location_uuid": "W1",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "patient_record_uuid": "R1",
            "patient_uuid": patient_uuid,
            "dh_product_uuid": "DH1234",
            "epr_encounter_id": "1234",
            "score_system": "news2",
        }
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        assert response.status_code == 200
        json: Optional[Dict] = response.json
        assert json is not None

        response = client.get(
            "/dhos/v1/encounter/" + str(json["uuid"]),
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 200
        assert data["epr_encounter_id"] == json["epr_encounter_id"]

    def test_duplicate_encounter_post(
        self,
        client: FlaskClient,
        patient_uuid: str,
    ) -> None:
        data = {
            "location_uuid": "W1",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "patient_record_uuid": "R1",
            "patient_uuid": patient_uuid,
            "dh_product_uuid": "DH1234",
            "epr_encounter_id": "1234",
            "score_system": "news2",
        }
        client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        assert response.status_code == 409

    def test_update_encounter_fail(
        self,
        client: FlaskClient,
        patient_uuid: str,
    ) -> None:
        data = {
            "location_uuid": "W1",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "patient_record_uuid": "R1",
            "patient_uuid": patient_uuid,
            "dh_product_uuid": "DH1234",
            "score_system": "news2",
        }
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        json: Optional[Dict] = response.json
        assert json is not None
        uuid = json["uuid"]
        data = {"child_of_encounter_uuid": "P2"}
        response = client.patch(
            f"/dhos/v1/encounter/{uuid}",
            headers={"Authorization": "Bearer TOKEN"},
            json=data,
        )
        assert response.status_code == 422

    def test_update_encounter_success(
        self,
        client: FlaskClient,
        mocker: MockFixture,
        patient_uuid: str,
        encounter_factory: Callable,
    ) -> None:
        encounter_factory(
            uuid="P1",
            location_uuid="L1",
            patient_record_uuid=generate_uuid(),
            patient_uuid=generate_uuid(),
            dh_product_uuid=generate_uuid(),
        )
        db.session.commit()
        data = {
            "location_uuid": "W1",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "patient_record_uuid": "R1",
            "patient_uuid": patient_uuid,
            "dh_product_uuid": "DH1234",
            "score_system": "news2",
        }
        mock_encounter_updated = mocker.patch.object(
            publish, "publish_encounter_update"
        )
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        assert response.status_code == 200
        json: Optional[Dict] = response.json
        assert json is not None
        uuid = json["uuid"]
        data = {"child_of_encounter_uuid": "P1"}
        response = client.patch(
            f"/dhos/v1/encounter/{uuid}",
            headers={"Authorization": "Bearer TOKEN"},
            json=data,
        )
        json = response.json
        assert json is not None

        assert response.status_code == 200
        expected = {
            "location_uuid": "W1",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "patient_record_uuid": "R1",
            "dh_product_uuid": "DH1234",
            "child_of_encounter_uuid": "P1",
            "score_system": "news2",
        }
        assert json["location_uuid"] == expected["location_uuid"]
        assert json["child_of_encounter_uuid"] == expected["child_of_encounter_uuid"]
        assert mock_encounter_updated.call_count == 2

    def test_reinstate_encounter_success(
        self,
        client: FlaskClient,
        mocker: MockFixture,
        patient_uuid: str,
    ) -> None:
        # A01 - receive new encounter POST
        mocker.patch.object(publish, "publish_encounter_update")
        data = {
            "location_uuid": "W1",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "patient_record_uuid": "R1",
            "patient_uuid": patient_uuid,
            "epr_encounter_id": "EPRZ",
            "dh_product_uuid": "DH1234",
            "score_system": "news2",
        }
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        assert response.status_code == 200
        json: Optional[Dict] = response.json
        assert json is not None

        uuid1 = json["uuid"]

        # A23 - cancel encounter
        data = {"deleted_at": "2018-01-01T00:00:00.000Z"}
        response = client.patch(
            f"/dhos/v1/encounter/{uuid1}",
            headers={"Authorization": "Bearer TOKEN"},
            json=data,
        )
        json = response.json
        assert json is not None
        assert json["deleted_at"] == data["deleted_at"]

        # A01 - create separate new encounter
        data = {
            "location_uuid": "W1",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "patient_record_uuid": "R1",
            "patient_uuid": patient_uuid,
            "dh_product_uuid": "DH1234",
            "epr_encounter_id": "EPRZ",
            "score_system": "news2",
        }
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        json = response.json
        assert json is not None
        assert response.status_code == 200
        uuid2 = json["uuid"]
        assert uuid1 != uuid2

        # A01 - reject as duplicate
        data = {
            "location_uuid": "W1",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "patient_record_uuid": "R1",
            "patient_uuid": patient_uuid,
            "dh_product_uuid": "DH1234",
            "epr_encounter_id": "EPRZ",
            "score_system": "news2",
        }
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        assert response.status_code == 409

    def test_get_empty_open_encounters(
        self,
        client: FlaskClient,
        patient_uuid: str,
    ) -> None:
        data = {
            "location_uuid": "W1",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "discharged_at": "2018-01-01T01:01:00.000Z",
            "patient_record_uuid": "R1",
            "patient_uuid": patient_uuid,
            "dh_product_uuid": "DH1234",
            "score_system": "news2",
        }
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        assert response.status_code == 200

    def test_get_closed_latest_encounters(
        self,
        client: FlaskClient,
        patient_uuid: str,
    ) -> None:
        data = {
            "location_uuid": "W1",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "discharged_at": "2018-01-01T01:01:00.000Z",
            "patient_record_uuid": "R1",
            "patient_uuid": patient_uuid,
            "dh_product_uuid": "DH1234",
            "score_system": "news2",
        }
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        assert response.status_code == 200
        json: Optional[Dict] = response.json
        assert json is not None
        response = client.get(
            f"/dhos/v2/encounter/latest?patient_id={patient_uuid}",
            headers={"Authorization": "Bearer TOKEN"},
        )
        json = response.json
        assert json is not None
        assert response.status_code == 200
        assert json["location_uuid"] == data["location_uuid"]

    def test_get_latest_encounters_none(
        self,
        client: FlaskClient,
        patient_uuid: str,
    ) -> None:
        response = client.get(
            f"/dhos/v2/encounter/latest?patient_id={patient_uuid}",
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 404

    def test_get_latest_encounters_none_post(self, client: FlaskClient) -> None:
        post = ["P1234"]
        response = client.post(
            f"/dhos/v2/encounter/latest",
            headers={"Authorization": "Bearer TOKEN"},
            json=post,
        )
        assert response.status_code == 200
        assert isinstance(response.json, Dict)
        assert response.json == {}

    def test_get_latest_encounters_post(
        self,
        client: FlaskClient,
        patient_uuid: str,
        assert_valid_schema: Callable,
    ) -> None:
        data = {
            "location_uuid": "W1",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "discharged_at": "2018-01-01T01:01:00.000Z",
            "patient_record_uuid": "R1",
            "patient_uuid": patient_uuid,
            "dh_product_uuid": "DH1234",
            "score_system": "news2",
        }
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        assert response.status_code == 200
        post = [patient_uuid]
        response = client.post(
            f"/dhos/v2/encounter/latest",
            headers={"Authorization": "Bearer TOKEN"},
            json=post,
        )
        assert response.status_code == 200
        json: Optional[Dict] = response.json
        assert json is not None
        for patient_id in json:
            assert_valid_schema(EncounterResponse, json[patient_id])

        assert json[patient_uuid]["admitted_at"] == data["admitted_at"]

    def test_get_latest_encounters_post_compact(self, client: FlaskClient) -> None:
        data = {
            "location_uuid": "W1",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "discharged_at": "2018-01-01T01:01:00.000Z",
            "patient_record_uuid": "R1",
            "patient_uuid": "P1234",
            "dh_product_uuid": "DH1234",
            "score_system": "news2",
        }
        response = client.post(
            "/dhos/v2/encounter?compact=true",
            headers={"Authorization": "Bearer TOKEN"},
            json=data,
        )
        assert response.status_code == 200
        post = ["P1234"]
        response = client.post(
            f"/dhos/v2/encounter/latest",
            headers={"Authorization": "Bearer TOKEN"},
            json=post,
        )
        json: Optional[Dict] = response.json
        assert json is not None
        assert response.status_code == 200
        assert isinstance(response.json, Dict)
        assert json["P1234"]["admitted_at"] == data["admitted_at"]

    def test_get_latest_open_encounters_post(
        self,
        client: FlaskClient,
        patient_uuid: str,
    ) -> None:
        data = {
            "location_uuid": "W1",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "patient_record_uuid": "R1",
            "patient_uuid": patient_uuid,
            "dh_product_uuid": "DH1234",
            "score_system": "news2",
        }
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        assert response.status_code == 200
        post = [patient_uuid]
        response = client.post(
            f"/dhos/v2/encounter/latest?open_as_of=2018-01-01T00:00:00.000Z",
            headers={"Authorization": "Bearer TOKEN"},
            json=post,
        )
        json: Optional[Dict] = response.json
        assert json is not None
        assert response.status_code == 200
        assert json[patient_uuid]["admitted_at"] == data["admitted_at"]

    def test_get_latest_open_encounters_post_empty(
        self,
        client: FlaskClient,
        patient_uuid: str,
    ) -> None:
        data = {
            "location_uuid": "W1",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "discharged_at": "2018-01-01T01:01:00.000Z",
            "patient_record_uuid": "R1",
            "patient_uuid": patient_uuid,
            "dh_product_uuid": "DH1234",
            "score_system": "news2",
        }
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        assert response.status_code == 200
        post = ["P1234"]
        response = client.post(
            f"/dhos/v2/encounter/latest?open_as_of=2018-01-01T00:00:00.000Z",
            headers={"Authorization": "Bearer TOKEN"},
            json=post,
        )
        assert response.status_code == 200
        assert response.json == {}

    def test_change_patient_record_from_encounter(
        self,
        client: FlaskClient,
        patient_uuid: str,
    ) -> None:
        data = {
            "location_uuid": "W1",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "discharged_at": "2018-01-01T01:01:00.000Z",
            "patient_record_uuid": "R1",
            "patient_uuid": patient_uuid,
            "dh_product_uuid": "DH1234",
            "score_system": "news2",
        }
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        assert response.status_code == 200
        json: Optional[Dict] = response.json
        assert json is not None
        uuid = json["uuid"]
        data = {"patient_record_uuid": "R2"}
        response = client.patch(
            f"/dhos/v1/encounter/{uuid}",
            headers={"Authorization": "Bearer TOKEN"},
            json=data,
        )
        json = response.json
        assert json is not None
        assert response.status_code == 200
        assert json["patient_record_uuid"] == "R2"

    def test_change_location_from_encounter(
        self,
        client: FlaskClient,
        patient_uuid: str,
    ) -> None:
        data = {
            "location_uuid": "W1",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "discharged_at": "2018-01-01T01:01:00.000Z",
            "patient_record_uuid": "R1",
            "patient_uuid": patient_uuid,
            "dh_product_uuid": "DH1234",
            "score_system": "news2",
        }
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        assert response.status_code == 200
        json: Optional[Dict] = response.json
        assert json is not None
        uuid = json["uuid"]
        data = {"location_uuid": "W2"}

        response = client.patch(
            f"/dhos/v1/encounter/{uuid}",
            headers={"Authorization": "Bearer TOKEN"},
            json=data,
        )
        json = response.json
        assert json is not None
        assert response.status_code == 200
        assert json["location_uuid"] == "W2"

    def test_child_of_latest_encounter(
        self,
        client: FlaskClient,
        patient_uuid: str,
    ) -> None:
        data = {
            "location_uuid": "W1",
            "epr_encounter_id": "E1",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:01.000Z",
            "patient_record_uuid": "R1",
            "patient_uuid": patient_uuid,
            "dh_product_uuid": "DH1234",
            "score_system": "news2",
        }
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        assert response.status_code == 200
        json: Optional[Dict] = response.json
        assert json is not None
        e1_uuid = json["uuid"]

        data = {
            "location_uuid": "W1",
            "epr_encounter_id": "E2",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-02T00:00:01.000Z",
            "patient_record_uuid": "R1",
            "patient_uuid": patient_uuid,
            "dh_product_uuid": "DH1234",
            "score_system": "news2",
        }
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        json = response.json
        assert json is not None
        assert response.status_code == 200
        e2_uuid = json["uuid"]

        response = client.get(
            f"/dhos/v2/encounter/latest?patient_id={patient_uuid}&open_as_of=2018-01-01T00:00:00.000Z",
            headers={"Authorization": "Bearer TOKEN"},
        )
        json = response.json
        assert json is not None
        assert response.status_code == 200
        assert json["epr_encounter_id"] == "E2"

        data = {"child_of_encounter_uuid": e1_uuid}
        response = client.patch(
            f"/dhos/v1/encounter/{e2_uuid}",
            headers={"Authorization": "Bearer TOKEN"},
            json=data,
        )
        json = response.json
        assert json is not None
        assert response.status_code == 200
        assert json["child_of_encounter_uuid"] == e1_uuid

        response = client.get(
            f"/dhos/v2/encounter/latest?patient_id={patient_uuid}&open_as_of=2017-01-01T00:00:00.000Z",
            headers={"Authorization": "Bearer TOKEN"},
        )
        json = response.json
        assert json is not None
        assert response.status_code == 200
        assert json["epr_encounter_id"] == "E1"

    def test_delete_parent_from_encounter(
        self,
        client: FlaskClient,
        patient_uuid: str,
    ) -> None:
        data = {
            "location_uuid": "W1",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "patient_record_uuid": "R1",
            "dh_product_uuid": "DH1234",
            "patient_uuid": patient_uuid,
            "epr_encounter_id": "1234",
            "score_system": "news2",
        }
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        assert response.status_code == 200
        json: Optional[Dict] = response.json
        assert json is not None
        parent_uuid = json["uuid"]

        data = {
            "location_uuid": "W1",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "patient_record_uuid": "R1",
            "patient_uuid": patient_uuid,
            "dh_product_uuid": "DH1234",
            "epr_encounter_id": "5678",
            "child_of_encounter_uuid": parent_uuid,
            "score_system": "news2",
        }
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        json = response.json
        assert json is not None
        assert response.status_code == 200
        child_uuid = json["uuid"]

        data = {"child_of_encounter_uuid": parent_uuid}
        response = client.delete(
            f"/dhos/v1/encounter/{child_uuid}",
            headers={"Authorization": "Bearer TOKEN"},
            json=data,
        )
        json = response.json
        assert json is not None
        assert response.status_code == 200
        assert "child_of_encounter_uuid" not in json

    @pytest.mark.parametrize(
        "open_as_of,expect_result",
        [
            ("2017-01-01T01:01:00.000+00:00", True),
            ("2018-01-01T01:01:00.000+00:00", False),
            (None, False),
        ],
    )
    def test_get_encounters_for_location(
        self,
        client: FlaskClient,
        open_as_of: Optional[str],
        expect_result: bool,
    ) -> None:
        data = {
            "location_uuid": "W1",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "discharged_at": "2018-01-01T01:01:00.000Z",
            "patient_record_uuid": "R1",
            "patient_uuid": "P1",
            "dh_product_uuid": "DH1234",
            "score_system": "news2",
        }
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        assert response.status_code == 200
        post = ["W1"]
        response = client.post(
            f"/dhos/v1/encounter/locations",
            headers={"Authorization": "Bearer TOKEN"},
            query_string={"open_as_of": open_as_of},
            json=post,
        )
        assert response.status_code == 200
        assert isinstance(response.json, List)
        json: List[Dict] = response.json if response.json else []
        if expect_result:
            assert json[0]["admitted_at"] == data["admitted_at"]
            assert json[0]["patient_record_uuid"] == "R1"
        else:
            assert json == []

    @pytest.mark.parametrize(
        "open_as_of,expect_result",
        [
            ("2017-01-01T01:01:00.000+00:00", True),
            ("2018-01-01T01:01:00.000+00:00", False),
            (None, False),
        ],
    )
    def test_get_encounters_for_patients(
        self,
        client: FlaskClient,
        open_as_of: Optional[str],
        expect_result: bool,
        patient_uuid: str,
        record_uuid: str,
    ) -> None:
        data = {
            "location_uuid": "W1",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "discharged_at": "2018-01-01T01:01:00.000Z",
            "patient_record_uuid": record_uuid,
            "patient_uuid": patient_uuid,
            "dh_product_uuid": "DH1234",
            "score_system": "news2",
        }
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        assert response.status_code == 200
        post = [patient_uuid]
        response = client.post(
            f"/dhos/v1/encounter/patients",
            headers={"Authorization": "Bearer TOKEN"},
            query_string={"open_as_of": open_as_of},
            json=post,
        )
        assert response.status_code == 200
        assert isinstance(response.json, List)
        if expect_result:
            assert response.json[0]["admitted_at"] == data["admitted_at"]
            assert response.json[0]["patient_record_uuid"] == record_uuid
            assert response.json[0]["patient_uuid"] == patient_uuid
        else:
            assert response.json == []

    @pytest.mark.parametrize(
        "open_as_of,expected",
        [
            ("2017-01-01T01:01:00.000+00:00", {"W1": 1}),
            ("2018-01-01T01:01:00.000+00:00", {}),
            (None, {}),
        ],
    )
    def test_get_patient_count_for_locations(
        self,
        client: FlaskClient,
        open_as_of: Optional[str],
        expected: Dict,
    ) -> None:
        data = {
            "location_uuid": "W1",
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "discharged_at": "2018-01-01T01:01:00.000Z",
            "patient_record_uuid": "R1",
            "patient_uuid": "P1",
            "dh_product_uuid": "DH1234",
            "score_system": "news2",
        }
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        assert response.status_code == 200
        post = ["W1"]
        response = client.post(
            f"/dhos/v1/encounter/locations/patient_count",
            headers={"Authorization": "Bearer TOKEN"},
            query_string={"open_as_of": open_as_of},
            json=post,
        )
        assert response.status_code == 200
        assert response.json == expected


@pytest.mark.usefixtures(
    "app",
    "jwt_clinician",
)
class TestSpo2ScaleChange:
    @pytest.fixture
    def mock_record_audit_message(self, mocker: MockFixture) -> Mock:
        return mocker.patch.object(publish, "publish_audit_event")

    @pytest.fixture
    def mock_publish_score_system_change(self, mocker: MockFixture) -> Mock:
        return mocker.patch.object(publish, "publish_score_system_change")

    @pytest.fixture(autouse=True)
    def pytest_fixtures(self, mock_publish_msg: Mock) -> None:
        pass

    @pytest.mark.parametrize(
        ["jwt_extra_claims", "expected_status"],
        [
            ({"can_edit_ews": True}, 200),
            ({"can_edit_ews": False}, 403),
            ({}, 403),
        ],
    )
    def test_create_new_encounter_with_spo2(
        self,
        mock_record_audit_message: Mock,
        client: FlaskClient,
        record_uuid: str,
        product_send_uuid: str,
        location_uuid: str,
        patient_uuid: str,
        jwt_extra_claims: Dict,
        expected_status: int,
    ) -> None:
        data = {
            "location_uuid": location_uuid,
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "patient_record_uuid": record_uuid,
            "patient_uuid": patient_uuid,
            "dh_product_uuid": product_send_uuid,
            "score_system": "news2",
            "spo2_scale": 2,
        }
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        assert response.status_code == expected_status
        json: Optional[Dict] = response.json
        assert json is not None
        if expected_status == 200:
            assert json["spo2_scale"] == 2

    @pytest.mark.parametrize(
        ["jwt_extra_claims", "expected_status"],
        [
            ({"can_edit_ews": True}, 200),
            ({"can_edit_ews": False}, 403),
            ({}, 403),
        ],
    )
    def test_update_new_encounter_with_spo2(
        self,
        mock_record_audit_message: Mock,
        mock_publish_score_system_change: Mock,
        client: FlaskClient,
        record_uuid: str,
        product_send_uuid: str,
        location_uuid: str,
        patient_uuid: str,
        jwt_extra_claims: Dict,
        expected_status: int,
        mock_publish_msg: Mock,
        jwt_clinician: str,
    ) -> None:
        data = {
            "location_uuid": location_uuid,
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "patient_record_uuid": record_uuid,
            "patient_uuid": patient_uuid,
            "dh_product_uuid": product_send_uuid,
            "score_system": "news2",
            "spo2_scale": 1,
        }
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        json: Optional[Dict] = response.json
        assert json is not None

        data = {"spo2_scale": 2}
        response = client.patch(
            f"/dhos/v1/encounter/{json['uuid']}",
            json=data,
            headers={"Authorization": "Bearer TOKEN"},
        )
        json = response.json
        assert json is not None

        if expected_status == 200:
            assert json["spo2_scale"] == 2
            assert json["score_system_history"][0]["previous_spo2_scale"] == 1
            assert json["score_system_history"][0]["spo2_scale"] == 2
            assert json["score_system_history"][0]["created_by"] == jwt_clinician
            assert json["score_system_history"][0]["changed_by"] == jwt_clinician
            assert mock_publish_msg.call_count == 2
        else:
            assert mock_publish_msg.call_count == 1

    @pytest.mark.parametrize(
        ["jwt_extra_claims", "expected_status", "call_count"],
        [
            ({"can_edit_ews": True}, 200, 2),
            ({"can_edit_ews": False}, 403, 1),
            ({}, 403, 1),
        ],
    )
    def test_update_encounter_with_spo2(
        self,
        mock_record_audit_message: Mock,
        mock_publish_score_system_change: Mock,
        client: FlaskClient,
        record_uuid: str,
        product_send_uuid: str,
        location_uuid: str,
        patient_uuid: str,
        jwt_extra_claims: Dict,
        expected_status: int,
        call_count: int,
    ) -> None:
        data = {
            "location_uuid": location_uuid,
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "patient_record_uuid": record_uuid,
            "patient_uuid": patient_uuid,
            "dh_product_uuid": product_send_uuid,
            "spo2_scale": 1,
            "score_system": "news2",
        }
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        assert response.status_code == 200
        json: Optional[Dict] = response.json
        assert json is not None
        assert 1 == json["spo2_scale"]

        uuid = json["uuid"]
        data = {"spo2_scale": 2}

        response = client.patch(
            f"/dhos/v1/encounter/{uuid}",
            headers={"Authorization": "Bearer TOKEN"},
            json=data,
        )
        json = response.json
        assert json is not None
        assert response.status_code == expected_status
        assert mock_record_audit_message.call_count == call_count

        if expected_status == 200:
            assert json["spo2_scale"] == 2
            assert (
                mock_record_audit_message.call_args.kwargs["event_type"]
                == "encounter_modified"
            )
        else:
            assert (
                mock_record_audit_message.call_args.kwargs["event_type"]
                == "ews_change_failure"
            )

    @pytest.mark.parametrize(
        ["jwt_extra_claims", "expected_status"],
        [({"can_edit_ews": True, "system_id": "dhos_robot"}, 200)],
    )
    def test_update_spo2_changed_time(
        self,
        mock_record_audit_message: Mock,
        mock_publish_score_system_change: Mock,
        client: FlaskClient,
        record_uuid: str,
        product_send_uuid: str,
        location_uuid: str,
        patient_uuid: str,
        jwt_extra_claims: Dict,
        clinician: str,
        expected_status: int,
    ) -> None:
        data = {
            "location_uuid": location_uuid,
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "patient_record_uuid": record_uuid,
            "patient_uuid": patient_uuid,
            "dh_product_uuid": product_send_uuid,
            "score_system": "news2",
            "spo2_scale": 1,
        }
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        assert response.status_code == 200
        json: Optional[Dict] = response.json
        assert json is not None
        uuid = json["uuid"]
        data = {"spo2_scale": 2}

        response = client.patch(
            f"/dhos/v1/encounter/{uuid}",
            headers={"Authorization": "Bearer TOKEN"},
            json=data,
        )
        json = response.json
        assert json is not None

        assert response.status_code == expected_status
        assert mock_record_audit_message.call_count == 2

        assert json["spo2_scale"] == 2

        scale_history_id = json["score_system_history"][0]["uuid"]

        scale_change_data = {"changed_time": "2019-06-11T06:06:06.411Z"}
        response = client.patch(
            f"/dhos/v1/score_system_history/{scale_history_id}",
            headers={"Authorization": "Bearer TOKEN"},
            json=scale_change_data,
        )
        json = response.json
        assert json is not None

        assert response.status_code == 200
        assert json["changed_time"] == scale_change_data["changed_time"]
        assert json["changed_by"] == clinician

    @pytest.mark.parametrize(
        ["jwt_extra_claims", "expected_status"], [({"can_edit_ews": True}, 200)]
    )
    def test_update_encounter_with_spo2_set_but_unchanged(
        self,
        mock_record_audit_message: Mock,
        mock_publish_score_system_change: Mock,
        client: FlaskClient,
        record_uuid: str,
        product_send_uuid: str,
        location_uuid: str,
        patient_uuid: str,
        jwt_extra_claims: Dict,
        expected_status: int,
    ) -> None:
        data = {
            "location_uuid": location_uuid,
            "encounter_type": "INPATIENT",
            "admitted_at": "2018-01-01T00:00:00.000Z",
            "patient_record_uuid": record_uuid,
            "patient_uuid": patient_uuid,
            "dh_product_uuid": product_send_uuid,
            "score_system": "news2",
            "spo2_scale": 2,
        }
        response = client.post(
            "/dhos/v2/encounter", headers={"Authorization": "Bearer TOKEN"}, json=data
        )
        assert response.status_code == 200
        json: Optional[Dict] = response.json
        assert json is not None
        uuid = json["uuid"]
        data = {"spo2_scale": 2}

        response = client.patch(
            f"/dhos/v1/encounter/{uuid}",
            headers={"Authorization": "Bearer TOKEN"},
            json=data,
        )
        json = response.json
        assert json is not None
        assert response.status_code == expected_status

        # We set the attribute to the same value so there isn't an audit message.
        mock_record_audit_message.assert_not_called()

        if expected_status == 200:
            assert json["score_system_history"] == []
            assert json["spo2_scale"] == 2

    @pytest.mark.parametrize("mock_uuid4", [("1A2B3C")], indirect=True)
    def test_publish_valid_encounter(
        self, mock_publish_msg: Mock, mock_uuid4: str
    ) -> None:
        encounter = {
            "uuid": "encounter_uuid",
            "created": datetime.min,
            "created_by": "I won't appear",
            "modified": datetime.utcnow(),
            "modified_by": "I am real",
            "score_system": "news2",
            "spo2_scale": 2,
        }

        publish.publish_score_system_change(encounter=encounter)

        assert mock_publish_msg.call_args[1]["body"] == {
            "actions": [
                {
                    "name": "process_observation_set",
                    "data": {
                        "encounter": encounter,
                        "observation_set": {
                            "created": encounter["modified"],
                            "created_by": encounter["modified_by"],
                            "modified": encounter["modified"],
                            "modified_by": encounter["modified_by"],
                            "record_time": encounter["modified"],
                            "score_system": encounter["score_system"],
                            "spo2_scale": encounter["spo2_scale"],
                            "uuid": mock_uuid4,
                        },
                    },
                }
            ]
        }

    def test_publish_invalid_encounter(self) -> None:
        encounter = {"spo2_scale": 2}

        with pytest.raises(KeyError):
            publish.publish_score_system_change(encounter=encounter)

    def test_merge_encounters(
        self,
        client: FlaskClient,
        encounter_factory: Callable,
        dh_product_uuid: str,
    ) -> None:
        child_patient_record_uuid = "67f9a1d6-80f3-4f3d-92f5-4136cd60d2be"
        child_patient_uuid = "98c38be3-5ee1-4469-9b94-c6b2561c3700"
        parent_patient_uuid = "ec950495-7a14-4bb0-8cf6-aff0ded4535d"
        parent_patient_record_uuid = "dcec8bbd-600a-4744-9581-945d1dfb2f4a"
        message_uuid = "f00f001"

        encounter_1 = encounter_factory(
            admitted_at="2019-01-23T08:31:19.123Z",
            created="2020-12-10T16:43:21.255Z",
            deleted_at=None,
            dh_product_uuid=dh_product_uuid,
            discharged_at=None,
            encounter_type="INPATIENT",
            epr_encounter_id=None,
            location_history=[],
            location_uuid="9f03efbe-5828-49dc-a777-7f6952b9cea8",
            patient_record_uuid=child_patient_record_uuid,
            patient_uuid=child_patient_uuid,
            score_system="news2",
            score_system_history=[],
            spo2_scale=2,
            uuid="889b2e04-0a73-4264-8494-66bb0a373430",
        ).uuid

        encounter_2 = encounter_factory(
            admitted_at="2019-01-23T08:31:19.123Z",
            created="2020-12-10T16:47:10.755Z",
            deleted_at=None,
            dh_product_uuid=dh_product_uuid,
            discharged_at=None,
            encounter_type="INPATIENT",
            epr_encounter_id=None,
            location_history=[],
            location_uuid="9f03efbe-5828-49dc-a777-7f6952b9cea8",
            patient_record_uuid=parent_patient_record_uuid,
            patient_uuid=parent_patient_uuid,
            score_system="news2",
            score_system_history=[],
            spo2_scale=2,
            uuid="6f282082-509c-4b3d-b957-7fbedb80cf2e",
        ).uuid

        db.session.commit()

        data = {
            "child_record_uuid": child_patient_record_uuid,
            "message_uuid": message_uuid,
            "parent_patient_uuid": parent_patient_uuid,
            "parent_record_uuid": parent_patient_record_uuid,
        }

        response = client.post(
            "/dhos/v1/encounter/merge",
            headers={"Authorization": "Bearer TOKEN"},
            json=data,
        )
        json: Optional[Dict] = response.json
        assert json is not None
        assert response.status_code == 200
        assert json == {"total": 1}

        enc = Encounter.query.get(encounter_1)
        assert enc.merge_history == [
            {
                "record_uuid": child_patient_record_uuid,
                "patient_uuid": child_patient_uuid,
                "message_uuid": message_uuid,
            }
        ]
        assert enc.patient_uuid == parent_patient_uuid
        assert enc.patient_record_uuid == parent_patient_record_uuid

    def test_get_encounters(self, client: FlaskClient, mocker: MockFixture) -> None:
        mock_get = mocker.patch(
            "dhos_encounters_api.blueprint_api.controller.get_encounters",
            return_value={"some": "return"},
        )
        response = client.get(
            "/dhos/v2/encounters?modified_since=2020-01-01",
            headers={"Authorization": "Bearer TOKEN"},
        )
        mock_get.assert_called_once()
        assert response.status_code == 200
