import docker
from time import sleep

from monk import Monk


@given('connections to each of the supported targets')
def step_impl(context):
    for target in context.table:
        context.execute_steps(f"given a connection to a debuggable {target['arch']} {target['os']} {target['kernel']} {target['machine']} target")

@given('connections to all targets')
def step_imp(context):
    pass

@given('a connection to a debuggable {arch} {os} {kernel} {machine} target')
def step_impl(context, arch, os, kernel, machine):
    target_name = f'monk-{arch}-{os}:{machine}-{kernel}'
    target_port = context.target_port_map[target_name]

    m = Monk(
        host='localhost',
        port=port,
        symbols=f'test/resources/{context.port_symbols_map[port]}',
        backend='rsp'
    )

    context.targets.append(m)
