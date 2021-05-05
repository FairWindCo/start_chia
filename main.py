import atexit
import configparser
import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from select import select
from threading import Thread

import psutil as psutil
from flask import Flask, request, send_from_directory, abort
from psutil import NoSuchProcess


def find_chia():
    for path in Path('/').rglob('chia.exe'):
        if 20_000_000 > path.stat().st_size > 4_000_000:
            return path
        else:
            print(f'PATH FOUND: {path} {path.stat().st_size:3d}')


def read_params_from_section(config_, section, default=None):
    if default is None:
        default = {}
    else:
        default = default.copy()
    from_file = {key: config_[section][key] for key in config_[section] if config_[section][key]}
    default.update(from_file)
    default['name'] = section
    return default


def convert_param_to_attribute(key, value):
    if key == 'thread_per_plot' and value:
        return f'-r {value}'
    if key == 'temp_dir' and value:
        return f'-t {value}'
    if key == 'work_dir' and value:
        return f'-d {value}'
    if key == 'memory' and value:
        return f'-b {value}'
    if key == '' and value:
        return f'-r {value}'
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


def get_command_args(congig_dict):
    args = [convert_param_to_attribute(key, val) for key, val in congig_dict.items()]
    command = congig_dict['chia_path']
    return f'{command} plots create {" ".join(args)}'


def get_threads_configs():
    config = configparser.ConfigParser()
    config.read('config.ini')
    default_config = {'chia_path': '~/chia.exe',
                      'thread_per_plot': '2',
                      'parallel_plot': '2', 'temp_dir': '/tmp',
                      'work_dir': '/safe', 'memory': '4608',
                      'bucket': '128', 'k_size': '32',
                      'plots_count': 10,
                      'bitfield_disable': 'False'}
    if 'default' in config.sections():
        default_config = read_params_from_section(config, 'default', default_config)
    if 'chia_path' not in default_config or not Path(default_config['chia_path']).exists():
        path = find_chia()
        if path:
            default_config['chia_path'] = path
            print('WARNING: NO "chia_path" IN CONFIG FILE OR PATH INCORRECT!')
            print(f'USE PATH: {path}')
        else:
            print('ERROR: NO CHIA.EXE FILE FOUND!')
            exit(1)
    config_thread = [read_params_from_section(config, section, default_config) for section in config.sections()
                     if section != 'default']
    return config_thread


matching = re.compile(r'Starting phase ([0-9]*/[0-9]*)')


class ChieThread(Thread):
    def __init__(self, name, file, cmd, current, last, temp_dir):
        super().__init__(name=name)
        self.file = file
        self.cmd = cmd
        self.current = current
        self.last = last
        self.process = None
        self.need_stop = False
        self.temp_dir = temp_dir
        self.log = open(f'{self.name}.log', 'at')
        self.phase = 'init'
        self.last_time = 'unknown'

    def __del__(self):
        if self.log:
            try:
                self.log.close()
            except Exception:
                pass

    def write_last(self):
        with open(self.file, 'wt') as file:
            file.write(f'{self.current}')

    def clear_temp(self):
        self.log.write(
            f'{datetime.now().strftime("%d.%m.%Y %H:%M:%S")} CLEAR TEMP\n')
        files = Path(self.temp_dir).glob('*.tmp')
        for f in files:
            try:
                f.unlink()
            except OSError as e:
                print("Error: %s : %s" % (f, e.strerror))
                current_date = datetime.now()
                self.log.write(
                    f'{current_date.strftime("%d.%m.%Y %H:%M:%S")} ERROR in {f} - {e.strerror} \n\n')

    def run(self) -> None:
        self.clear_temp()
        self.log.write(
            f'{datetime.now().strftime("%d.%m.%Y %H:%M:%S")} START WORK from {self.current} to {self.last}\n')
        for ind in range(self.current, self.last):
            try:
                start_time = datetime.now()
                self.process = subprocess.Popen(['powershell', self.cmd], stderr=subprocess.PIPE,
                                                stdout=subprocess.PIPE, shell=True, encoding='cp866',
                                                universal_newlines=True)
                while not self.need_stop and self.process.poll() is None:
                    text = self.process.stdout.readline()
                    print(text)
                    result = matching.search(text)
                    if result:
                        print(f'THREAD {self.name} IS {result}')
                        self.phase = result.group(1)
                    self.log.write(text)
                    self.log.flush()

                if self.process.returncode == 0:
                    time = datetime.now() - start_time
                    print(f'COMMAND {self.cmd}')
                    # process.wait()
                    self.current = ind + 1
                    self.write_last()
                    current_date = datetime.now()
                    self.log.write(
                        f'{current_date.strftime("%d.%m.%Y %H:%M:%S")} plot {self.current:3d} created at {time}\n')
                elif not self.need_stop:
                    current_date = datetime.now()
                    error_text = self.process.stderr.read()
                    self.log.write(
                        f'{current_date.strftime("%d.%m.%Y %H:%M:%S")} ERROR {self.current:3d}: {error_text}\n')

                if self.need_stop:
                    current_date = datetime.now()
                    self.log.write(
                        f'{current_date.strftime("%d.%m.%Y %H:%M:%S")} ABORT plot {self.current} \n\n')
                    self.process = None
                    return
                self.process = None
                self.log.flush()
            except Exception as e:
                self.process = None
                current_date = datetime.now()
                self.log.write(
                    f'{current_date.strftime("%d.%m.%Y %H:%M:%S")} ERROR {e} plot {self.current} created \n\n')

    def kill(self):
        self.need_stop = True
        if self.process:
            try:
                process = psutil.Process(self.process.pid)
                for proc in process.children(recursive=True):
                    proc.kill()
            except NoSuchProcess:
                pass
            time.sleep(1)
            self.process.kill()
            self.process = None
        time.sleep(2)
        self.clear_temp()
        self.current = f'STOP {self.current}'


