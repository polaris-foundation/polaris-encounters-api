from behave import step, use_step_matcher
from behave.runner import Context

use_step_matcher("re")


@step("(?P<who>.+) tries to (?P<do_what>.+)")
def step_impl(context: Context, who: str, do_what: str) -> None:
    context.exception = None
    try:
        context.execute_steps(f"When {who} {do_what}")
    except Exception as e:
        context.exception = e


@step("the attempt fails")
def assert_exception_thrown(context: Context) -> None:
    assert context.exception is not None
