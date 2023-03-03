from monk_plugins.linux.forensics import get_proc_name, find_task
from monk.utils.helpers import as_string

@when('I search for the {task_name} task')
def step_impl(context, task_name):
    for target in context.targets:
        context.result[target] = find_task(target, task_name)

@then("the result should be '{result}'")
def step_impl(context, result):
    for target in context.targets:
        if not context.result[target] == result:
            raise AssertionError(f"Result not equal: {context.result[target]} != {result}")

@then('the result should not be None')
def step_impl(context):
    for target in context.targets:
        if context.result[target] == None:
            raise AssertionError("Result was None")

@then("the result should be a TaskStruct with .comm attribute '{comm}'")
def step_impl(context, comm):
    for target in context.targets:
        TaskStruct = target.symbols.structs.TaskStruct
        result = context.result[target]

        if not type(result) == TaskStruct:
            raise AssertionError("Result is not of type 'TaskStruct'")

        if not as_string(result.comm) == comm:
            raise AssertionError("Result does not have .comm '{comm}' (has '{as_string(result.comm}}'")
