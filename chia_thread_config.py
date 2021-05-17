import configparser
import hashlib
import os
import sys
from pathlib import Path

from chia_thread import ChieThread
from utils import read_params_from_section, check_bool, find_chia, get_command_args

salt = os.urandom(32)  # Remember this


def get_hash(password):
    return hashlib.pbkdf2_hmac(
        'sha256',  # The hash digest algorithm for HMAC
        password.encode('utf-8'),  # Convert the password to bytes
        salt,  # Provide the salt
        100000  # It is recommended to use at least 100,000 iterations of SHA-256
    )


def get_threads_configs():
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
                      'fingerprint': None, 'pool_pub_key': None, 'farmer_pub_key': None,
                      'start_node': None, 'set_peer_address': None,
                      'start_shell': False, 'shell_name': 'powershell', 'p_open_shell': False, 'code_page': 'cp1251',
                      'bitfield_disable': 'False'}
    if not os.path.exists('config.ini'):
        with open('config.ini', 'wt') as file:
            file.write('[default]\n')
            file.writelines([f'{k}={v if v is not None else ""}\n' for k, v in default_config.items()])
    config = configparser.ConfigParser()
    config.read('config.ini')
    if 'default' in config.sections():
        default_config = read_params_from_section(config, 'default', default_config)
    chia_path = default_config.get('chia_path', None)
    is_imitator = chia_path.find('python.exe') >= 0
    if chia_path is None and not is_imitator and not Path(default_config['chia_path']).exists():
        if check_bool(default_config.get('auto_find_exe', True)):
            path_chia_exe = find_chia()
        else:
            path_chia_exe = False

        if path_chia_exe:
            default_config['chia_path'] = path_chia_exe
            print('WARNING: NO "chia_path" IN CONFIG FILE OR PATH INCORRECT!')
            print(f'USE PATH: {path_chia_exe}')
        else:
            print('ERROR: NO CHIA.EXE FILE FOUND!')
            sys.exit(1)
    password = get_hash(default_config.get('password', 'Qwerty12345'))
    default_config['password'] = password
    config_thread = [read_params_from_section(config, section, default_config) for section in config.sections()
                     if section != 'default']
    return config_thread, default_config


# matching = re.compile(r'Starting phase ([0-9]*/[0-9]*):\s*([A-Z][\w\d\s:\\\-".]+)\.\.\.\s+([A-Z][\w\d\s:]+)$')

# r'Starting phase ([0-9]*\/[0-9]*):\s*(.*)\s+([A-Z][a-z]{2,4}\s+[A-Z][a-z]{2,10}\s+\d{1,2}\s+\d{1,2}:\d{1,2}:\d{1,2}\s+\d{2,4}.*)$')


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
        result = [ChieThread(f'{self.name}-{index_el}', f'{self.name}_{index_el}', self.command, number, self.num_plots,
                             self.config['temp_dir'], self.config) for
                  index_el, number in
                  enumerate(self.process)]
        self.process = [0 for _ in range(self.num_parallel)]
        return result
