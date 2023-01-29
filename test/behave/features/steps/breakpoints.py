from monk_plugins.linux.callbacks import OnExecute

@when('an execution breakpoint is set on {symbol}')
def step_impl(context, symbol):
    set_exec_breakpoint(context, symbol)

@when('an execution breakpoint is set at address {address}')
def step_impl(context, address):
    set_exec_breakpoint(context, address)

def set_exec_breakpoint(context, symbol):
    for target in context.targets:
        target.stop()
        context.callbacks.append(OnExecute(target, symbol))
        target.run()

@when('the breakpoint is uninstalled')
def step_impl(context):
    for i in range(context.targets):
        target = context.targets[i]
        callback = context.callbacks[i]

        target.stop()
        callback.uninstall()
        target.run()

@then('the target should not stop execution at {symbol}')
def step_impl(context, symbol):
    for target in context.targets:
        target.stop()
        pc = target.get_reg('pc')

        if pc == target.symbols.lookup(symbol):
            fail(f'target stopped execution at {symbol}')

@then('the target should stop execution at the address of {symbol}')
def step_impl(context, symbol):
    for target in context.targets:
        pc = target.get_reg('pc')

        if pc != target.symbols.lookup(symbol):
            fail(f"target did not stop execution at {symbol}")

@then('the target should stop execution at address {address}')
def step_impl(context, address):
    for target in context.targets:
        pc = target.get_reg('pc')

        if pc != address:
            fail(f"target did not stop execution at {hex(address)}")
