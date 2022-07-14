from datetime import datetime
from typing import Dict, Optional

from flask_batteries_included.helpers import generate_uuid
from flask_batteries_included.sqldb import ModelIdentifier, db
from sqlalchemy import Column, DateTime, ForeignKey, String


class LocationHistory(ModelIdentifier, db.Model):
    uuid = Column(
        String(length=36),
        unique=True,
        nullable=False,
        primary_key=True,
        default=generate_uuid,
    )

    encounter_uuid = Column(
        String(),
        ForeignKey("encounter.uuid"),
        nullable=False,
    )
    location_uuid = Column(String(length=36), nullable=False, index=True)

    arrived_at = Column(
        DateTime(timezone=True),
        unique=False,
        nullable=True,
        default=datetime.utcnow,
        index=True,
    )
    departed_at = Column(
        DateTime(timezone=True),
        unique=False,
        nullable=True,
        default=datetime.utcnow,
    )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.to_dict()}"

    @classmethod
    def new(
        cls,
        encounter_uuid: str,
        location_uuid: str,
        arrived_at: Optional[datetime] = None,
        departed_at: Optional[datetime] = None,
    ) -> "LocationHistory":
        obj = cls(
            encounter_uuid=encounter_uuid,
            location_uuid=location_uuid,
            arrived_at=arrived_at,
            departed_at=departed_at,
        )
        db.session.add(obj)
        return obj

    def to_dict(self) -> Dict:
        return {
            "location_uuid": self.location_uuid,
            "created_at": self.created,
            "arrived_at": self.arrived_at,
            "departed_at": self.departed_at,
        }
