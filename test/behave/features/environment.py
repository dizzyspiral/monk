import docker
from time import sleep

target_port_map = {
    'monk-ppc64-linux:e5500-5.17.7': 1111,
    'monk-ppc-linux:e500mc-5.17.7': 1112,
    'monk-mips64-linux:mips64-malta-5.15.18': 1113,
    'monk-mips32-linux:mips32r2-malta-5.15.18': 1114,
    'monk-aarch64-linux:aarch64_virt-5.15.18': 1115,
    'monk-arm-linux:vexpress-5.15.18': 1116,
    'monk-arm-linux:versatilepb-5.15.18': 1117,
    'monk-arm-linux:versatilepb-5.10.7': 1118,
}

port_symbols_map = {
    1111: 'ppc64-e5500-5.17.7.json',
    1112: 'ppc-e500mc-5.17.7.json',
    1113: 'mips64_malta-5.15.8.json',
    1114: 'mips32r2_malta-linux-5.15.18.json',
    1115: 'aarch64_virt-linux-5.15.18.json',
    1116: 'arm-vexpress-linux-5.15.18.json',
    1117: 'arm-versatilepb-linux-5.15.18.json',
    1118: 'arm-versatilepb-linux-5.10.7.json',
}

def before_all(context):
    # Provide the container names and ports to the test steps
    context.target_port_map = target_port_map
    context.port_symbols_map = port_symbols_map
    context.containers = []

    client = docker.from_env()
    containers = client.containers.list()

    # Start all containers
    for target_name, target_port in target_port_map.items():
        try:
            container = client.containers.run(target_name,
                                  detach=True,
                                  ports={1234:target_port_map[target_name]},
                                  remove=True)
        except:
            raise Exception(f"Unable to start container {target_name} on port {target_port_map[target_name]}")

        context.containers.append(container)
        sleep(1)  # Wait for container to fully initialize

def after_all(context):
    for container in context.containers:
        container.kill()

def before_scenario(context, scenario):
    context.targets = []  # Holds target connections (Monk objects) for each supported target
    context.callbacks = []  # Holds any callbacks created for all targets
    context.prev_pc = {}  # Holds the value of PC before doing some operation for each target
    context.result = {}

def after_scenario(context, scenario):
    # Clean up context.targets
    for target in context.targets:
        target.shutdown()
