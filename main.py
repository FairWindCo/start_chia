import atexit
import configparser
import os
import re
import signal
import subprocess
import time
from datetime import datetime
from pathlib import Path
from threading import Thread

import psutil as psutil
from flask import Flask, request, send_from_directory, abort, Response
from psutil import NoSuchProcess


def find_chia():
    for found_path in Path('/').rglob('chia.exe'):
        if 20_000_000 > found_path.stat().st_size > 4_000_000:
            return found_path
        else:
            print(f'PATH FOUND: {found_path} {found_path.stat().st_size:3d}')


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


def get_command_args(config_dict):
    args = [convert_param_to_attribute(key, val) for key, val in config_dict.items()]
    command = config_dict['chia_path']
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
                      'auto_restart': False,
                      'auto_find_exe': True,
                      'pause_before_start': 0,
                      'recheck_work_dir': False,
                      'start_node': None,
                      # 'set_peer_address': '',
                      'bitfield_disable': 'False'}
    if 'default' in config.sections():
        default_config = read_params_from_section(config, 'default', default_config)
    if 'chia_path' not in default_config or not Path(default_config['chia_path']).exists():
        if default_config.get('auto_find_exe', True):
            path_chia_exe = find_chia()
        else:
            path_chia_exe = False

        if path_chia_exe:
            default_config['chia_path'] = path_chia_exe
            print('WARNING: NO "chia_path" IN CONFIG FILE OR PATH INCORRECT!')
            print(f'USE PATH: {path_chia_exe}')
        else:
            print('ERROR: NO CHIA.EXE FILE FOUND!')
            exit(1)
    config_thread = [read_params_from_section(config, section, default_config) for section in config.sections()
                     if section != 'default']
    return config_thread, default_config


matching = re.compile(r'Starting phase ([0-9]*/[0-9]*)')


class ChieThread(Thread):
    def __init__(self, name, file, cmd, current, last, temp_dir, config_for_thread):
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
        self.config = config_for_thread

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
                print("Error: %s : %s" % (f, e.strerror))
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
        for ind in range(self.current, self.last):
            try:
                start_time = datetime.now()
                if not self.need_stop:
                    self.process = subprocess.Popen(['powershell', self.cmd], stderr=subprocess.PIPE,
                                                    stdout=subprocess.PIPE, shell=True, encoding='cp866',
                                                    universal_newlines=True)
                while not self.need_stop and self.process.poll() is None:
                    text = self.process.stdout.readline()
                    result = matching.search(text)
                    if result:
                        self.phase = result.group(1)
                    self.write_log(text, False, need_flush=True)
                if self.need_stop and self.process.poll() is None:
                    self.kill()

                if self.process and self.process.returncode == 0:
                    elapsed_time = datetime.now() - start_time
                    self.current = ind + 1
                    self.write_last()
                    self.write_log(f'plot {self.current:3d} created at {elapsed_time}\n')
                elif not self.need_stop:
                    error_text = self.process.stderr.read()
                    self.write_log(f'ERROR {self.current:3d}: {error_text}\n')

                if self.need_stop:
                    self.write_log(f'ABORT plot {self.current} \n\n', need_flush=True, need_stdout=True)
                    self.process = None
                    return
                self.process = None
            except Exception as e:
                self.process = None
                self.write_log(f'ERROR {e} plot {self.current} created \n\n')

            if self.config.get('recheck_work_dir', False):
                chia_cmd_path = self.config.get('chia_path')
                if chia_cmd_path:
                    work_dir = self.config['work_dir']
                    subprocess.Popen(['powershell', f'{chia_cmd_path} --final_dir "{work_dir}"'])

        self.process = None
        self.need_stop = True
        self.phase = 'EXECUTED'
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
        path_safe_iteration_count_file = Path(f'{self.name}_{number}')
        if path_safe_iteration_count_file.exists():
            with open(path_safe_iteration_count_file, 'rt') as file:
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
        result = [ChieThread(f'{self.name}-{index}', f'{self.name}_{index}', self.command, number, self.num_plots,
                             self.config['temp_dir'], self.config) for
                  index, number in
                  enumerate(self.process)]
        self.process = [0 for _ in range(self.num_parallel)]
        return result


app = Flask(__name__)


