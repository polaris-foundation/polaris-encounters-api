import uuid
from typing import Any, Dict

import kombu_batteries_included
from she_logging import logger


def publish_audit_event(event_type: str, event_data: Dict[str, Any]) -> None:
    audit = {"event_type": event_type, "event_data": event_data}
    logger.debug(f"Publishing audit message of type {event_type}")
    kombu_batteries_included.publish_message(routing_key="dhos.34837004", body=audit)


# DM000005 - Observation set with encounter
# The observation set uses the modified and modified_by fields of the encounter
# To populate its created(_by) and modified(_by) fields,
# as it isn't an observation set from the database
def publish_score_system_change(encounter: Dict) -> None:
    logger.debug(
        "Publishing score system change",
        extra={
            "encounter_uuid": encounter["uuid"],
            "score_system": encounter["score_system"],
            "spo2_scale": encounter["spo2_scale"],
        },
    )
    body = {
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
                        "uuid": str(uuid.uuid4()),
                    },
                },
            }
        ]
    }
    kombu_batteries_included.publish_message(routing_key="dhos.DM000005", body=body)


def publish_encounter_update(encounter: Dict) -> None:
    logger.debug("Publishing encounter update", extra={"encounter_data": encounter})
    kombu_batteries_included.publish_message(
        routing_key="dhos.DM000007", body={"encounter_id": encounter.get("uuid")}
    )
