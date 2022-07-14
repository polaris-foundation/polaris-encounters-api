from typing import Dict

from behave.runner import Context
from faker import Faker
from she_data_generation.patient import nhs_number as generate_nhs_number

fake = Faker()


def minimal_patient_data(context: Context) -> Dict:
    return {
        "allowed_to_text": False,
        "allowed_to_email": None,
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "phone_number": "07123456789",
        "dob": "1970-01-01",
        "nhs_number": generate_nhs_number(),
        "hospital_number": str(fake.random_number(digits=10, fix_len=True)),
        "email_address": "bburrell@example.com",
        "dh_products": [
            {
                "product_name": "SEND",
                "opened_date": "1970-01-01",
                "accessibility_discussed": False,
            }
        ],
        "personal_addresses": [
            {
                "address_line_1": "33 Scarcroft Road",
                "address_line_2": "",
                "address_line_3": "",
                "address_line_4": "",
                "locality": "Oxford",
                "region": "Oxfordshire",
                "postcode": "OX3 5TF",
                "country": "England",
                "lived_from": "1970-01-01",
                "lived_until": "1970-01-01",
            }
        ],
        "ethnicity": "13233008",
        "sex": "23456",
        "highest_education_level": "473461003",
        "accessibility_considerations": [],
        "other_notes": "",
        "record": {"notes": [], "history": {}, "pregnancies": [], "diagnoses": []},
        "locations": [context.location["uuid"]],
    }
