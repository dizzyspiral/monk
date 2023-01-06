Feature: execution control
    Scenario: Tell a stopped target to run
        Given a stopped target
        When the run method is invoked
        Then the target will resume execution

    Scenario: Tell a running target to run
        Given a running target
        When the run method is invoked
        Then the target should still be running

    Scenario: Tell a running target to stop
        Given a running target
        When the stop method is invoked
        Then the target should halt execution

    Scenario: Tell a stopped target to stop
        Given a stopped target
        When the stop method is invoked
        Then the target should still be stopped

    Scenario: Tell a stopped target to step execution
        Given a stopped target
        When the step method is invoked
        Then execution should step by one instruction

    Scenario: Tell a running target to step execution
        Given a running target
        When the step method is invoked
        Then an error should be thrown
