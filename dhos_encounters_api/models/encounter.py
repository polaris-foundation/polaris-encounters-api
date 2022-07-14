from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Union

from flask_batteries_included.helpers import generate_uuid
from flask_batteries_included.helpers.error_handler import UnprocessibleEntityException
from flask_batteries_included.sqldb import ModelIdentifier, db
from she_logging import logger
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import RelationshipProperty, relationship

from dhos_encounters_api.models.location_history import LocationHistory
from dhos_encounters_api.models.score_system_history import ScoreSystemHistory


class Encounter(ModelIdentifier, db.Model):
    uuid = Column(
        type_=String(length=36),
        default=generate_uuid,
        nullable=False,
        primary_key=True,
        unique=True,
    )
    epr_encounter_id = Column(String, nullable=True)
    encounter_type = Column(String, nullable=True)
    admitted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=datetime.utcnow,
    )
    discharged_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)
    spo2_scale = Column(Integer, nullable=True, default=1)
    score_system_history: RelationshipProperty = relationship(
        ScoreSystemHistory,
        primaryjoin="Encounter.uuid == ScoreSystemHistory.encounter_uuid",
        cascade="all,delete",
    )
    location_uuid = Column(String(length=36), nullable=False, index=True)

    location_history: RelationshipProperty = relationship(
        "LocationHistory",
        order_by="LocationHistory.arrived_at",
        backref="encounter",
        cascade="all,delete",
    )

    dh_product_uuid = Column(
        String(length=36),
        nullable=False,
    )
    patient_record_uuid = Column(
        String(length=36),
        nullable=False,
    )
    patient_uuid = Column(String(length=36), nullable=False, index=True)
    parent_uuid = Column(
        String(), ForeignKey("encounter.uuid"), index=True, nullable=True
    )
    score_system = Column(String(), nullable=True)
    merge_history = Column(JSON, default=[])

    __table_args__ = (
        Index(
            "epr_encounter_id_deleted_at",
            epr_encounter_id,
            func.coalesce(deleted_at, datetime(1970, 1, 1).isoformat()),
            unique=True,
        ),
    )

    @property
    def is_local(self) -> bool:
        return self.epr_encounter_id is None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.to_dict(compact=True)}"

    @classmethod
    def new(
        cls,
        dh_product_uuid: str,
        location_uuid: str,
        patient_uuid: str,
        patient_record_uuid: str,
        location_history: Sequence[Dict] = (),
        child_of_encounter_uuid: Optional[str] = None,
        epr_encounter_id: Optional[str] = None,
        *args: Any,
        **kwargs: Any,
    ) -> "Encounter":
        if epr_encounter_id == "":
            epr_encounter_id = None  # Avoid triggering an integrity error for multiple local encounters

        obj = cls(
            dh_product_uuid=dh_product_uuid,
            location_uuid=location_uuid,
            patient_record_uuid=patient_record_uuid,
            patient_uuid=patient_uuid,
            parent_uuid=child_of_encounter_uuid,
            epr_encounter_id=epr_encounter_id,
            location_history=[LocationHistory(**lh) for lh in location_history],
            *args,
            **kwargs,
        )
        db.session.add(obj)
        return obj

    def update(self, *args: Any, **kwargs: Any) -> "Encounter":
        if "location_uuid" in kwargs:
            previous_location_uuid: str = self.location_uuid
            new_location_uuid: str = kwargs.pop("location_uuid")
            if new_location_uuid != previous_location_uuid:
                logger.debug(
                    "Location history being created for location with UUID %s",
                    previous_location_uuid,
                )
                history = LocationHistory.new(
                    encounter_uuid=self.uuid, location_uuid=previous_location_uuid
                )
                db.session.add(history)
                self.location_uuid = new_location_uuid

        if any(key in kwargs for key in ("spo2_scale", "score_system")):
            previous_score_system: Optional[str] = self.score_system
            new_score_system: Optional[str] = kwargs.pop("score_system", None)
            previous_spo2_scale: Optional[int] = self.spo2_scale
            new_spo2_scale: Optional[int] = kwargs.pop("spo2_scale", None)

            if (
                new_spo2_scale is not None and new_spo2_scale != previous_spo2_scale
            ) or (
                new_score_system is not None
                and new_score_system != previous_score_system
            ):
                logger.debug(
                    "Score system history being created: %s %s",
                    self.score_system,
                    self.spo2_scale,
                )
                score_system_history = ScoreSystemHistory.new(
                    score_system=new_score_system,
                    previous_score_system=previous_score_system,
                    spo2_scale=new_spo2_scale,
                    previous_spo2_scale=previous_spo2_scale,
                    changed_time=datetime.now(tz=timezone.utc),
                )
                self.score_system_history.append(score_system_history)
                if new_spo2_scale:
                    self.spo2_scale = new_spo2_scale
                if new_score_system:
                    self.score_system = new_score_system

        if "dh_product_uuid" in kwargs:
            self.dh_product_uuid = kwargs.pop("dh_product_uuid")

        if "patient_record_uuid" in kwargs:
            self.patient_record_uuid = kwargs.pop("patient_record_uuid")

        child_of_encounter_uuid = kwargs.pop("child_of_encounter_uuid", None)
        if child_of_encounter_uuid:
            child_of = Encounter.query.get(child_of_encounter_uuid)
            if child_of is None:
                raise UnprocessibleEntityException

            self.parent_uuid = child_of_encounter_uuid

        for key in kwargs:
            setattr(self, key, kwargs[key])

        db.session.add(self)
        return self

    def remove(self, *args: Any, **kwargs: Any) -> "Encounter":
        child_of_encounter_uuid = kwargs.pop("child_of_encounter_uuid", None)
        if child_of_encounter_uuid and self.parent_uuid == child_of_encounter_uuid:
            self.parent_uuid = None  # type: ignore
            db.session.add(self)

        return self

    def to_dict(
        self,
        compact: bool = False,
        expanded: bool = False,
    ) -> Dict[str, Any]:

        obj: Dict[str, Union[str, int, datetime, None, List]] = {
            "epr_encounter_id": self.epr_encounter_id,
            "admitted_at": self.admitted_at,
            "discharged_at": self.discharged_at,
            "deleted_at": self.deleted_at,
            "location_uuid": self.location_uuid,
            "patient_record_uuid": self.patient_record_uuid,
            "patient_uuid": self.patient_uuid,
            "uuid": self.uuid,
        }
        if not compact:
            obj = {
                **obj,
                "encounter_type": self.encounter_type,
                "score_system": self.score_system,
                "spo2_scale": self.spo2_scale,
                "dh_product": [{"uuid": self.dh_product_uuid}],
                "score_system_history": [
                    ss.to_dict() for ss in self.score_system_history
                ],
                "location_history": [lh.to_dict() for lh in self.location_history],
                "created": self.created.replace(tzinfo=timezone.utc),
            }

            if self.parent_uuid:
                obj["child_of_encounter_uuid"] = self.parent_uuid

        if expanded:
            return {**obj, **self.pack_identifier()}

        return obj

    @classmethod
    def schema(cls) -> Dict:
        return {
            "optional": {
                "discharged_at": str,
                "deleted_at": str,
                "epr_encounter_id": str,
                "child_of_encounter_uuid": str,
                "spo2_scale": int,
                "score_system_history": [dict],
            },
            "required": {
                "encounter_type": str,
                "admitted_at": str,
                "location_uuid": str,
                "patient_record_uuid": str,
                "dh_product_uuid": str,
                "score_system": str,
            },
            "updatable": {
                "epr_encounter_id": str,
                "encounter_type": str,
                "admitted_at": str,
                "discharged_at": str,
                "deleted_at": str,
                "location_uuid": str,
                "dh_product_uuid": str,
                "score_system": str,
                "score_system_history": [dict],
                "patient_record_uuid": str,
                "child_of_encounter_uuid": str,
                "spo2_scale": int,
            },
        }
