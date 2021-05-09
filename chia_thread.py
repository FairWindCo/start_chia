import math
import os
import re
import signal
import subprocess
import time
from datetime import datetime
from pathlib import Path
from threading import Thread

import psutil
from psutil import NoSuchProcess

from utils import check_bool, get_command_for_execute_with_shell

matching = re.compile(r'Starting phase ([0-9]*\/[0-9]*):')
ex_data = re.compile(r'\s*(.*)\s+([A-Z][a-z]{2,4}\s+[A-Z][a-z]{2,10}\s+\d{1,2}\s+\d{1,2}:\d{1,2}:\d{1,2}\s+\d{2,4}.*)$')
matching_time = re.compile(r'Time for phase ([0-9]+) = ([0-9.]+) seconds. CPU \(([0-9.]+)%\) ([\w\d\s:]*)$')

class ChieThread(Thread):
    def __init__(self, name, file, cmd, current, last, temp_dir, config_for_thread):
        super().__init__(name=name)
        self.file = file
        self.cmd = cmd
        self.current = current
        self.last = last
        self.process = None
        self.need_stop = False
        self.need_stop_iteration = False
        self.temp_dir = temp_dir
        self.log = open(f'{self.name}.log', 'at')
        self.phase = 'init'
        self.last_time = 'unknown'
        self.config = config_for_thread
        self.plot_created = 0
        self.total_time = 0
        self.ave_time = 0
        self.start_shell = check_bool(self.config.get('p_open_shell', False))
        self.end_phase_info = ''
        self.start_phase_info = ''
        self.status = 'INIT'
        self.phase_stat = {}
        if os.name == 'nt':
            if self.start_shell:
                self.code_page = 'cp866'
            else:
                self.code_page = 'cp1251'
        else:
            self.code_page = self.config.get('code_page', 'utf8')

    def __del__(self):
        if self.log:
            try:
                self.log.close()
            except Exception:
                pass

    def write_last(self):
        with open(self.file, 'wt') as file:
            file.write(f'{self.current}')

    def write_log(self, text, need_time_stamp=True, need_stdout=False, need_flush=False):
        date = datetime.now().strftime("%d.%m.%Y %H:%M:%S ") if need_time_stamp else ''
        if need_stdout:
            print(f'{date}{text}')
        if self.log:
            try:
                self.log.write(f'{date}{text}\n')
                if need_flush and self.log:
                    self.log.flush()
            except IOError:
                pass

    def clear_temp(self):
        self.write_log('CLEAR TEMP')
        files = Path(self.temp_dir).glob('*.tmp')
        for f in files:
            try:
                f.unlink()
            except OSError as e:
                self.write_log(f'ERROR in {f} - {e.strerror} ')

    def run(self) -> None:
        self.clear_temp()
        pause = self.config.get('pause_before_start', 0)
        if pause:
            try:
                pause = float(pause)
                if pause > 0:
                    time.sleep(pause)
            except ValueError:
                pass

        self.write_log(f'START WORK from {self.current} to {self.last}')
        if not str(self.current).isdecimal() or not str(self.last).isdecimal():
            self.write_log(f'ERROR IN RANGE PARAMS from {self.current} to {self.last}', need_stdout=True)
            return
        for ind in range(self.current, self.last):
            try:
                start_time = datetime.now()
                if not self.need_stop:
                    cmd = get_command_for_execute_with_shell(self.cmd, self.config)
                    print(cmd)
                    self.process = subprocess.Popen(cmd,
                                                    stderr=subprocess.PIPE,
                                                    stdout=subprocess.PIPE,
                                                    shell=self.start_shell, encoding=self.code_page,
                                                    universal_newlines=True)
                while not self.need_stop and self.process.poll() is None:
                    text = self.process.stdout.readline()
                    result = matching.search(text)
                    if result:
                        self.phase = result.group(1)
                        result = ex_data.search(text, result.end())
                        if result:
                            self.start_phase_info = f'{result.group(1)} [{result.group(2)}]'
                    else:
                        result = matching_time.search(text)
                        if result:
                            seconds = float(result.group(2))
                            minutes = math.ceil(seconds / 60)
                            name = f'Фаза {result.group(1)}'
                            statistics = self.phase_stat.get(name, {
                                'Последнее значение': 0.0,
                                'Минимальное значение значение': 0.0,
                                'Максимальное значение значение': 0.0,
                                'Средне значение': 0.0,
                                'Количество': 0.0,
                                'Сумарное': 0.0,
                            })

                            statistics['Последнее значение'] = seconds
                            if seconds > statistics['Максимальное значение значение']:
                                statistics['Максимальное значение значение'] = seconds
                            if seconds < statistics['Минимальное значение значение']:
                                statistics['Минимальное значение значение'] = seconds
                            statistics['Сумарное'] = statistics['Сумарное'] + seconds
                            statistics['Количество'] = (self.current + 1)
                            statistics['Средне значение'] = statistics['Сумарное'] / (self.current + 1)

                            self.phase_stat[name] = statistics
                            self.end_phase_info = f'Фаза {result.group(1)} - \
                            завершина за {minutes} мин CPU {result.group(3)}% [{result.group(4)}]'

                    self.write_log(text, False, need_flush=True)
                if self.need_stop and self.process.poll() is None:
                    self.kill()

                if self.process and self.process.returncode == 0:
                    elapsed_time = datetime.now() - start_time
                    self.current = ind + 1
                    self.write_last()
                    self.write_log(f'plot {self.current:3d} created at {elapsed_time}\n')
                    self.last_time = elapsed_time
                    self.plot_created += 1
                    self.total_time += elapsed_time.total_seconds()
                    self.ave_time = math.ceil(self.total_time / self.plot_created)
                elif not self.need_stop:
                    error_text = self.process.stderr.read()
                    self.status = f'ERROR {self.current:3d}: {error_text}'
                    self.write_log(f'ERROR {self.current:3d}: {error_text}\n')

                if self.need_stop:
                    self.write_log(f'ABORT plot {self.current} \n\n', need_flush=True, need_stdout=True)
                    self.status = 'ABORT'
                    self.process = None
                    return
                self.process = None
            except Exception as e:
                self.process = None
                self.status = f'ERROR {e} on plot {self.current}'
                self.write_log(f'ERROR {e} plot {self.current} created \n\n')

            if check_bool(self.config.get('recheck_work_dir', False)):
                chia_cmd_path = self.config.get('chia_path')
                if chia_cmd_path:
                    work_dir = self.config['work_dir']
                    subprocess.Popen(get_command_for_execute_with_shell(f'{chia_cmd_path} plots add -d {work_dir}',
                                                                        self.config), shell=self.start_shell)
                    self.status = 'РЕГИСТРАЦИЯ КАТАЛОГА'

            if self.need_stop_iteration:
                self.write_log(f'ABORT ITERATION \n\n', need_flush=True, need_stdout=True)
                self.status = 'ABORT ITERATION'
                break

        self.process = None
        self.need_stop = True
        self.phase = f'ПРОЦЕСС ЗАВЕРШЕН! {datetime.now()}'
        os.remove(self.file)
        for name, stat in self.phase_stat.items():
            self.write_log(name)
            for k, v in stat.items():
                self.write_log(f'{k}:{v:10.0f}')
        self.log.close()
        self.log = None

    def kill(self):
        self.need_stop = True
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
            time.sleep(1)
            if self.process:
                self.process.kill()
            self.process = None
        time.sleep(2)
        self.clear_temp()
        self.status = f'STOP on {self.current}'
