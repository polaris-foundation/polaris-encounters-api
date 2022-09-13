import contextlib
import json
import os
import signal
import socket
import sys
import time
from typing import (
    Any,
    Callable,
    ContextManager,
    Dict,
    Generator,
    Iterator,
    List,
    NoReturn,
    Optional,
    Tuple,
    Type,
    Union,
)
from urllib.parse import urlparse

import kombu_batteries_included
import pytest
import sqlalchemy
from _pytest.config import Config
from flask import Flask, g
from flask_batteries_included.config import RealSqlDbConfig
from flask_batteries_included.helpers import generate_uuid
from flask_batteries_included.sqldb import (
    database_connectivity_test,
    database_version_test,
    db,
)
from marshmallow import RAISE, Schema
from mock import Mock
from pytest_mock import MockFixture
from sqlalchemy.orm import Session

GDM_CLINICIAN_PERMISSIONS: List[str] = [
    "read:gdm_patient",
    "write:gdm_patient",
    "read:gdm_clinician",
    "write:gdm_clinician",
    "read:gdm_location",
    "read:gdm_message",
    "write:gdm_message",
    "read:gdm_bg_reading_all",
    "write:gdm_alert",
    "read:gdm_medication",
    "read:gdm_pdf",
    "write:gdm_pdf",
    "read:gdm_csv",
    "read:gdm_question",
    "read:gdm_answer_all",
    "write:gdm_answer_all",
    "read:gdm_activation",
    "write:gdm_activation",
    "read:gdm_trustomer",
    "read:gdm_telemetry_all",
    "write:gdm_telemetry",
    "write:gdm_terms_agreement",
]

SEND_CLINICIAN_PERMISSIONS: List[str] = [
    "read:send_clinician",
    "read:send_encounter",
    "read:send_location",
    "read:send_observation",
    "read:send_patient",
    "read:send_rule",
    "read:send_trustomer",
    "write:send_encounter",
    "write:send_observation",
    "write:send_patient",
    "write:send_terms_agreement",
]

SYSTEM_PERMISSIONS: List[str] = [
    "delete:gdm_article",
    "delete:gdm_sms",
    "read:audit_event",
    "read:gdm_activation",
    "read:gdm_answer_all",
    "read:gdm_bg_reading_all",
    "read:gdm_clinician_all",
    "read:gdm_location_all",
    "read:gdm_medication",
    "read:gdm_message_all",
    "read:gdm_patient_all",
    "read:gdm_pdf",
    "read:gdm_question",
    "read:gdm_rule",
    "read:gdm_sms",
    "read:gdm_survey_all",
    "read:gdm_telemetry",
    "read:gdm_telemetry_all",
    "read:gdm_trustomer",
    "read:location_by_ods",
    "read:send_clinician",
    "read:send_device",
    "read:send_encounter",
    "read:send_entry_identifier",
    "read:send_location",
    "read:send_observation",
    "read:send_patient",
    "read:send_rule",
    "read:send_trustomer",
    "write:audit_event",
    "write:gdm_activation",
    "write:gdm_alert",
    "write:gdm_article",
    "write:gdm_clinician_all",
    "write:gdm_csv",
    "write:gdm_location",
    "write:gdm_medication",
    "write:gdm_message_all",
    "write:gdm_patient_all",
    "write:gdm_pdf",
    "write:gdm_question",
    "write:gdm_sms",
    "write:gdm_survey",
    "write:gdm_telemetry",
    "write:hl7_message",
    "write:send_clinician",
    "write:send_device",
    "write:send_encounter",
    "write:send_location",
    "write:send_observation",
    "write:send_patient",
]

#####################################################
# Configuration to use database started by tox-docker
#####################################################


def pytest_configure(config: Config) -> None:
    for env_var, tox_var in [
        ("DATABASE_HOST", "POSTGRES_HOST"),
        ("DATABASE_PORT", "POSTGRES_5432_TCP_PORT"),
    ]:
        if tox_var in os.environ:
            os.environ[env_var] = os.environ[tox_var]

    import logging

    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if os.environ.get("SQLALCHEMY_ECHO") else logging.WARNING
    )


