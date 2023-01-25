import docker

target_port_map = {
    'monk-ppc64-linux:e5500-5.17.7': 1111,
    'monk-ppc-linux:e500mc-5.17-7': 1112,
    'monk-mips64-linux:mips64-malta5.15.18': 1113,
    'monk-mips32-linux:mips32r2-malta-5.15.18': 1114,
    'monk-aarch64-linux:aarch64_virt-5.15.18': 1115,
    'monk-arm-linux:vexpress-5.15.18': 1116,
    'monk-arm-linux:versatilepb-5.15.18': 1117,
    'monk-arm-linux:versatilepb-5.10.7': 1118,
}

port_symbols_map = {
    1111: 'ppc64-e5500-5.17.7.json',
    1112: 'ppc-3500mc-5.17.7.json',
    1113: 'mips64_malta-5.15.8.json',
    1114: 'mips32r2_malta-linux-5.15.18.json',
    1115: 'aarch64_virt-linux-5.15.18.json',
    1116: 'arm-vexpress-linux-5.15.18.json',
    1117: 'arm-versatilepb-linux-5.15.18.json',
    1118: 'arm-versatilepb-linux-5.10.7.json',
}

@given('connections to each of the supported targets')
def step_impl(context):
    for target in context.table:
        context.execute_steps(f"given a connection to a debuggable {target['arch']} {target['os']} {target['kernel']} {target['machine']} target")

@given('connections to all targets')
def step_imp(context):
    pass

@given('a connection to a debuggable {arch} {os} {kernel} {machine} target')
def step_impl(context, arch, os, kernel, machine):
    port = start_target(arch, os, kernel, machine)
    context.targets.append(connect_to_target(port))

def start_target(arch, os, kernel, machine):
    """
    Starts the docker container for the target with the specified arch and OS. If a suitable container for the
    arch/os combination is already running, nothing is done.

    :param string arch: the architecture of the target
    :param string os: the OS of the target
    :param string kernel: the kernel version of the target (currently ignored)
    :param string machine: the machine of the target (currently ignored)
    :rtype: int
    :return: the port the target's gdbstub is running on
    """
    client = docker.from_env()
    containers = client.containers.list()

    for container in containers:
        image = container.attrs['Config']['Image']
        tag = container.attrs['Config']['Tag']
        if image == f'monk-{arch}-{os}' and tag == '{machine}-{kernel}':
            return 

    target_name = f'monk-{arch}-{os}:{machine}-{kernel}'
    client.containers.run(target_name, detach=True, ports={1234:target_port_map[target_name]}, remove=True)

def connect_to_target(port):
    """
    Connects to a running target.

    :param context: the behave context
    :returns: The monk object connected to the target
    :rtype: Monk
    """
    return Monk(
        host='localhost',
        port=port,
        symbols=f'test/resources/{port_symbols_map[port]}',
        backend='rsp'
    )
