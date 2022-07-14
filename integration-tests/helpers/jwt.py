import uuid

from environs import Env
from jose import jwt as jose_jwt


def get_system_token() -> str:
    env: Env = Env()
    hs_issuer: str = env.str("HS_ISSUER")
    hs_key: str = env.str("HS_KEY")
    proxy_url: str = env.str("PROXY_URL")

    return jose_jwt.encode(
        {
            "metadata": {"system_id": "dhos-robot", "can_edit_ews": True},
            "iss": hs_issuer,
            "aud": proxy_url + "/",
            "scope": env.str("SYSTEM_JWT_SCOPE"),
            "exp": 9_999_999_999,
        },
        key=hs_key,
        algorithm="HS512",
    )


def get_superclinician_token(clinician_uuid: str = None) -> str:
    if clinician_uuid is None:
        clinician_uuid = str(uuid.uuid4())
    env: Env = Env()
    hs_issuer: str = env.str("HS_ISSUER")
    hs_key: str = env.str("HS_KEY")
    proxy_url: str = env.str("PROXY_URL")
    scope: str = " ".join(
        [
            "read:send_clinician",
            "read:send_clinician_temp",
            "read:send_encounter",
            "read:send_location",
            "read:send_observation",
            "read:send_patient",
            "read:send_pdf",
            "read:send_rule",
            "read:send_trustomer",
            "read:ward_report",
            "write:send_encounter",
            "write:send_observation",
            "write:send_clinician_temp",
            "write:send_patient",
            "write:send_terms_agreement",
        ]
    )
    return jose_jwt.encode(
        {
            "metadata": {"clinician_id": clinician_uuid},
            "iss": hs_issuer,
            "aud": proxy_url + "/",
            "scope": scope,
            "exp": 9_999_999_999,
        },
        key=hs_key,
        algorithm="HS512",
    )
