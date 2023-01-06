@given('a {state} target')
def step_impl(context, state):
    # Make sure we have a target first
    context.execute_steps('''
        given a debuggable ARM Linux target
    ''')

    # Hey maybe try out python's new switch statement thing
    if state == 'running':
        pass
    elif state == 'stopped':
        pass

@when('the {command} method is invoked')
def step_impl(context, command):
    if command == 'run':
        pass
    elif command == 'stop':
        pass
    elif command == 'step':
        pass

@then('the target should still be {state}')
def step_impl(context, state):
    if state == 'stopped':
        pass
    elif state == 'running":
        pass

