import os
import signal
import subprocess

import psutil
from psutil import NoSuchProcess

from utility.SeparateThread import SeparateCycleThread
from utility.utils import check_bool


def get_command_for_execute_with_shell(cmd, config):
    run_in_shell = check_bool(config.get('start_shell', False))
    shelling_info = check_bool(config.get('p_open_shell', False))
    shell_name = config.get('shell_name', '')
    return [shell_name, cmd] if run_in_shell and shell_name else [el for el in cmd.split(' ') if
                                                                  el] if not shelling_info else cmd


class SeparateCycleProcessCommandThread(SeparateCycleThread):
    process = None

    def __init__(self, cmd, config: dict, before_start_pause: float = 0, inter_iteration_pause: float = 0,
                 name: str = 'SeparateCycleProcessCommandThread',
                 demon=None,
                 start_iteration_number: int = 0, pause_before: bool = True) -> None:
        super().__init__(before_start_pause, inter_iteration_pause, name, demon, start_iteration_number, pause_before)
        self.config = config
        self.cmd = cmd

    def analise_command_output(self, iteration_index, output_string, err=False):
        pass

    def work_procedure(self, iteration) -> bool:
        for line in self.run_command_and_get_output(self.cmd, iteration):
            self.analise_command_output(iteration, line)
        return False

    def run_command_and_get_output(self, cmd, index):
        start_shell = self.config.get('start_shell', False)

        if os.name == 'nt':
            if start_shell:
                code_page = 'cp866'
            else:
                code_page = 'cp1251'
        else:
            code_page = self.config.get('code_page', 'utf8')

        cmd = get_command_for_execute_with_shell(cmd, self.config)
        try:
            self.status = f'RUN COMMAND'
            self.process = subprocess.Popen(cmd,
                                            stderr=subprocess.PIPE,
                                            stdout=subprocess.PIPE,
                                            shell=start_shell, encoding=code_page,
                                            universal_newlines=True)

            while self.worked and self.process.poll() is None:
                text = self.process.stdout.readline()
                if text:
                    yield text
        except Exception as e:
            self.process = None
            self.status = f'ERROR {e} on plot {self.current}'
            self.analise_command_output(index, str(e), True)

    def shutdown(self):
        self.kill_command()
        super().shutdown()

    def kill_command(self):
        if self.process:
            try:
                process = psutil.Process(self.process.pid)
                for proc in process.children(recursive=True):
                    try:
                        proc.kill()
                        os.kill(proc.pid, signal.SIGTERM)
                    except Exception:
                        pass
            except NoSuchProcess:
                pass
            self.event.wait(1)
            if self.process:
                self.process.kill()
            self.process = None
