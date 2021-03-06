import subprocess
from datetime import datetime
from threading import Thread, Event

import psutil

from InfoThread import InfoThread
from PerfThread import PerfThread
from TelegramSenderThread import TelegramSenderThread
from TelegramThread import TelegramThread
from chia_thread_config import ChieThreadConfig
from utility.SeparateSubprocessThread import get_command_for_execute_with_shell
from utility.utils import check_bool, GIGABYTE, get_disks_info_str, get_from_dicts


class MainThread(Thread):

    def __init__(self, thread_configs, main_configs):
        super().__init__(name='MAIN PROCESSOR')
        # self.configs, self.main_config = get_threads_configs()
        self.configs = thread_configs
        self.main_config = main_configs
        self.threads = []
        self.all_thread_stopped = True
        self.web_server_running = True
        self.restart_command = False
        self.event = Event()
        self.info = None
        self.perf = None
        self.telegram = None
        self.messager = None

    def need_start(self):
        if not self.threads:
            return True
        if self.all_thread_stopped and check_bool(self.main_config.get('auto_restart', False)):
            return True
        if self.all_thread_stopped and self.restart_command:
            self.restart_command = False
            return True
        return False

    def get_all_work_dirs(self):
        return list({conf['work_dir'] for conf in self.configs})

    def add_new_thread(self, config):
        new_threads = ChieThreadConfig(config).get_threads()
        for thread in new_threads:
            thread.start()
            self.threads.append(thread)

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
        self.perf = PerfThread(self)
        self.telegram = TelegramThread(self)
        self.messager = TelegramSenderThread(self)

        self.perf.start()
        self.info.start()
        self.telegram.start()
        self.messager.start()
        while self.web_server_running:
            if self.need_start() and self.web_server_running:
                self.init_thread()
                if self.threads:
                    print('START POOL')
                    self.start_workers()
                else:
                    self.event.wait(60 * 60)
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
        memory = psutil.virtual_memory()
        now = datetime.now().strftime('%m/%d/%Y, %H:%M:%S')

        return {
            'load_avg': self.perf.performance['load_avg'],
            'cpu_percent': psutil.cpu_percent(),
            'memory': (memory.available / GIGABYTE, memory.total / GIGABYTE),
            'disk_info': self.perf.disk_info["disks"],
            'threads': self.threads,
            'current_time': now,
            'plots': self.info.wallet_info.get('count_plots', 'UNKNOWN'),
            'farm_sync': get_from_dicts(self.info.wallet_info, 'blockchain.blockchain_state.sync.synced'),
            'wallet_sync': get_from_dicts(self.info.wallet_info, 'wallet_sync.synced'),
            'sync': self.info.global_sync,
        }

    def show_config(self):
        return {
            'threads': self.threads,
            'default_config': self.main_config,
        }
        # global_text = get_html_dict(self.main_config, '???????????????????? ????????????????????????')
        # per_plot = ''.join([get_html_dict(thread.config, thread.name) for thread in self.threads])
        # cmds = ''.join([f'<li>{thread.cmd}<li>' for thread in self.threads])
        # context = f'<h1>???????????????????????? ??????????????</h1>{global_text}\
        #           <h2>???????????????????????? ??????????????</h2>{per_plot}<h2>???????????? ??????????????</h2><ul>{cmds}</ul>'
        # return get_back_control_template(context)

    def stop(self, stop_index: int):
        if 0 <= stop_index < len(self.threads):
            self.threads[stop_index].kill_command()
            return 'THREAD STOP COMMAND!'
        else:
            return None

    def stop_iteration(self, index_element: int):
        if 0 <= index_element < len(self.threads):
            self.threads[index_element].need_stop_iteration = True
            return 'THREAD SET STOP ITERATION!'
        else:
            return None

    def restart_thread(self, index_element: int):
        if 0 <= index_element < len(self.threads):
            if self.threads[index_element].worked:
                return 'THREAD ALREADY RUNNING!'
            thread = self.threads[index_element].clone()
            thread.start()
            self.threads.append(thread)
            return 'TRY ADD NEW THREAD !'
        else:
            return None

    def stop_all(self):
        self.web_server_running = False
        self.main_config['auto_restart'] = False
        self.kill_all()
        return '?????????????? ?????????????????? ?????????????????? (???????????????????? ?? ?????????????? 1 ????????????)'

    def kill_threads(self):
        for thread in self.threads:
            thread.shutdown()
        return '?????????????? ?????????????????????? ?????????????????? ???????? ??????????????!'

    def stop_iteration_all(self):
        for thread in self.threads:
            thread.stop()
        return '?????????????? ?????????????????? ???????????????? ???????? ??????????????!'

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
        context = '\n'.join(
            [f'{i:2d}.?????????? {thread.name} {thread.current_iteration}/{thread.last} \
                ???????? {thread.phase} ???????? ???? {thread.last_iteration_time}'
             for i, thread in
             enumerate(self.threads)])
        message = f'{now}\n?????????????????? ?? ????????????\n{get_disks_info_str()}\n{context}'
        return message
