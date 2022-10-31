from monk.memory.memreader import get_reg
from monk.symbols.structs import TaskStruct, ThreadInfo, ListHead, PtRegs
from monk.utils.helpers import as_string, as_int_list


def get_proc_name(thread=None, task=None):
    """
    Gets task's process name (task_struct comm field). If task is not specified, gets the process 
    name for thread. If both task and thread are not specified, gets the name of the 
    current process.

    :param int thread: The thread to get the process name from (this argument is not 
    used if task is supplied)
    :param int task: The task to get the process name from
    :returns: The process name
    :rtype: string
    """
    if not task:
        task = get_task(thread)

    return as_string(TaskStruct(task).comm)

def get_thread(sp=None):
    """
    Gets the thread_info struct for the stack sp. If sp is not specified, gets the 
    current thread from the current stack pointer.

    :param int sp: The thread's stack pointer
    :returns: Address of thread_info for the thread
    :rtype: int
    """
    if not sp:
        sp = get_reg('sp')

    return sp & (~0x1fff);

def get_task(thread=None):
    """
    Gets thread's task_struct. If thread is not specified, gets the current thread's 
    task_struct.

    :param int thread: The address of the thread_info struct for the thread
    :returns: Address of task_struct for the thread
    :rtype: int
    """
    if not thread:
        thread = get_thread()

    return ThreadInfo(thread).task

def get_pid(task=None):
    """
    Gets tasks's PID. If task is not specified, gets the current task's PID.

    :param int task: The address of the task
    :returns: Task's PID
    :rtype: int
    """
    if not task:
        task = get_task()

    return TaskStruct(task).pid

_task_cache = {}
def find_task(name):
    """
    Find the base address of the named task.

    :param str name: The name of the task to find
    :return: Tasks's base address
    :rtype: int
    """
    global _task_cache

    if name in _task_cache.keys():
        if as_string(TaskStruct(_task_cache[name]).comm) == name:
            return _task_cache[name]

    t = get_task()
    t = TaskStruct(t)
    first_pid = t.pid
    t = TaskStruct(t.tasks.next - t.tasks_offset)

    while as_string(t.comm) != name and t.pid != first_pid:
        t = TaskStruct(t.tasks.next - t.tasks_offset)

    if as_string(t.comm) == name:
        _task_cache[name] = t.base
        return t.base
    else:
        return None

def walk_tasks(task=None):
    """
    Walks tasks and prints their names, starting with the specified task. If no task is 
    given, the currently running task is used to begin the walk.

    :param int task: The address of the task to begin walking from
    """
    if not task:
        task = get_task()

    t = TaskStruct(task)
    pid = t.pid
    cur_task = TaskStruct(t.tasks.next - t.tasks_offset)
   
    while cur_task.pid != pid:
        print("{}, ".format(as_string(cur_task.comm)))
        cur_task = TaskStruct(cur_task.tasks.next - cur_task.tasks_offset)

def get_task_list(task=None):
    """
    Walks tasks and returns a list of TaskStruct objects, starting with the specified task.
    If no task is given, the currently running task is used to begin the walk.

    :param int task: The address of the task to begin walking from
    """
    if not task:
        task = get_task()

    task_list = []

    task_list.append(TaskStruct(task))
    pid = task_list[-1].pid
    task_list.append(TaskStruct(task_list[-1].tasks.next - task_list[-1].tasks_offset))
   
    while task_list[-1].pid != pid:
        task_list.append(TaskStruct(task_list[-1].tasks.next - task_list[-1].tasks_offset))

    return task_list

def _get_task(task=None, taskname=None):
    """
    This is a silly helper function to get the task based on args specified to other
    functions. Maybe combine it with get_task() somehow?
    """
    if task:
        t = task
    elif taskname:
        t = find_task(taskname)
    else:
        t = get_task()

    return t

def set_task_pid(newpid, task=None, taskname=None):
    """
    Sets the PID for task, if specified, otherwise sets the PID for the task with taskname, 
    if specified. If neither options is specified, sets the PID for the current task.
    """
    t = _get_task(task, taskname)

    if not t:
        print("Unable to find task for taskname '%s'" % taskname)
        return

    t = TaskStruct(t)
    t.pid = newpid

def set_task_name(newname, task=None, taskname=None):
    t = _get_task(task, taskname)

    if not t:
        print("Unable to find task for taskname '%s'" % taskname)
        return

    t = TaskStruct(t)
    t.comm = as_int_list(newname)

def set_task_tasks(taskname, othertask):
    t1 = find_task(taskname)
    t2 = find_task(othertask)

    t1 = TaskStruct(t1)
    t2 = TaskStruct(t2)

    t1.tasks = t2.tasks

def get_root_task():
    """
    Gets the root (pid 0) task
    """
    t = TaskStruct(get_task())

    while t.pid != 0:
        t = TaskStruct(t.parent)

    return t.base

def get_user_regs(sp=None):
    """
    Gets the saved user registers from the stack sp. If sp is not specified, gets the 
    current thread's saved registers.

    :param int sp: The stack pointer for the thread
    :returns: The address of the saved registers' pt_regs struct
    :rtype: int
    """
    if not sp:
        sp = get_reg('sp')

    return PtRegs(sp | 0x1fb0).uregs

def get_pt_regs(sp=None):
    if not sp:
        sp = get_reg('sp')

    return sp | 0x1fb0

def get_kernel_regs(thread=None):
    """
    Gets the saved kernel registers for the thread. If thread is not specified, gets the saved 
    kernel registers for the current thread.
    """
    # Currently, this is just speculation that the kernel registers are saved in cpu_context. 
    # But it's convicing speculation. I'm really not sure what else that would be used for,
    # since the user registers are saved on the stack and the saved kernel registers are 
    # decidedly not in the same place.

    if not thread:
        thread = get_thread()

    return ThreadInfo(thread).cpu_context