class ChieThreadConfig:
    def __init__(self, config):
        self.config = config
        self.command = get_command_args(config)
        self.name = config['name']
        self.num_plots = int(config.get('plots_count', 1))
        self.num_parallel = int(config.get('parallel_plot', 1))

        self.process = [self.get_created_plots(num) for num in range(self.num_parallel)]

    def get_created_plots(self, number):
        path = Path(f'{self.name}_{number}')
        if path.exists():
            with open(path, 'rt') as file:
                created = file.readline()
            if created.isdigit():
                with open(f'{self.name}.log', 'at') as log:
                    log.write(
                        f'RE START NEW WORK FROM {created} plots\n')
                return int(created)

        with open(f'{self.name}-{number}.log', 'wt') as log:
            log.write(
                f'START NEW WORK need create {self.num_plots} plots\n')
        return 0

    def get_threads(self):
        return [ChieThread(f'{self.name}-{index}', f'{self.name}_{index}', self.command, number, self.num_plots,
                           self.config['temp_dir']) for
                index, number in
                enumerate(self.process)]


app = Flask(__name__)


class MainThread(Thread):

    def __init__(self):
        super().__init__()
        self.configs = get_threads_configs()
        self.threads = []
        self.init_thread()

    def init_thread(self):
        self.threads = [thread for conf in self.configs for thread in ChieThreadConfig(conf).get_threads()]

    def start_workers(self):
        for thread in self.threads:
            thread.start()

        for thread in self.threads:
            thread.join()

    def run(self):
        app.run(port=5050, host='0.0.0.0')

    def kill_all(self):
        print('!TRY KILL ALL!')
        for thread in self.threads:
            thread.kill()
        self.shutdown_server()

    def shutdown_server(self):
        try:
            func = request.environ.get('werkzeug.server.shutdown')
            if func:
                func()
        except RuntimeError:
            pass


if __name__ == '__main__':
    processor = MainThread()
    atexit.register(processor.kill_all)


    @app.route('/')
    def hello_world():
        context = '\n'.join(
            [f'<li>{index:2d}.ПОТОК {thread.name} ВЫПОЛЯЕТ {thread.current} из {thread.last} <BR>\
                ТЕКУЩАЯ ФАЗА {thread.phase} ВРЕМЯ ПОСЛЕДНЕГО ПЛОТА В ПОТОКЕ {thread.last_time}<BR>\
                <a href="/view_log/{thread.name}">VIEW LOG</a> \
                <a href="/log{thread.name}">СКАЧАТЬ LOG</a> \
                <a href="/stop{index}">ОСТАНОВИТЬ ПОТОК</a> \
                </li>' for index, thread in
             enumerate(processor.threads)])
        return f'<HTML><HEAD></HEAD><BODY><a href="/">ОБНОВИТЬ</a><UL>{context}</UL><div><a href="/stop_all">SHUTDOWN ALL</a></div></BODY></HTML>'


    @app.route('/log<name>')
    def get_log(name):
        current_path = os.getcwd()
        path = Path(current_path).joinpath(f'{name}.log')
        print(path)
        if path.exists():
            return send_from_directory(directory=current_path, filename=f'{name}.log')
        else:
            abort(404)


    @app.route('/stop<index>')
    def stop(index):
        if not index.isdecimal():
            abort(404)
        index = int(index)
        if 0 <= index < len(processor.threads):
            processor.threads[index].kill()
            context = f'THREAD STOPPED!<BR><a href="/">BACK</a>'
            return f'<HTML><HEAD></HEAD><BODY><UL>{context}</UL><div><a href="/stop_all">SHUTDOWN ALL</a></div></BODY></HTML>'
        else:
            abort(404)


    @app.route('/view_log/<name>')
    def view_log(name):
        current_path = os.getcwd()
        path = Path(current_path).joinpath(f'{name}.log')
        print(path)
        if path.exists():
            try:
                content = open(path, 'rt').read()
            except Exception as e:
                print(f'EXCEPTION {e}')
                abort(500)
            return content
        else:
            abort(404)


    @app.route('/stop_all')
    def stop_all():
        processor.kill_all()
        return 'TRY ALL STOP'


    processor.start()
    processor.start_workers()
