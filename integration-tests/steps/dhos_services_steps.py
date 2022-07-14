from behave import step
from behave.runner import Context
from clients import dhos_locations_client, dhos_services_client
from helpers import patient as patient_helper
from helpers.location import get_location_body


@step("there exists a patient")
def create_patient(context: Context) -> None:
    patient: dict = patient_helper.minimal_patient_data(context)
    context.patients.append(dhos_services_client.post_patient(context, patient))


@step("there exists a location")
def create_location(context: Context) -> None:
    context.location = dhos_locations_client.post_location(context, get_location_body())
