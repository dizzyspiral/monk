Feature: breakpoints
    Scenario: Set execution breakpoint by symbol name
        Given a connection to a debuggable arm linux 5.10.7 versatilepb target
        When an execution breakpoint is set on __switch_to
        Then the target should stop execution at the address of __switch_to

    Scenario: Set execution breakpoint by address
        Given a connection to a debuggable arm linux 5.10.7 versatilepb target
        When an execution breakpoint is set at address 0xidk
        Then the target should stop execution at address 0xidk
