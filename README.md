# Monk

An introspection framework built on GDB.

## Requirements

```
sudo apt install gdb-multiarch qemu-system-arm
```

Note: you need GDB version 8.2+ (see Gotchas, below).

## Installation

TBD, right now it's a WIP

## Quickstart - try it out!

So maybe you don't have a VM or hardware target you want to try this against right now, but you think it's neat. Here are some instructions for building a target VM that you can run the introspection API against, so you can get an idea of how it works, what its capabilities and limitations are, and how you might use it to build other analysis tools.

1. Get buildroot 

```
git clone https://github.com/buildroot/buildroot.git
```

2. Build an ARM versatile-pb Linux kernel with symbols, and busybox VM image.

```
cd buildroot
TBD
```

3. Create a JSON symbols and types file from the kernel and System.map file

```
./dwarf2json linux --elf buildroot/output/vmlinux --elf-symbols buildroot/output/vmlinux --elf-types buildroot/output/vmlinux --system-map buildroot/output/linux-5.10.7/System.map > arm-versatile-linux-5.10.7.json
```

4. Run the QEMU VM

```
TBD
```

5. Attach GDB

```
gdb-multiarch vmlinux
target remote localhost:1234
```

6. Load monk

```
source monk_gdb.py
```

Now you're ready to start doing some introspection using GDBeast. Here's some ideas to get you started. Alternatively, check out the API documentation.

### Print the name of the current process

```
print-current-process name
```

### Print the names of all processes

```
TBD
```

## Supported platforms

|       | ARM | MIPS | PPC |
| ----- | --- | ---- | --- |
| Linux | *   |      |     |

Legend: 
\* = Work-in-progress
x = Done

### ARM Linux

Currently testing using a versatile-pb QEMU machine with a 5.10.7 Linux kernel and busybox VM image created by [buildroot](https://github.com/buildroot/buildroot).

## Writing callbacks

There are some rules to writing callback functions for execution hooks.
Hooks are only supported for the RSP backend.

1. Callbacks cannot run, step, or stop the target. The target _must_ remain stopped during callbacks because more than one callback can be registered for a hook. If the target starts again during a callback, subsequent callbacks can't act on the target before it runs again. This is no bueno. I've made some effort to save you from yourself; all API calls that execute or stop the target will throw exceptions if you try to run them from a callback. When called from other threads, they will block until callbacks are not executing.
2. Callbacks have to terminate. If your callback needs to run forever for some reason, fork off a thread to do the forever thing. The callback _must_ return so that the event handler can call any other callbacks and, once callbacks are finished, unlock target execution for the main thread/other threads.
3. This shouldn't need to be said, but callbacks should be short if you want you want the target to run at a somewhat normal speed. The target is stopped while callbacks execute. If your callback is lengthy, espcially if it gets called often... target performance will tank.

## Gotchas

Must use GDB version 8.2+, see [this SO post and associated issues](https://stackoverflow.com/questions/48312903/how-to-set-or-modify-breakpoint-commands-in-a-gdb-python-script). Basically GDB-python won't let you add commands to breakpoints in 8.1.x using the Python integration. Unfortunately this version of GDB can be the repo default in some (non-current) OS distros.
