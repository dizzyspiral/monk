Feature: execution control
    Scenario: Tell a stopped target to run
        Given connections to each of the supported targets
            | arch | os    | kernel | machine     |
            | arm  | linux | 5.10.7 | versatilepb |
        And the target is stopped
        When the run method is invoked
        Then the target should be running

    Scenario: Tell a running target to run
        Given connections to each of the supported targets
            | arch | os    | kernel | machine     |
            | arm  | linux | 5.10.7 | versatilepb |
        And the target is running
        When the run method is invoked
        Then the target should be running

    Scenario: Tell a running target to stop
        Given connections to each of the supported targets
            | arch | os    | kernel | machine     |
            | arm  | linux | 5.10.7 | versatilepb |
        And the target is running
        When the stop method is invoked
        Then the target should be stopped

    Scenario: Tell a stopped target to stop
        Given connections to each of the supported targets
            | arch | os    | kernel | machine     |
            | arm  | linux | 5.10.7 | versatilepb |
        And the target is stopped
        When the stop method is invoked
        Then the target should be stopped

    Scenario: Tell a stopped target to step execution
        Given connections to each of the supported targets
            | arch | os    | kernel | machine     |
            | arm  | linux | 5.10.7 | versatilepb |
        And the target is stopped
        When the step method is invoked
        Then execution should step by one instruction

#    Scenario: Tell a running target to step execution
#        Given the target is running
#        When the step method is invoked
#        Then an error should be thrown
