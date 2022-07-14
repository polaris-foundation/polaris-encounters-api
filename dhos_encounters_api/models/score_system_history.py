from datetime import datetime
from typing import Any, Dict, List

from flask_batteries_included.helpers import generate_uuid
from flask_batteries_included.sqldb import ModelIdentifier, db
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String


class ScoreSystemHistory(ModelIdentifier, db.Model):
    uuid = Column(
        String(length=36),
        unique=True,
        nullable=False,
        primary_key=True,
        default=generate_uuid,
    )
    encounter_uuid = Column(String, ForeignKey("encounter.uuid"), index=True)
    score_system = Column(String, nullable=True)
    previous_score_system = Column(String, nullable=True)
    spo2_scale = Column(Integer, nullable=True)
    previous_spo2_scale = Column(Integer, nullable=True)
    changed_time = Column(
        DateTime(timezone=True),
        unique=False,
        nullable=False,
        default=datetime.utcnow,
    )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.to_dict()}"

    @classmethod
    def new(cls, **kw: Any) -> "ScoreSystemHistory":
        obj = cls(**kw)
        db.session.add(obj)
        return obj

    def to_dict(self) -> Dict:
        return {
            "uuid": self.uuid,
            "created_by": self.created_by_,
            "changed_time": self.changed_time,
            "score_system": self.score_system,
            "previous_score_system": self.previous_score_system,
            "spo2_scale": self.spo2_scale,
            "previous_spo2_scale": self.previous_spo2_scale,
            "changed_by": self.created_by_,
        }

    def update(
        self, *args: List, changed_time: datetime, **kwargs: Dict[str, Any]
    ) -> "ScoreSystemHistory":
        self.changed_time = changed_time
        return self

    @classmethod
    def schema(cls) -> Dict:
        return {"optional": {}, "required": {}, "updatable": {"changed_time": str}}
