from monk import Callback
from monk_plugins.linux.forensics import get_proc_name, get_user_regs, get_kernel_regs


class OnExecute(Callback):
    def __init__(self, target, symbol, callback=None):
        super().__init__(target, callback)
        self._symbol = symbol
        self.install()

    def install(self):
        self.add_hook(self._symbol, self.run)


class OnProcessScheduled(Callback):
    def __init__(self, target, proc_name=None, callback=None):
        super().__init__(target, callback)
        self._proc_name = proc_name
        self.install()

    def install(self):
        self.add_hook("__switch_to", self._on_switch_to)

    def _on_switch_to(self):
        print("_on_switch_to")
        if not self._proc_name:
            self.run()
        else:
            next_thread = self.target.get_reg('r2')

            if get_proc_name(self.target, next_thread) == self._proc_name:
                self.run()


class OnProcessExecute(Callback):
    def __init__(self, target, proc_name, callback=None):
        super().__init__(target, callback)
        self._proc_name = proc_name
        self.install()

    def _on_switch_to(self):
        next_thread = self.target.get_reg('r2')

        if get_proc_name(self.target, next_thread) == self._proc_name:
            t = self.target.structs.ThreadInfo(next_thread)
            
            # addr_limit is the highest userspace address a process can access; if it's 0,
            # then this is a kernel process. If not, then it's a userspace process.
            if t.addr_limit > 0x0:
                saved_pc = get_user_regs(self.target, sp=t.cpu_context.sp)[UREGS_PC]
                self._cb_proc_exec = self.add_hook(saved_pc, self._on_proc_exec)
            else:
                saved_regs = get_kernel_regs(self.target)

        self._cb_proc_exec = self.add_hook(saved_regs.pc, self._on_proc_exec)

    def _on_proc_exec(self):
        self.remove_hook(self._cb_proc_exec)
        self.run()

    def install(self):
        self._cb_switch_to = self.add_hook("__switch_to", self._on_switch_to)
