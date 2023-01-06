@when('an execution breakpoint is set on {symbol}')
def step_impl(context, symbol):
    pass

@when('an execution breakpoint is set at address {address}')
def step_impl(context, address):
    pass

@then('the target should stop execution at the address of {symbol}')
def step_impl(context, symbol):
    pass

@then('the target should stop execution at address {address}')
def step_impl(context, address):
    pass
