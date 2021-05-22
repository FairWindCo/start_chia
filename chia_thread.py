import math
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

from utility.LogInterface import LogInterface
from utility.SeparateSubprocessThread import SeparateCycleProcessCommandThread

matching = re.compile(r'Starting phase ([0-9]*/[0-9]*):')
ex_data = re.compile(r'\s*(.*)\s+([A-Z][a-z]{2,4}\s+[A-Z][a-z]{2,10}\s+\d{1,2}\s+\d{1,2}:\d{1,2}:\d{1,2}\s+\d{2,4}.*)$')
matching_time = re.compile(r'Time for phase ([0-9]+) = ([0-9.]+) seconds. CPU \(([0-9.]+)%\) ([\w\d\s:]*)$')


def convert_param_to_attribute(key, value):
    if key == 'thread_per_plot' and value:
        return f'-r {value}'
    if key == 'temp_dir' and value:
        return f'-t {value}'
    if key == 'work_dir' and value:
        return f'-d {value}'
    if key == 'memory' and value:
        return f'-b {value}'
    if key == 'bucket' and value:
        return f'-u {value}'
    if key == 'k_size' and value:
        return f'-r {value}'
    if key == 'bitfield_disable' and (value == 'True' or value == 'true'):
        return f'-e'
    if key == 'fingerprint' and value:
        return f'-a {value}'
    if key == 'pool_pub_key' and value:
        return f'-p {value}'
    if key == 'farmer_pub_key' and value:
        return f'-f {value}'
    return ''


def get_command_args(config_dict):
    args = [convert_param_to_attribute(key, val) for key, val in config_dict.items()]
    command = config_dict['chia_path']
    return f'{command} plots create {" ".join(args)}'


class ChieThread(SeparateCycleProcessCommandThread, LogInterface):
    def __init__(self, name, start_index, last, config_for_thread):
        pause = float(config_for_thread.get('pause_before_start', 0))
        super().__init__(config_for_thread, pause, 0, name, False,
                                                          start_iteration_number=start_index)
        LogInterface.__init__(self, name)
        self.pause_once = True
        self.file = name
        self.last = last
        self.phase = 'ИНИЦИАЛИЗАЦИЯ'
        self.plot_created = 0
        self.ave_time = 0
        self.end_phase_info = ''
        self.start_phase_info = ''
        self.phase_stat = {}

    def on_end_iteration(self, index):
        with open(self.file, 'wt') as file:
            file.write(f'{index}')

    def on_start_iteration(self, index):
        cmd = get_command_args(self.config)
        self.config['cmd'] = cmd

    def on_start_thread(self):
        self.clear_temp()
        self.write_log(f'START WORK from {self.start_iteration_number} to {self.last}')

    def check_stop_iteration(self, iteration_index: int) -> bool:
        return iteration_index >= self.last

    def on_stop_thread(self):
        self.phase = f'ПРОЦЕСС ЗАВЕРШЕН! {datetime.now()}'
        try:
            os.remove(self.file)
        except FileNotFoundError:
            print(f'SAFE ITERATION FILE: {self.file} not found - may be no iteration\n')
        for name, stat in self.phase_stat.items():
            self.write_log(name)
            for k, v in stat.items():
                if type(v) == int or type(v) == float:
                    self.write_log(f'{k:7s}:{v:10.0f}')
                elif type(v) == str:
                    self.write_log(f'{k:7s}:{v:10s}')
                else:
                    self.write_log(f'{k:7s}:{v[0]:10.0f}s   {v[1]}')
        self.close_log()

    def clear_temp(self):
        self.write_log('CLEAR TEMP')
        temp_dir = self.config.get('temp_dir')
        files = Path(temp_dir).glob('*.tmp')
        for f in files:
            try:
                f.unlink()
            except OSError as e:
                self.write_log(f'ERROR in {f} - {e.strerror} ')

    def set_status(self, text):
        super().set_status(text)
        self.write_log(text, need_flush=True)

    def analise_command_output(self, iteration_index, output_string, err=False):
        self.write_log(output_string, need_flush=True)
        result = matching.search(output_string)
        if result:
            self.phase = result.group(1)
            self.set_status(f'Запущена фаза {self.phase}')
            result = ex_data.search(output_string, result.end())
            if result:
                self.start_phase_info = f'{result.group(1)} [{result.group(2)}]'
        else:
            result = matching_time.search(output_string)
            if result:
                seconds = float(result.group(2))
                minutes = math.ceil(seconds / 60)
                name = f'Фаза {result.group(1)}'
                statistics = self.phase_stat.get(name, {
                    'last': (0.0, timedelta(seconds=0)),
                    'min': (0.0, timedelta(seconds=0)),
                    'max': (0.0, timedelta(seconds=0)),
                    'avg': (0.0, timedelta(seconds=0)),
                    'count': 0.0,
                    'total': (0.0, timedelta(seconds=0)),
                    'time': datetime.now().strftime('%d/%m/%y %H:%M:%S')
                })

                statistics['last'] = (seconds, timedelta(seconds=seconds))
                if seconds > statistics['max'][0]:
                    statistics['max'] = (seconds, timedelta(seconds=seconds))
                if statistics['min'] == 0:
                    statistics['min'] = (seconds, timedelta(seconds=seconds))
                if seconds < statistics['min'][0]:
                    statistics['min'] = (seconds, timedelta(seconds=seconds))
                total = statistics['total'][0]
                statistics['total'] = (total + seconds, timedelta(seconds=total + seconds))
                statistics['count'] = (iteration_index + 1)
                avg = total + seconds / (iteration_index + 1)
                statistics['avg'] = (avg, timedelta(seconds=avg))
                statistics['time'] = datetime.now().strftime('%d/%m/%y %H:%M:%S')

                self.phase_stat[name] = statistics
                self.end_phase_info = f'Фаза {result.group(1)} - \
                завершина за {minutes} мин CPU {result.group(3)}% [{result.group(4)}]'
            else:
                if output_string.find('ERROR'):
                    self.set_status(output_string)
