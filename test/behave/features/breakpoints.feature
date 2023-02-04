Feature: breakpoints
    Scenario: Set execution breakpoint by symbol name
        Given connections to each of the supported targets
            | arch | os    | kernel | machine     |
            | arm  | linux | 5.10.7 | versatilepb |
        When an execution breakpoint is set on __switch_to
        And I wait for 5 seconds
        Then the target should stop execution at the address of __switch_to

    Scenario: Set execution breakpoint by address
        Given connections to each of the supported targets
            | arch | os    | kernel | machine     |
            | arm  | linux | 5.10.7 | versatilepb |
        When an execution breakpoint is set at the specified address
            | target index  | address    |
            | 0             | 0xc00094a8 |
        And I wait for 5 seconds
        Then the target should stop execution at the specified address

    Scenario: Uninstall an execution breakpoint
        Given connections to each of the supported targets
            | arch | os    | kernel | machine     |
            | arm  | linux | 5.10.7 | versatilepb |
        When an execution breakpoint is set on __switch_to
        And the breakpoint is uninstalled
        And I wait for 5 seconds
        Then the target should not stop execution
