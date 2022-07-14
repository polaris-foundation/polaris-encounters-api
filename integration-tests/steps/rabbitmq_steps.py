from behave import given, step, use_fixture
from behave.runner import Context
from clients.rabbitmq_client import (
    RABBITMQ_MESSAGES,
    assert_rabbitmq_message_queues_are_empty,
    create_rabbitmq_connection,
    create_rabbitmq_queues,
    get_rabbitmq_message,
)


@given("RabbitMQ is running")
def rabbitmq_is_running(context: Context) -> None:
    if not hasattr(context, "rabbit_connection"):
        context.rabbit_connection = use_fixture(create_rabbitmq_connection, context)
        use_fixture(create_rabbitmq_queues, context, routing_keys=RABBITMQ_MESSAGES)


@step("{dummy} {message_name} message is published to RabbitMQ")
def message_published_to_rabbitmq(
    context: Context, dummy: str, message_name: str
) -> None:
    message = get_rabbitmq_message(context, RABBITMQ_MESSAGES[message_name])
    context.rabbit_message = message


@step("the RabbitMQ queues are empty")
def step_impl(context: Context) -> None:
    assert_rabbitmq_message_queues_are_empty(context)
