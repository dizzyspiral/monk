from monk.utils.helpers import as_string, as_int_list


def get_proc_name(target, thread=None, task=None):
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
        task = get_task(target, thread)

    return as_string(target.structs.TaskStruct(task).comm)

def get_thread(target, sp=None):
    """
    Gets the thread_info struct for the stack sp. If sp is not specified, gets the 
    current thread from the current stack pointer.

    :param int sp: The thread's stack pointer
    :returns: Address of thread_info for the thread
    :rtype: int
    """
    if not sp:
        sp = target.get_reg('sp')

    return sp & (~0x1fff);

def get_task(target, thread=None):
    """
    Gets thread's task_struct. If thread is not specified, gets the current thread's 
    task_struct.

    :param int thread: The address of the thread_info struct for the thread
    :returns: Address of task_struct for the thread
    :rtype: int
    """
    if not thread:
        thread = get_thread(target)

    return target.structs.ThreadInfo(thread).task

def get_pid(target, task=None):
    """
    Gets tasks's PID. If task is not specified, gets the current task's PID.

    :param int task: The address of the task
    :returns: Task's PID
    :rtype: int
    """
    if not task:
        task = get_task(target)

    return target.structs.TaskStruct(task).pid

def find_task(target, name):
    """
    Find the base address of the named task.

    :param str name: The name of the task to find
    :return: Tasks's base address
    :rtype: int
    """
    TaskStruct = target.structs.TaskStruct

    t = get_task(target)
    t = TaskStruct(t)

    # Check if the first task is the one we want. If this weren't python, we'd do
    # a do-while loop...
    if as_string(t.comm) == name:
        return t

    # Prime the loop by getting the next task, and save the first task's PID so we
    # know if we've walked the whole list
    first_pid = t.pid
    t = TaskStruct(t.tasks.next - t.tasks_offset)

    # Walk the task list looking for the task with the specified name
    while as_string(t.comm) != name and t.pid != first_pid:
        # tasks.next points to the next task's task member, so we need to adjust it by
        # the offset of the tasks member to get a pointer to the base of the next task
        t = TaskStruct(t.tasks.next - t.tasks_offset)

    # Check to see if we actually found the task in question. We could have walked
    # the whole list and not found it.
    if as_string(t.comm) == name:
        return t
    else:
        return None

def walk_tasks(target, task=None):
    """
    Walks tasks and prints their names, starting with the specified task. If no task is 
    given, the currently running task is used to begin the walk.

    :param int task: The address of the task to begin walking from
    """
    TaskStruct = target.structs.TaskStruct

    if not task:
        task = get_task(target)

    t = TaskStruct(task)
    pid = t.pid
    cur_task = TaskStruct(t.tasks.next - t.tasks_offset)
   
    while cur_task.pid != pid:
        print("{}, ".format(as_string(cur_task.comm)))
        cur_task = TaskStruct(cur_task.tasks.next - cur_task.tasks_offset)

def get_task_list(target, task=None):
    """
    Walks tasks and returns a list of TaskStruct objects, starting with the specified task.
    If no task is given, the currently running task is used to begin the walk.

    :param int task: The address of the task to begin walking from
    """
    TaskStruct = target.structs.TaskStruct

    if not task:
        task = get_task(target)

    task_list = []

    task_list.append(TaskStruct(task))
    pid = task_list[-1].pid
    task_list.append(TaskStruct(task_list[-1].tasks.next - task_list[-1].tasks_offset))
   
    while task_list[-1].pid != pid:
        task_list.append(TaskStruct(task_list[-1].tasks.next - task_list[-1].tasks_offset))

    return task_list

def _get_task(target, task=None, taskname=None):
    """
    This is a silly helper function to get the task based on args specified to other
    functions. Maybe combine it with get_task() somehow?
    """
    if task:
        t = task
    elif taskname:
        t = find_task(target, taskname)
    else:
        t = get_task(target)

    return t

def set_task_pid(target, newpid, task=None, taskname=None):
    """
    Sets the PID for task, if specified, otherwise sets the PID for the task with taskname, 
    if specified. If neither options is specified, sets the PID for the current task.
    """
    t = _get_task(target, task, taskname)

    if not t:
        print("Unable to find task for taskname '%s'" % taskname)
        return

    t = target.structs.TaskStruct(t)
    t.pid = newpid

def set_task_name(target, newname, task=None, taskname=None):
    t = _get_task(task, taskname)

    if not t:
        print("Unable to find task for taskname '%s'" % taskname)
        return

    t = target.structs.TaskStruct(t)
    t.comm = as_int_list(newname)

def set_task_tasks(target, taskname, othertask):
    t1 = find_task(target, taskname)
    t2 = find_task(target, othertask)

    t1 = target.structs.TaskStruct(t1)
    t2 = target.structs.TaskStruct(t2)

    t1.tasks = t2.tasks

def get_root_task(target):
    """
    Gets the root (pid 0) task
    """
    TaskStruct = target.structs.TaskStruct
    t = TaskStruct(get_task())

    while t.pid != 0:
        t = TaskStruct(t.parent)

    return t.base

def get_user_regs(target, sp=None):
    """
    Gets the saved user registers from the stack sp. If sp is not specified, gets the 
    current thread's saved registers.

    :param int sp: The stack pointer for the thread
    :returns: The address of the saved registers' pt_regs struct
    :rtype: int
    """
    if not sp:
        sp = target.get_reg('sp')

    return target.structs.PtRegs(sp | 0x1fb0).uregs

def get_pt_regs(target, sp=None):
    if not sp:
        sp = target.get_reg('sp')

    return sp | 0x1fb0

def get_kernel_regs(target, thread=None):
    """
    Gets the saved kernel registers for the thread. If thread is not specified, gets the saved 
    kernel registers for the current thread.
    """
    # Currently, this is just speculation that the kernel registers are saved in cpu_context. 
    # But it's convicing speculation. I'm really not sure what else that would be used for,
    # since the user registers are saved on the stack and the saved kernel registers are 
    # decidedly not in the same place.

    if not thread:
        thread = get_thread(target)

    return target.structs.ThreadInfo(thread).cpu_context
