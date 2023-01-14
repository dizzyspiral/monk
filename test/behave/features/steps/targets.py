import docker

@given('a connection to a debuggable {arch} {os} {kernel} target')
def step_impl(context, arch, os):
    start_target(arch, os, kernel)

def start_target(arch, os, kernel):
    """
    Starts the docker container for the target with the specified arch and OS. If a suitable container for the
    arch/os combination is already running, nothing is done.

    :param string arch: the architecture of the target
    :param string os: the OS of the target
    :param string kernel: the kernel version of the target (currently ignored)
    """
    client = docker.from_env()
    containers = client.containers.list()

    for container in containers:
        if container.attrs['Config']['Image'] == f'monk-{arch}-{os}':
            return

    client.containers.run(f'monk-{arch}-{os}', detach=True, ports={1234:1234})

def connect_to_target(context):
    initialized = False

    try:
        if context.monk.backend.connected:
            return context.monk
    except:
        pass

    if not initialized:
        return Monk(
            host='localhost',
            port=1234,
            symbols='test/versatilepb-linux-5.10.7-all.json',
            backend='rsp'
        )
