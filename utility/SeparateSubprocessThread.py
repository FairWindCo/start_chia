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

    def __init__(self, config: dict, before_start_pause: float = 0, inter_iteration_pause: float = 0,
                 name: str = 'SeparateCycleProcessCommandThread',
                 demon=None,
                 start_iteration_number: int = 0, pause_before: bool = True,
                 ) -> None:
        super().__init__(before_start_pause, inter_iteration_pause, name, demon, start_iteration_number, pause_before)
        self.config = config
        self.process = None

    def analise_command_output(self, iteration_index, output_string, err=False):
        pass

    def work_procedure(self, iteration) -> bool:
        for line in self.run_command_and_get_output(self.config['cmd'], iteration):
            self.analise_command_output(iteration, line)
        return False

    def run_command_and_get_output(self, cmd, index, clear_lines=True):
        start_shell = self.config.get('start_shell', False)
        shelling_info = check_bool(self.config.get('p_open_shell', False))
        code_page = self.config.get('code_page', '')
        if not code_page:
            if os.name == 'nt' and shelling_info:
                if start_shell:
                    code_page = 'cp866'
                else:
                    code_page = 'cp1251'
            else:
                code_page = 'utf8'

        cmd = get_command_for_execute_with_shell(cmd, self.config)
        try:
            self.status = f'RUN COMMAND'
            print(f'TRY EXECUTE CMD {cmd} IN THREAD {self.name} with code_page={code_page} shell={start_shell}')
            self.process = subprocess.Popen(cmd,
                                            stderr=subprocess.PIPE,
                                            stdout=subprocess.PIPE,
                                            shell=start_shell, encoding=code_page,
                                            universal_newlines=True)

            while self.worked and self.process and self.process.poll() is None:
                text = self.process.stdout.readline()
                if text:
                    if clear_lines:
                        text = text.strip()
                        if text:
                            yield text
                    else:
                        yield text
        except subprocess.CalledProcessError as e:
            self.set_status(f'ERROR {e} on plot {self.current_iteration}')
            self.process = None
        except ValueError as e:
            self.set_status(f'ERROR {e} on plot {self.current_iteration}')
            self.process = None
        except Exception as e:
            self.set_status(f'ERROR {e} on plot {self.current_iteration}')
            self.analise_command_output(index, str(e), True)

    def shutdown(self):
        self.kill_command()
        super().shutdown()

    def kill_command(self):
        self.stop()
        self.wakeup()
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
                try:
                    os.kill(self.process.pid, signal.SIGTERM)
                except Exception:
                    pass
            self.process = None