class MainThread(Thread):

    def __init__(self):
        super().__init__()
        self.configs, self.main_config = get_threads_configs()
        self.threads = []
        self.all_thread_stopped = True
        self.web_server_running = True
        self.restart_command = False

    def need_start(self):
        if not self.threads:
            return True
        if self.all_thread_stopped and self.main_config.get('auto_restart', False):
            return True
        if self.all_thread_stopped and self.restart_command:
            self.restart_command = False
            return True
        return False

    def init_thread(self):
        self.threads = [thread for conf in self.configs for thread in ChieThreadConfig(conf).get_threads()]

    def start_workers(self):
        self.all_thread_stopped = False
        for thread in self.threads:
            thread.start()

        for thread in self.threads:
            thread.join()
        self.all_thread_stopped = True

    def run(self):
        try:
            app.run(port=5050, host='0.0.0.0')
        except Exception as _:
            pass
        self.web_server_running = False

    def kill_all(self):
        self.main_config['auto_restart'] = False
        print('!TRY KILL ALL!')
        for thread in self.threads:
            thread.kill()
        self.shutdown_server()

    @staticmethod
    def shutdown_server():
        try:
            func = request.environ.get('werkzeug.server.shutdown')
            if func:
                func()
        except RuntimeError:
            pass
        os.kill(os.getpid(), signal.CTRL_C_EVENT)


GIGABYTE = 1024 * 1024 * 1024
if __name__ == '__main__':
    processor = MainThread()
    atexit.register(processor.kill_all)


    @app.route('/')
    def hello_world():
        load_avg = psutil.getloadavg()
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        context = '\n'.join(
            [f'<li>{index:2d}.ПОТОК {thread.name} ВЫПОЛЯЕТ {thread.current} из {thread.last} <BR>\
                ТЕКУЩАЯ ФАЗА {thread.phase} ВРЕМЯ ПОСЛЕДНЕГО ПЛОТА В ПОТОКЕ {thread.last_time}<BR>\
                <a href="/view_log/{thread.name}">VIEW LOG</a> \
                <a href="/log{thread.name}">СКАЧАТЬ LOG</a> \
                <a href="/stop{index}">ОСТАНОВИТЬ ПОТОК</a> \
                </li>' for index, thread in
             enumerate(processor.threads)])
        return f'<HTML><HEAD></HEAD> \
                 <BODY> \
                 <div>ЗАГРУЗКА CPU {cpu_percent}% \
                 последние 1 мин {load_avg[0]}% 5 мин {load_avg[1]}% 15 мин {load_avg[2]}% \
                 </div> \
                 <div>\
                 Использование памяти доступно {(memory.available / GIGABYTE):6.2f}Gb \
                 из {(memory.total / GIGABYTE):6.2f}Gb\
                 </div>\
                 <a href="/">ОБНОВИТЬ</a> \
                 <a href="restart_workers">RESTART</a> \
                 <UL>{context}</UL><div><a href="/stop_all">SHUTDOWN</a></div></BODY></HTML>'


    @app.route('/log<name>')
    def get_log(name):
        current_path = os.getcwd()
        path_to_log_file = Path(current_path).joinpath(f'{name}.log')
        print(path_to_log_file)
        if path_to_log_file.exists():
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
            return f'<HTML><HEAD></HEAD><BODY><UL>{context}</UL></BODY></HTML>'
        else:
            abort(404)


    def line_by_line(file_path):
        if Path(file_path).exists():
            yield '<a href="/">НАЗАД</a><BR>'
            with open(file_path, 'rt') as file:
                for row in file:
                    yield f'{row}<BR>\n'
            yield '<a href="/">НАЗАД</a>'
        else:
            raise Exception(f'FILE {file_path} not found')


    @app.route('/view_log/<name>')
    def view_log(name):
        current_path = os.getcwd()
        path_to_log_file = Path(current_path).joinpath(f'{name}.log')
        if path_to_log_file.exists():
            # try:
            #     content = open(path, 'rt').read()
            # except Exception as e:
            #     print(f'EXCEPTION {e}')
            #     abort(500)
            return Response(line_by_line(path_to_log_file))
        else:
            abort(404)


    @app.route('/stop_all')
    def stop_all():
        processor.kill_all()
        context = 'КОМАНДА ОСТАНОВКИ ПРОГРАММЫ (завершение в течении 1 минуту)'
        return f'<HTML><HEAD></HEAD><BODY><UL>{context}</UL></BODY></HTML>'


    @app.route('/restart_workers')
    def restart_all():
        processor.restart_command = True
        context = f'TRY RESTART!<BR><a href="/">BACK</a>'
        return f'<HTML><HEAD></HEAD><BODY><UL>{context}</UL></BODY></HTML>'

    node_start = processor.main_config.get('start_node', None)
    if node_start:
        path = processor.main_config['chia_path']
        if path:
            peer_config = processor.main_config.get('set_peer_address', None)
            shel = subprocess.Popen(['powershell', f'{path} configure --set-farmer-peer {node_start} -upnp false'])
            shel.wait(10)
            subprocess.Popen(['powershell', f'{path} start {peer_config}'])

    processor.start()
    while processor.web_server_running:
        if processor.need_start():
            processor.init_thread()
            processor.start_workers()
        else:
            try:
                time.sleep(60)
            except KeyboardInterrupt:
                processor.kill_all()