def pytest_report_header(config: Config) -> str:
    db_config = (
        f"{os.environ['DATABASE_HOST']}:{os.environ['DATABASE_PORT']}"
        if os.environ.get("DATABASE_PORT")
        else "Sqlite"
    )
    return f"SQL database: {db_config}"


def _wait_for_it(service: str, timeout: int = 30) -> None:
    url = urlparse(service, scheme="http")

    host = url.hostname
    port = url.port or (443 if url.scheme == "https" else 80)

    friendly_name = f"{host}:{port}"

    def _handle_timeout(signum: Any, frame: Any) -> NoReturn:
        print(f"timeout occurred after waiting {timeout} seconds for {friendly_name}")
        sys.exit(1)

    if timeout > 0:
        signal.signal(signal.SIGALRM, _handle_timeout)
        signal.alarm(timeout)
        print(f"waiting {timeout} seconds for {friendly_name}")
    else:
        print(f"waiting for {friendly_name} without a timeout")

    t1 = time.time()

    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s = sock.connect_ex((host, port))
            if s == 0:
                seconds = round(time.time() - t1)
                print(f"{friendly_name} is available after {seconds} seconds")
                break
        except socket.gaierror:
            pass
        finally:
            time.sleep(1)

    signal.alarm(0)


#########################################################
# End Configuration to use database started by tox-docker
#########################################################


@pytest.fixture(scope="session")
def session_app() -> Flask:
    import dhos_encounters_api.app

    port = os.environ.get("DATABASE_PORT")
    use_pgsql = bool(port)
    app = dhos_encounters_api.app.create_app(
        testing=True, use_pgsql=use_pgsql, use_sqlite=not use_pgsql
    )
    if os.environ.get("DATABASE_PORT"):
        # Override fbi use of sqlite to run tests with Postgres
        app.config.from_object(RealSqlDbConfig())

        with app.app_context():
            db.drop_all()
            db.create_all()

    return app


@pytest.fixture
def app(mocker: MockFixture, session_app: Flask) -> Flask:
    from flask_batteries_included.helpers.security import _ProtectedRoute

    def mock_claims(self: Any, verify: bool = True) -> Tuple:
        return g.jwt_claims, g.jwt_scopes

    mocker.patch.object(_ProtectedRoute, "_retrieve_jwt_claims", mock_claims)
    session_app.config["IGNORE_JWT_VALIDATION"] = False
    return session_app


@pytest.fixture
def app_context(app: Flask) -> Generator[None, None, None]:
    with app.app_context():
        yield


@pytest.fixture
def jwt_user_type() -> str:
    "parametrize to 'clinician', 'patient', or None as appropriate"
    return "clinician"


@pytest.fixture
def jwt_scopes() -> Optional[Dict]:
    "parametrize to scopes required by a test"
    return None


@pytest.fixture
def jwt_extra_claims() -> Dict:
    return {"can_edit_ews": True}


@pytest.fixture
def clinician() -> str:
    return generate_uuid()


@pytest.fixture
def jwt_clinician(
    app_context: Flask, jwt_scopes: Dict, clinician: str, jwt_extra_claims: Dict
) -> str:
    """Use this fixture to make requests as a SEND clinician"""
    claims = {"clinician_id": clinician}
    claims.update(jwt_extra_claims)
    g.jwt_claims = claims
    if jwt_scopes is None:
        g.jwt_scopes = SEND_CLINICIAN_PERMISSIONS
    else:
        if isinstance(jwt_scopes, str):
            jwt_scopes = jwt_scopes.split(",")
        g.jwt_scopes = jwt_scopes
    return clinician


@pytest.fixture
def jwt_clinician_cannot_change_spo2(
    app_context: Flask, jwt_scopes: Dict, clinician: str
) -> str:
    """Use this fixture to make requests as a SEND clinician"""
    g.jwt_claims = {"clinician_id": clinician}
    if jwt_scopes is None:
        g.jwt_scopes = SEND_CLINICIAN_PERMISSIONS
    else:
        if isinstance(jwt_scopes, str):
            jwt_scopes = jwt_scopes.split(",")
        g.jwt_scopes = jwt_scopes
    return clinician


