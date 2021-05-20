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


class ChieThread(SeparateCycleProcessCommandThread, LogInterface):
    def __init__(self, name, file, cmd, start_index, last, temp_dir, config_for_thread):
        self.config = config_for_thread
        pause = float(self.config.get('pause_before_start', 0))
        super().__init__(name=name, cmd=cmd, config=config_for_thread, before_start_pause=pause,
                         start_iteration_number=start_index)
        self.pause_once = True
        self.file = file
        self.last = last
        self.temp_dir = temp_dir
        self.phase = 'ИНИЦИАЛИЗАЦИЯ'
        self.plot_created = 0
        self.ave_time = 0
        self.end_phase_info = ''
        self.start_phase_info = ''
        self.phase_stat = {}

    def on_end_iteration(self, index):
        with open(self.file, 'wt') as file:
            file.write(f'{index}')

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
            print(f'{self.file} not found')
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
        files = Path(self.temp_dir).glob('*.tmp')
        for f in files:
            try:
                f.unlink()
            except OSError as e:
                self.write_log(f'ERROR in {f} - {e.strerror} ')

    def analise_command_output(self, iteration_index, output_string, err=False):
        self.write_log(output_string)
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

