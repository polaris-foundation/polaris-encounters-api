from behave import given
from behave.runner import Context


@given("a valid {what} JWT")
def set_current_jwt(context: Context, what: str) -> None:
    context.current_jwt = getattr(context, f"{what}_jwt")
