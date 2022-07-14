from collections import Callable
from typing import Dict, Generator

import pytest
from flask_batteries_included.sqldb import db

from dhos_encounters_api.blueprint_api import controller
from dhos_encounters_api.models.encounter import Encounter
from dhos_encounters_api.models.location_history import LocationHistory
from dhos_encounters_api.models.score_system_history import ScoreSystemHistory


@pytest.mark.usefixtures("app_context")
class TestMerge:
    @pytest.fixture(autouse=True)
    def pre_existing_nodes(self) -> Generator[None, None, None]:
        yield
        LocationHistory.query.delete()
        ScoreSystemHistory.query.delete()
        Encounter.query.delete()
        db.session.commit()

    def test_merge(
        self,
        app_context: None,
        encounter_factory: Callable,
        location_uuid: str,
        dh_product_uuid: str,
        record_uuid: str,
        patient_uuid: str,
    ) -> None:
        encounter_1 = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="epr_encounter1",
            encounter_type="INPATIENT",
            admitted_at="2018-01-01T00:00:00.000Z",
            patient_record_uuid=record_uuid,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
        )
        db.session.commit()
        encounter_2 = encounter_factory(
            location_uuid=location_uuid,
            epr_encounter_id="epr_encounter2",
            encounter_type="INPATIENT",
            admitted_at="2018-01-02T00:00:00.000Z",
            patient_record_uuid=record_uuid,
            patient_uuid=patient_uuid,
            dh_product_uuid=dh_product_uuid,
        )
        db.session.commit()

        patient2_uuid = "patient2_uuid!"
        patient_record2_uuid = "patient_record2_uuid!"
        message_uuid = "message_uuid!"

        result: Dict = controller.merge_encounters(
            child_record_uuid=record_uuid,
            parent_record_uuid=patient_record2_uuid,
            parent_patient_uuid=patient2_uuid,
            message_uuid=message_uuid,
        )

        assert result == {"total": 2}
        for uuid in [encounter_1.uuid, encounter_2.uuid]:
            enc = Encounter.query.get(uuid)
            assert enc.merge_history == [
                {
                    "record_uuid": record_uuid,
                    "patient_uuid": patient_uuid,
                    "message_uuid": message_uuid,
                }
            ]
            assert enc.patient_uuid == patient2_uuid
            assert enc.patient_record_uuid == patient_record2_uuid

        patient3_uuid = "patient3_uuid!"
        patient_record3_uuid = "patient_record3_uuid!"
        message2_uuid = "message2_uuid!"

        result2: Dict = controller.merge_encounters(
            child_record_uuid=patient_record2_uuid,
            parent_record_uuid=patient_record3_uuid,
            parent_patient_uuid=patient3_uuid,
            message_uuid=message2_uuid,
        )

        assert result == {"total": 2}

        for uuid in [encounter_1.uuid, encounter_2.uuid]:
            enc = Encounter.query.get(uuid)
            assert enc.merge_history == [
                {
                    "record_uuid": record_uuid,
                    "patient_uuid": patient_uuid,
                    "message_uuid": message_uuid,
                },
                {
                    "record_uuid": patient_record2_uuid,
                    "patient_uuid": patient2_uuid,
                    "message_uuid": message2_uuid,
                },
            ]
            assert enc.patient_uuid == patient3_uuid
            assert enc.patient_record_uuid == patient_record3_uuid

    def test_merge2(
        self,
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

        result = controller.merge_encounters(
            child_record_uuid=child_patient_record_uuid,
            message_uuid=message_uuid,
            parent_patient_uuid=parent_patient_uuid,
            parent_record_uuid=parent_patient_record_uuid,
        )
        assert result == {"total": 1}

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
