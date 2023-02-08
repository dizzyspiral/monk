from time import sleep

from monk_plugins.linux.callbacks import OnExecute

@when('an execution breakpoint is set on {symbol}')
def step_impl(context, symbol):
    for target in context.targets:
        context.callbacks.append(set_exec_breakpoint(target, symbol))

@when('an execution breakpoint is set at the specified address')
def step_impl(context):
    # The scenario specifies addresses in a table:
    #
    # | target index | address    |
    # | 0            | 0xblahblah |
    # | 1            | 0xtoottoot |
    #
    # The target index must correspond to the index of the target in context.targets -
    # in other words, it must match the order in which the supported targets were 
    # defined by the scenario, starting with index 0

    for addresses in context.table:
        target = context.targets[int(addresses['target index'])]
        address = addresses['address']
        context.callbacks.append(set_exec_breakpoint(target, address))

def set_exec_breakpoint(target, symbol):
    target.stop()
    callback = OnExecute(target, symbol)
    target.run()

    return callback

@when('the breakpoint is uninstalled')
def step_impl(context):
    for target, callback in zip(context.targets, context.callbacks):
        target.stop()

    # Wait for the target to stop. This shouldn't need to be here.
    sleep(1)

    for target, callback in zip(context.targets, context.callbacks):
        callback.uninstall()
        target.run()

@when('I wait for {seconds} seconds')
def step_impl(context, seconds):
    sleep(int(seconds))

@then('the target should not stop execution')
def step_impl(context):
    for target in context.targets:
        if target.is_stopped():
            raise AssertionError('Target stopped')

@then('the target should stop execution at the address of {symbol}')
def step_impl(context, symbol):
    for target in context.targets:
        if not target.is_stopped():
            raise AssertionError('Target did not stop')
        
        pc = target.get_reg('pc')

        if pc != target.symbols.lookup(symbol):
            raise AssertionError(f"target stopped, but did not stop execution at {symbol}")

@then('the target should stop execution at the specified address')
def step_impl(context):
    for target, callback in zip(context.targets, context.callbacks):
        if not target.is_stopped():
            raise AssertionError(f'Target did not stop, {hex(target.symbols.lookup("__switch_to"))}')

        pc = target.get_reg('pc')

        if pc != int(callback.symbol, 16):
            raise AssertionError(f"target stopped, but did not stop execution at {hex(address)}")
