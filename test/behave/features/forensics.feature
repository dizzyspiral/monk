Feature: linux forensics
    Scenario: Find a task by name
        Given connections to each of the supported targets
            | arch | os    | kernel | machine     |
            | arm  | linux | 5.10.7 | versatilepb |
        When the run method is invoked
        And I wait for 5 seconds
        And the stop method is invoked
        And I search for the init task
        Then the result should not be None
        And the result should be a TaskStruct with .comm attribute 'init'
