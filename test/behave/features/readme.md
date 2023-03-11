Before running the test suite, start all of the target docker containers. Port map each container to a different port. Then the test steps can specify which targets they support.

"Given a connection to a debuggable x.x.x.x target" should append to the context's list of supported targets. There should also be a "given any target" which appends all available test targets to the list of supported targets. (Maybe that list of supported targets is actually just a list of Monk objects? Maybe it's a map that maps the target string to the Monk object, for debug/error output purposes...)

Maybe we should have a "given connections to these supported targets" with a table listing, and that step implementation will call the given for each combo to populate the list of connections for the test

We need a test fixture that runs cleanup after each test, that shuts down all Monk objects in the list of targets and clears the context. So we can be sure we're always starting with fresh connections, and nothing else is connected to the target.
