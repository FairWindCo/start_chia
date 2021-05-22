import subprocess
from datetime import datetime
from threading import Thread, Event

import psutil

from InfoThread import InfoThread
from TelegramSenderThread import TelegramSenderThread
from TelegramThread import TelegramThread
from chia_thread_config import get_threads_configs, ChieThreadConfig
from utility.SeparateSubprocessThread import get_command_for_execute_with_shell
from utility.utils import check_bool, GIGABYTE


class MainThread(Thread):

    def __init__(self):
        super().__init__(name='MAIN PROCESSOR')
        self.configs, self.main_config = get_threads_configs()
        self.threads = []
        self.all_thread_stopped = True
        self.web_server_running = True
        self.restart_command = False
        self.event = Event()
        self.info = None
        self.telegram = None

    def need_start(self):
        if not self.threads:
            return True
        if self.all_thread_stopped and check_bool(self.main_config.get('auto_restart', False)):
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
        node_start = self.main_config.get('start_node', None)
        if node_start:
            path = self.main_config['chia_path']
            if path:
                peer_config = self.main_config.get('set_peer_address', None)
                shelling = self.main_config.get('p_open_shell', False)
                shel = subprocess.Popen(
                    get_command_for_execute_with_shell(f'{path} configure --set-farmer-peer {node_start} -upnp false',
                                                       self.main_config), shell=shelling)
                shel.wait(10)
                subprocess.Popen(
                    get_command_for_execute_with_shell(f'{path} start {peer_config}', self.main_config),
                    shell=shelling)
        self.info = InfoThread(self)
        self.telegram = TelegramThread(self)
        self.messager = TelegramSenderThread(self)

        self.info.start()
        self.telegram.start()
        self.messager.start()
        while self.web_server_running:
            if self.need_start() and self.web_server_running:
                print('START POOL')
                self.init_thread()
                self.start_workers()
            else:
                try:
                    if self.web_server_running:
                        self.event.wait(60)
                        self.event.clear()
                except KeyboardInterrupt:
                    self.kill_all()
                    break
        self.info.shutdown()
        self.telegram.shutdown()
        self.messager.shutdown()
        print(f'{self.name} - shutdown')

    def kill_all(self):
        self.main_config['auto_restart'] = False
        print('!TRY KILL ALL!')
        for thread in self.threads:
            thread.shutdown()
        self.web_server_running = False
        # os.kill(self.native_id, signal.CTRL_C_EVENT)
        self.event.set()
        self.info.shutdown()
        self.telegram.shutdown()

    def get_main_info(self):
        disk_info_data = [(p.mountpoint, psutil.disk_usage(p.mountpoint))
                          for p in psutil.disk_partitions() if p.fstype and p.opts.find('fixed') >= 0]
        disk_info = [(di[0], di[1].free / GIGABYTE, di[1].total / GIGABYTE, di[1].percent)
                     for di in disk_info_data]
        memory = psutil.virtual_memory()
        now = datetime.now().strftime('%m/%d/%Y, %H:%M:%S')
        return {
            'load_avg': psutil.getloadavg(),
            'cpu_percent': psutil.cpu_percent(),
            'memory': (memory.available / GIGABYTE, memory.total / GIGABYTE),
            'disk_info': disk_info,
            'threads': self.threads,
            'current_time': now
        }

    def show_config(self):
        return {
            'threads': self.threads,
            'default_config': self.main_config,
        }
        # global_text = get_html_dict(self.main_config, 'Глобальная конфигурация')
        # per_plot = ''.join([get_html_dict(thread.config, thread.name) for thread in self.threads])
        # cmds = ''.join([f'<li>{thread.cmd}<li>' for thread in self.threads])
        # context = f'<h1>КОНФИГУРАЦИЯ СИСТЕМЫ</h1>{global_text}\
        #           <h2>Конфигурации потоков</h2>{per_plot}<h2>Строки запуска</h2><ul>{cmds}</ul>'
        # return get_back_control_template(context)

    def stop(self, stop_index: int):
        if 0 <= stop_index < len(self.threads):
            self.threads[stop_index].kill()
            return 'THREAD STOP COMMAND!'
        else:
            return None

    def stop_iteration(self, index_element: int):
        if 0 <= index_element < len(self.threads):
            self.threads[index_element].need_stop_iteration = True
            return 'THREAD SET STOP ITERATION!'
        else:
            return None

    def stop_all(self):
        self.web_server_running = False
        self.main_config['auto_restart'] = False
        self.kill_all()
        return 'КОМАНДА ОСТАНОВКИ ПРОГРАММЫ (завершение в течении 1 минуту)'

    def kill_threads(self):
        for thread in self.threads:
            thread.shutdown()
        return 'КОМАНДА НЕМЕДЛЕННОЙ ОСТАНОВКИ ВСЕХ ПОТОКОВ!'

    def stop_iteration_all(self):
        for thread in self.threads:
            thread.stop()
        return 'КОМАНДА ОСТАНОВКИ ИТЕРАЦИЙ ВСЕХ ПОТОКОВ!'

    def restart_all(self):
        self.event.set()
        self.restart_command = True
        return 'TRY RESTART!'

    def wakeup_thread(self, index):
        if 0 <= index < len(self.threads):
            self.threads[index].wakeup()
            return 'THREAD WAKEUP COMMAND'
        else:
            return f'NO THREAD WITH INDEX {index}'

    def pause_thread(self, index, pause: int):
        if 0 <= index < len(self.threads):
            self.threads[index].set_pause(pause)
            return 'THREAD PAUSE ON NEXT ITERATION COMMAND'
        else:
            return f'NO THREAD WITH INDEX {index}'

    def get_telegram_message(self):
        now = datetime.now().strftime('%m/%d/%Y, %H:%M:%S')
        disk_info_data = [(p.mountpoint, psutil.disk_usage(p.mountpoint))
                          for p in psutil.disk_partitions() if p.fstype and p.opts.find('fixed') >= 0]
        disk_info = '\n'.join([f'HDD {di[0]} {(di[1].free / GIGABYTE):.2f}/'
                               f'{(di[1].total / GIGABYTE):.2f}Гб'
                               for di in disk_info_data])
        context = '\n'.join(
            [f'{i:2d}.ПОТОК {thread.name} {thread.current_iteration}/{thread.last} \
                ФАЗА {thread.phase} ПЛОТ ЗА {thread.last_iteration_time}'
             for i, thread in
             enumerate(self.threads)])
        message = f'{now}\nИнформция о дисках\n{disk_info}\n{context}'
        return message
