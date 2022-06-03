import gdb

from forensics.linux import get_thread, get_task, get_kernel_regs, get_proc_name, get_pid, \
    walk_tasks, find_task, set_task_pid, set_task_name, set_task_tasks

class PrintCurrentProcess(gdb.Command):
    def __init__(self):
        super(PrintCurrentProcess, self).__init__("print-current-process", gdb.COMMAND_USER, gdb.COMPLETE_NONE)

    def invoke(self, arg, from_tty):
        if arg == "name":
            print(get_proc_name())
        elif arg == "thread":
            print("0x%x" % get_thread())
        elif arg == "task":
            print("0x%x" % get_task())
        elif arg == "saved-cpu-context":
            print("0x%x" % get_kernel_regs())
        elif arg == 'pid':
            print("{}".format(get_pid()))
#        elif arg == 'children':
#            print("{}".format(get_child_task_names()))
        else:
            print("print-current-process [name|thread|task|saved-cpu-context|pid]")


class ChangeCurrentProcess(gdb.Command):
    def __init__(self):
        super(ChangeCurrentProcess, self).__init__("change-current-process", gdb.COMMAND_USER, gdb.COMPLETE_NONE)

    def invoke(self, arg, from_tty):
        args = arg.split()

        if len(args) < 2:
            print("not enough args")
            print("change-current-process [name|pid] [new value]")
        else:
            if args[0] == "name":
                set_task_name(args[1])
            elif args[0] == "pid":
                set_task_pid(int(args[1]))
            else:
                print("wrong command format")
                print("change-current-process [name|pid] [new value]")


class PrintAllProcesses(gdb.Command):
    def __init__(self):
        super(PrintAllProcesses, self).__init__("print-all-processes", gdb.COMMAND_USER, gdb.COMPLETE_NONE)

    def invoke(self, arg, from_tty):
        walk_tasks()


class FindTask(gdb.Command):
    def __init__(self):
        super(FindTask, self).__init__("find-task", gdb.COMMAND_USER, gdb.COMPLETE_NONE)

    def invoke(self, arg, from_tty):
        task = find_task(arg)
        if task:
            print("0x%x" % task)
        else:
            print("Unable to find task '{}'".format(arg))

class ChangePid(gdb.Command):
    def __init__(self):
        super(ChangePid, self).__init__("change-pid", gdb.COMMAND_USER, gdb.COMPLETE_NONE)

    def invoke(self, arg, from_tty):
        args = arg.split()
        if len(args) < 2:
            print("change-pid taskname newpid")
        else:
            set_task_pid(args[0], int(args[1]))

class ChangeName(gdb.Command):
    def __init__(self):
        super(ChangeName, self).__init__("change-name", gdb.COMMAND_USER, gdb.COMPLETE_NONE)

    def invoke(self, arg, from_tty):
        args = arg.split()
        if len(args) < 2:
            print("change-name taskname newname")
        else:
            set_task_name(args[0], args[1])

class ChangeTasks(gdb.Command):
    def __init__(self):
        super(ChangeTasks, self).__init__("change-tasks", gdb.COMMAND_USER, gdb.COMPLETE_NONE)

    def invoke(self, arg, from_tty):
        args = arg.split()

        if len(args) < 2:
            print("change-tasks task1 task2")
        else:
            set_task_tasks(args[0], args[1])

class RemoveProcess(gdb.Command):
    def __init__(self):
        super(RemoveProcess, self).__init("remove-process", gdb.COMMAND_USER, gdb.COMPLETE_NONE)

    def invoke(self, arg, from_tty):
        if len(args) < 1:
            print("remove-process process_name")
        else:
            to_remove = arg[0]
            print("Not implemented yet")


class PrintProcessInfo(gdb.Command):
    def __init__(self):
        super(PrintProcessInfo, self).__init__("print-process-info", gdb.COMMAND_USER, gdb.COMPLETE_NONE)

    def invoke(self, arg, from_tty):
        args = arg.split()
        print("args = %s" % args)

        if len(args) < 2:
            print("print-process-info thread_info_addr [task|name]")
        else:
            try:
                thread = int(arg[0])
                choice = arg[1]

                print ("choice = %s")

                if choice == "name":
                    print(get_proc_name(thread=thread))
                elif choice == "task":
                    print(get_task(thread=thread))
            except:
                print("Invalid args '%s'" % arg)


class TraceProcessExecution(gdb.Command):
    def __init__(self):
        super(TraceProcessExecution, self).__init__("trace-process-execution", gdb.COMMAND_USER, gdb.COMPLETE_NONE)

    def invoke(self, arg, from_tty):
        print("Beginning trace...")
#        proc_name = linuxstate.get_proc_name()
#        cur_proc_name = proc_name

        pc_list = []

#        while cur_proc_name == proc_name:

        # While we're still in userspace
        while get_reg('pc') < 0xc0000000:
            pc_list.append(get_reg('pc'))
            s = gdb.execute("si", to_string=True)

        print("Finished tracing, generating output...")
        #print(["0x%x" % x for x in pc_list])

#        user_pcs = []
#
#        for address in pc_list:
#            if address < 0xc0000000:
#                user_pcs.append(address)

        with open('trace.txt', 'a') as f:
            f.write("\n".join(["0x%x" % x for x in pc_list]))
#            f.write(["0x%x" % x for x in user_pcs].join("\n"))


class RunUntilProcessExecutes(gdb.Command):
    def __init__(self):
         super(RunUntilProcessExecutes, self).__init__("run-until-process-executes", gdb.COMMAND_USER, gdb.COMPLETE_NONE)
       
    def invoke(self, arg, from_tty):
        print("Single stepping until process '%s' executes" % arg)

        proc_name = get_proc_name()

        while proc_name != arg:
            s = gdb.execute("s", to_string=False)
            proc_name = get_proc_name()


PrintCurrentProcess()
PrintAllProcesses()
TraceProcessExecution()
RunUntilProcessExecutes()
PrintProcessInfo()
FindTask()
ChangePid()
ChangeName()
ChangeTasks()
ChangeCurrentProcess()