@pytest.fixture
def jwt_user_uuid(
    app_context: Flask,
    jwt_send_clinician_uuid: str,
    patient_uuid: str,
    jwt_user_type: str,
    jwt_scopes: Dict,
) -> str:
    """Use this fixture for parametrized tests setting the jwt_user_type fixture to select different
    account types for requests."""

    if jwt_user_type == "clinician":
        # Default user type so nothing to change.
        return jwt_send_clinician_uuid

    elif jwt_user_type == "patient":
        g.jwt_claims = {"patient_id": patient_uuid}
        if jwt_scopes is None:
            g.jwt_scopes = ""
        else:
            if isinstance(jwt_scopes, str):
                jwt_scopes = jwt_scopes.split(",")
            g.jwt_scopes = jwt_scopes
        return patient_uuid

    else:
        g.jwt_claims = {}
        if isinstance(jwt_scopes, str):
            jwt_scopes = jwt_scopes.split(",")
        g.jwt_scopes = jwt_scopes

        return "dummy"


@pytest.fixture
def product_send_uuid() -> str:
    return f"SEND:{generate_uuid()}"[:36]


@pytest.fixture
def location_uuid() -> Generator[str, None, None]:
    yield f"location:{generate_uuid()}"[:36]


@pytest.fixture
def patient_uuid() -> str:
    return f"patient:{generate_uuid()}"[:36]


@pytest.fixture
def record_uuid() -> str:
    return f"record:{generate_uuid()}"[:36]


@pytest.fixture
def dh_product_uuid() -> str:
    return f"dh_product:{generate_uuid()}"[:36]


@pytest.fixture
def mock_publish_msg(mocker: MockFixture) -> Mock:
    return mocker.patch.object(kombu_batteries_included, "publish_message")


@pytest.fixture
def mock_uuid4(mocker: MockFixture, request: Any) -> Any:
    mocker.patch("uuid.uuid4", return_value=request.param)
    return request.param


@pytest.fixture(autouse=True)
def mock_bearer_validation(mocker: MockFixture) -> Mock:
    return mocker.patch(
        "jose.jwt.get_unverified_claims",
        return_value={
            "sub": "1234567890",
            "name": "John Doe",
            "iat": 1_516_239_022,
            "iss": "http://localhost/",
        },
    )


@pytest.fixture
def encounter_factory() -> Callable:
    from dhos_encounters_api.models.encounter import Encounter

    def factory(*args: Any, **kw: Any) -> Encounter:
        e = Encounter.new(*args, **kw)
        db.session.add(e)
        db.session.commit()
        return e

    return factory


@pytest.fixture
def assert_valid_schema(
    app: Flask,
) -> Callable[[Type[Schema], Union[Dict, List], bool], None]:
    def verify_schema(
        schema: Type[Schema], value: Union[Dict, List], many: bool = False
    ) -> None:
        # Roundtrip through JSON to convert datetime values to strings.
        serialised = json.loads(json.dumps(value, cls=app.json_encoder))
        schema().load(serialised, many=many, unknown=RAISE)

    return verify_schema


class DBStatementCounter(object):
    def __init__(self) -> None:
        self.clauses: List[sqlalchemy.sql.ClauseElement] = []

    @property
    def count(self) -> int:
        return len(self.clauses)

    def callback(
        self,
        conn: sqlalchemy.engine.Connection,
        clauseelement: sqlalchemy.sql.ClauseElement,
        multiparams: List[Dict],
        params: Dict,
    ) -> None:
        if isinstance(clauseelement, sqlalchemy.sql.elements.SavepointClause):
            return

        self.clauses.append(clauseelement)


@contextlib.contextmanager
def db_statement_counter(session: Session) -> Iterator[DBStatementCounter]:
    counter = DBStatementCounter()
    cb = counter.callback
    sqlalchemy.event.listen(db.engine, "before_execute", cb)
    try:
        yield counter
    finally:
        sqlalchemy.event.remove(db.engine, "before_execute", cb)


@pytest.fixture
def statement_counter() -> Callable[[Session], ContextManager[DBStatementCounter]]:
    return db_statement_counter
