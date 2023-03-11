Feature: linux forensics
    Scenario: Print current process name
        Given connections to each of the supported targets
            | arch | os | kernel | machine |
            | arm | linux | 5.10.7 | versatilepb |
            | arm | linux | 5.15.18 | versatilepb |
            | arm | linux | 5.15.18 | vexpress |
#            | ppc | linux | 5.17.7 | e500mc |
#            | aarch64 | linux | 5.15.18 | aarch64_virt |
        When the run method is invoked
        And I wait for 1 seconds
        And the stop method is invoked
        And I wait for 1 seconds
        And I get the current process name
        Then I should not get any errors
        And the result should not be empty

    Scenario: Find a task by name
        Given connections to each of the supported targets
            | arch | os    | kernel | machine     |
            | arm  | linux | 5.10.7 | versatilepb |
            | arm | linux | 5.15.18 | versatilepb |
            | arm | linux | 5.15.18 | vexpress |
#            | ppc | linux | 5.17.7 | e500mc |
#            | aarch64 | linux | 5.15.18 | aarch64_virt |
        When the run method is invoked
        And I wait for 5 seconds
        And the stop method is invoked
        And I wait for 1 seconds
        And I search for the init task
        Then the result should not be None
        And the result should be a TaskStruct with .comm attribute 'init'
