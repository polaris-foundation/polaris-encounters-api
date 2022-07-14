import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from behave.runner import Context


def encounter_body(context: Context, **body_values: Optional[Dict[str, Any]]) -> Dict:
    if body_values is None:
        body_values = {}
    body: dict = {
        "encounter_type": "INPATIENT",
        "admitted_at": datetime.now(tz=timezone.utc).isoformat(timespec="milliseconds"),
        "dh_product_uuid": "144873d2-8eb4-4b89-8d38-7650e6012504",
        "location_uuid": str(uuid4()),
        "patient_record_uuid": str(uuid4()),
        "patient_uuid": str(uuid4()),
        "score_system": "news2",
    }
    return {**body, **body_values}


# helper to handle phrases like "the encounter" (=last created encounter) or "encounter 1" (=1st created encounter)
def to_object_index(object_selector: str) -> int:
    if not object_selector or re.match(r"the \w+", object_selector):
        return -1
    return int(re.sub(r"\D+", "", object_selector)) - 1
