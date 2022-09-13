import random
import string
from typing import Dict, List

from behave.runner import Context
from faker import Faker

fake = Faker()


def random_string(length: int, letters: bool = True, digits: bool = True) -> str:
    choices: str = ""
    if letters:
        choices += string.ascii_letters
    if digits:
        choices += string.digits
    return "".join(random.choice(choices) for _ in range(length))


def nhs_number() -> str:
    """
    An NHS number must be 10 digits, where the last digit is a check digit using the modulo 11 algorithm
    (see https://datadictionary.nhs.uk/attributes/nhs_number.html).
    """
    first_nine: str = random_string(length=9, letters=False, digits=True)
    digits: List[int] = list(map(int, list(first_nine)))
    total = sum((10 - i) * digit for i, digit in enumerate(digits))
    check_digit = 11 - (total % 11)
    if check_digit == 10:
        # Invalid - try again
        return nhs_number()
    if check_digit == 11:
        check_digit = 0
    return first_nine + str(check_digit)


def minimal_patient_data(context: Context) -> Dict:
    return {
        "allowed_to_text": False,
        "allowed_to_email": None,
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "phone_number": "07123456789",
        "dob": "1970-01-01",
        "nhs_number": nhs_number(),
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
