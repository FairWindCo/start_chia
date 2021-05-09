import os
import signal
import subprocess
import time
from threading import Thread, Event

import psutil

from chia_thread_config import get_threads_configs, ChieThreadConfig
from utils import check_bool, GIGABYTE, get_command_for_execute_with_shell, get_html_dict


class MainThread(Thread):

    def __init__(self):
        super().__init__()
        self.configs, self.main_config = get_threads_configs()
        self.threads = []
        self.all_thread_stopped = True
        self.web_server_running = True
        self.restart_command = False
        self.event = Event()

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
        while self.web_server_running:
            if self.need_start() and self.web_server_running:
                self.init_thread()
                self.start_workers()
            else:
                try:
                    if self.web_server_running:
                        self.event.sleep(60)
                        self.event.clear()
                except KeyboardInterrupt:
                    self.kill_all()
                    break

    def kill_all(self):
        self.main_config['auto_restart'] = False
        print('!TRY KILL ALL!')
        for thread in self.threads:
            thread.kill()
        self.web_server_running = False
        # os.kill(self.native_id, signal.CTRL_C_EVENT)
        self.event.set()
        self.shutdown_server()

    def index(self):
        load_avg = psutil.getloadavg()
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()  # self.ave_time
        disk_info_data = [(p.mountpoint, psutil.disk_usage(p.mountpoint))
                          for p in psutil.disk_partitions() if p.fstype and p.opts.find('fixed') >= 0]
        disk_info = '\n'.join([f'<li>ДИСК {di[0]} СВОБОДНО {(di[1].free / GIGABYTE):.2f}Гб '
                               f'из {(di[1].total / GIGABYTE):.2f}Гб  {di[1].percent}%</li>'
                               for di in disk_info_data])
        context = '\n'.join(
            [f'<li>{index_el:2d}.ПОТОК {thread.name} ВЫПОЛНЕНО {thread.current} из {thread.last} <BR>\
                ТЕКУЩАЯ ФАЗА {thread.phase} {thread.start_phase_info}<BR>\
                ЗАВЕРШЕННАЯ ФАЗА: {thread.end_phase_info} <BR>\
                ВРЕМЯ ПОСЛЕДНЕГО ПЛОТА {thread.last_time}<BR>\
                СРЕДНЕЕ ВРЕМЯ ПЛОТА {thread.ave_time}<BR>\
                <a href="/view_log/{thread.name}">VIEW LOG</a> \
                {thread.status}\
                </li>' for index_el, thread in
             enumerate(self.threads)])
        return f'<HTML><HEAD></HEAD> \
                 <BODY> \
                 <a href="/">ОБНОВИТЬ</a> \
                 <div><h3>СИСТЕМА</h3>ЗАГРУЗКА CPU {cpu_percent}% \
                 последние 1 мин {load_avg[0]}% 5 мин {load_avg[1]}% 15 мин {load_avg[2]}% \
                 </div> \
                 <div>\
                 Использование памяти доступно {(memory.available / GIGABYTE):6.2f}Gb \
                 из {(memory.total / GIGABYTE):6.2f}Gb\
                 <h6>Дисковая подсистема</h6><ul>{disk_info}</ul>\
                 </div>\
                 <a href="/">ОБНОВИТЬ</a> <h5>ПРОЦЕССЫ</h5>\
                 <UL>{context}</UL><div>\
                 <a href="/">ОБНОВИТЬ</a><br><a href="/stat">СТАТИСТИКА</a><br>\
                 <a href="/control">УПРАВЛЕНИЕ</a></div></BODY></HTML>'

    def control(self):
        load_avg = psutil.getloadavg()
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        context = '\n'.join(
            [f'<li>{i:2d}.ПОТОК {thread.name} ВЫПОЛНЕНО {thread.current} из {thread.last} <BR>\
                ТЕКУЩАЯ ФАЗА {thread.phase} ВРЕМЯ ПОСЛЕДНЕГО ПЛОТА В ПОТОКЕ {thread.last_time}<BR>\
                <a href="/view_log/{thread.name}">VIEW LOG</a> \
                <a href="/log/{thread.name}">СКАЧАТЬ LOG</a> \
                <a href="/stop/{i}">ОСТАНОВИТЬ</a> \
                <a href="/stop_iteration/{i}">СТОП ИТЕРАЦИИ</a> \
                </li>' for i, thread in
             enumerate(self.threads)])
        return f'<HTML><HEAD></HEAD> \
                 <BODY> \
                 <a href="/control">ОБНОВИТЬ</a> \
                 <div>ЗАГРУЗКА CPU {cpu_percent}% \
                 последние 1 мин {load_avg[0]}% 5 мин {load_avg[1]}% 15 мин {load_avg[2]}% \
                 </div> \
                 <div>\
                 Использование памяти доступно {(memory.available / GIGABYTE):6.2f}Gb \
                 из {(memory.total / GIGABYTE):6.2f}Gb\
                 </div>\
                 <a href="/control">ОБНОВИТЬ</a> \
                 <a href="/">ГЛАВНАЯ</a> \
                 <UL>{context}</UL>\
                 <div> \
                 <h5>Управление</h5><ul>\
                 <li><a href="/show_config">КОНФИГ</a></li> \
                 <li><a href="/stop_iteration_all">ОСТАНОВИТЬ ИТЕРАЦИИ</a></li> \
                 <li><a href = "/restart_workers">ПЕРЕЗАПУСТИТЬ ЕСЛИ ВСЕ ПОТОКИ ОСТАНОВЛЕНЫ</a></li> \
                 <li><a href = "/kill_threads">УБИТТЬ ВСЕ ПОТОКИ</a></li> \
                 <li><a href="/stop_all">SHUTDOWN (ЗАВЕРШИТЬ ПРОГРАММУ)</a></li>\
                 </ul>\
                 <a href="/get_self_program">СКАЧАТЬ ПРОГРАММУ</a>\
                 <a href="/get_self_src">СКАЧАТЬ ИСХОДНИК</a>\
                 </div></BODY></HTML>'

    def show_config(self):
        global_text = get_html_dict(self.main_config, 'Глобальная конфигурация')
        per_plot = ''.join([get_html_dict(thread.config, thread.name) for thread in self.threads])
        cmds = ''.join([f'<li>{thread.cmd}<li>' for thread in self.threads])
        context = f'<h1>КОНФИГУРАЦИЯ СИСТЕМЫ</h1>{global_text}\
                  <h2>Конфигурации потоков</h2>{per_plot}<h2>Строки запуска</h2><ul>{cmds}</ul>'
        return f'<HTML><HEAD></HEAD><BODY>{context}<a href="/control">BACK</a><a href="/">HOME</a></BODY></HTML>'

    def show_stat(self):
        def converter(info):
            phase_name, phase_info = info
            return get_html_dict(phase_info, phase_name)

        threads_info = '\n'.join([f'<div><h3>{thread.name}</h3><h4>{thread.cmd}</h4>\
                        {"".join(map(converter, thread.phase_stat.items()))}</div>'
                                  for thread in self.threads])

        context = f'<h1>Стататистика по фазам</h1>{threads_info}'
        return f'<HTML><HEAD></HEAD><BODY>{context}<a href="/">HOME</a></BODY></HTML>'

    def stop(self, stop_index: int):
        if 0 <= stop_index < len(self.threads):
            self.threads[stop_index].kill()
            context = f'THREAD STOPPED!<BR><<a href="/control">BACK</a><a href="/">HOME</a>'
            return f'<HTML><HEAD></HEAD><BODY><UL>{context}</UL></BODY></HTML>'
        else:
            return None

    def stop_iteration(self, index_element:int):
        if 0 <= index_element < len(self.threads):
            self.threads[index_element].need_stop_iteration = True
            context = f'THREAD SET STOP ITERATION!<BR><a href="/control">BACK</a><a href="/">HOME</a>'
            return f'<HTML><HEAD></HEAD><BODY><UL>{context}</UL></BODY></HTML>'
        else:
            return None

    def stop_all(self):
        self.main_config['auto_restart'] = False
        self.kill_all()
        context = 'КОМАНДА ОСТАНОВКИ ПРОГРАММЫ (завершение в течении 1 минуту)'
        return f'<HTML><HEAD></HEAD><BODY><UL>{context}</UL></BODY></HTML>'

    def kill_threads(self):
        for thread in self.threads:
            thread.kill()
        context = f'КОМАНДА НЕМЕДЛЕННОЙ ОСТАНОВКИ ВСЕХ ПОТОКОВ!<BR><a href="/control">BACK</a><a href="/">HOME</a>'
        return f'<HTML><HEAD></HEAD><BODY><UL>{context}</UL></BODY></HTML>'

    def stop_iteration_all(self):
        for thread in self.threads:
            thread.need_stop_iteration = True
        context = f'КОМАНДА ОСТАНОВКИ ИТЕРАЦИЙ ВСЕХ ПОТОКОВ!<BR><a href="/control">BACK</a><a href="/">HOME</a>'
        return f'<HTML><HEAD></HEAD><BODY><UL>{context}</UL></BODY></HTML>'

    def restart_all(self):
        self.event.set()
        self.restart_command = True
        context = f'TRY RESTART!<BR><a href="/control">BACK</a><a href="/">HOME</a>'
        return f'<HTML><HEAD></HEAD><BODY><UL>{context}</UL></BODY></HTML>'
