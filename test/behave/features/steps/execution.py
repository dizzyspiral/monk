@given('the target is {state}')
def step_impl(context, state):
    # Hey maybe try out python's new switch statement thing
    if state == 'running':
        for target in context.targets:
            target.run()
    elif state == 'stopped':
        for target in context.targets:
            target.stop()

@when('the {command} method is invoked')
def step_impl(context, command):
    if command == 'run':
        for target in context.targets:
            target.run()
    elif command == 'stop':
        for target in context.targets:
            target.stop()
    elif command == 'step':
        context.prev_insn = {}

        for target in context.targets:
            context.prev_pc[target] = target.get_reg('pc')
            target.step()

@then('the target should be {state}')
def step_impl(context, state):
    if state == 'stopped':
        for target in context.targets:
            if target.is_running():
                fail('target is running')
    elif state == 'running':
        for target in context.targets:
            if not target.is_running():
                fail('target is stopped')

@then('execution should step by one instruction')
def step_impl(context):
    for target in context.targets:
        pc = target.get_reg('pc')

        if pc == context.prev_pc[target]:
            # Technically possible with a jump self, but also, generally not going to happen.
            fail('PC remained the same')

        # There's no good way to tell if we incremented one instruction forward in control flow
        # without employing a disassembler. I'm not going to that trouble.

@then('an error should be thrown')
def step_impl(context):
    pass
