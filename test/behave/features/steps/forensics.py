from monk_plugins.linux.forensics import get_proc_name, find_task
from monk.utils.helpers import as_string

@when('I get the current process name')
def step_impl(context):
    for target in context.targets:
        context.result[target] = get_proc_name(target)

@when('I search for the {task_name} task')
def step_impl(context, task_name):
    for target in context.targets:
        context.result[target] = find_task(target, task_name)

@then("the result should be '{expect}'")
def step_impl(context, expect):
    for target in context.targets:
        if not context.result[target] == expect:
            raise AssertionError(f"Result not equal: {context.result[target]} != {expect}")

@then('the result should not be {not_expect}')
def step_impl(context, not_expect):
    if not_expect == 'None':
        test = lambda x: x is not None
    elif not_expect == 'empty':
        test = lambda x: x
    else:
        test = lambda x: x != not_expect

    for target in context.targets:
        if not test(context.result[target]):
            raise AssertionError(f"Result '{context.result[target]}' was {not_expect}")

@then('I should not get any errors')
def step_impl(context):
    # Empty, because if we arrive at this step execution, it means there were no errors in
    # the previous steps.
    pass

@then("the result should be a TaskStruct with .comm attribute '{comm}'")
def step_impl(context, comm):
    for target in context.targets:
        TaskStruct = target.symbols.structs.TaskStruct
        result = context.result[target]

        if not type(result) == TaskStruct:
            raise AssertionError("Result is not of type 'TaskStruct'")

        if not as_string(result.comm) == comm:
            raise AssertionError("Result does not have .comm '{comm}' (has '{as_string(result.comm}}'")
