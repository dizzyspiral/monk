"""
ARM register layout. Might be specific to QEMU versatilepb machine. This file shouldn't be required -
there is a way to query the guest for the register layout. But the meaning of the answer to that query
is a GDB internal implementation detail, so to figure out how to re-create that logic in rsp_target,
we have to RE that process. So, for now, this file exists. Hopefully it is temporary.
"""

reg_layout = [
    ('r0', 4),
    ('r1', 4),
    ('r2', 4),
    ('r3', 4),
    ('r4', 4),
    ('r5', 4),
    ('r6', 4),
    ('r7', 4),
    ('r8', 4),
    ('r9', 4),
    ('r10', 4),
    ('r11', 4),
    ('r12', 4),
    ('sp', 4),
    ('lr', 4),
    ('pc', 4),
    ('cpsr', 4)
]
reg_map = {
    'r0': 0,
    'r1': 1,
    'r2': 2,
    'r3': 3,
    'r4': 4,
    'r5': 5,
    'r6': 6,
    'r7': 7,
    'r8': 8,
    'r9': 9,
    'r10': 10,
    'r11': 11,
    'r12': 12,
    'sp': 13,
    'lr': 14,
    'pc': 15,
    'cpsr': 25
}
