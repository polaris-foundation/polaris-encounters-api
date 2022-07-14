from typing import Dict

from faker import Faker

fake = Faker()


def get_location_body() -> Dict:

    ods_code = fake.random_number(digits=5, fix_len=True)
    return {
        "location_type": "225746001",
        "ods_code": str(ods_code),
        "display_name": fake.sentence(),
        "active": True,
        "dh_products": [{"product_name": "GDM", "opened_date": "2001-01-01"}],
    }
