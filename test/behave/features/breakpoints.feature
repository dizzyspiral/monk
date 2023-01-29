Feature: breakpoints
    Scenario: Set execution breakpoint by symbol name
        Given connections to each of the supported targets
            | arch | os    | kernel | machine     |
            | arm  | linux | 5.10.7 | versatilepb |
        When an execution breakpoint is set on __switch_to
        Then the target should stop execution at the address of __switch_to

    Scenario: Set execution breakpoint by address
        Given connections to each of the supported targets
            | arch | os    | kernel | machine     |
            | arm  | linux | 5.10.7 | versatilepb |
        When an execution breakpoint is set at address 0xidk
        Then the target should stop execution at address 0xidk

    Scenario: Uninstall an execution breakpoint
        Given connections to each of the supported targets
            | arch | os    | kernel | machine     |
            | arm  | linux | 5.10.7 | versatilepb |
        When an execution breakpoint is set on __switch_to
        And the breakpoint is uninstalled
        Then the target should not stop execution at __switch_to
