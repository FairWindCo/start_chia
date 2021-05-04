import configparser
import subprocess
from datetime import datetime
from pathlib import Path
from threading import Thread


def find_chia():
    for path in Path('/').rglob('chia.exe'):
        return path


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
    config_thread = [read_params_from_section(config, section, default_config) for section in config.sections()
                     if section != 'default']
    return config_thread


class ChieThread(Thread):
    def __init__(self, name, file, cmd, current, last):
        super().__init__(name=name)
        self.file = file
        self.cmd = cmd
        self.current = current
        self.last = last

    def write_last(self):
        with open(self.file, 'wt') as file:
            file.write(f'{self.current}')

    def run(self) -> None:
        # print(f'INIT COMMAND {self.cmd} {self.current} {self.last}')
        with open(f'{self.name}.log', 'at') as log:
            log.write(
                f'{datetime.now().strftime("%d.%m.%Y %H:%M:%S")} START WORK from {self.current} to {self.last}\n')
            for ind in range(self.current, self.last):
                try:
                    start_time = datetime.now()
                    process = subprocess.run(['powershell', self.cmd], stderr=subprocess.PIPE)
                    if process.returncode == 0:
                        time = datetime.now() - start_time
                        print(f'COMMAND {self.cmd}')
                        # process.wait()
                        self.current = ind + 1
                        self.write_last()
                        current_date = datetime.now()
                        log.write(
                            f'{current_date.strftime("%d.%m.%Y %H:%M:%S")} plot {self.current:3d} created at {time}\n')
                    else:
                        current_date = datetime.now()
                        error_text = process.stderr.decode('cp866')
                        log.write(
                            f'{current_date.strftime("%d.%m.%Y %H:%M:%S")} ERROR {self.current:3d}: {error_text}\n')
                except Exception as e:
                    current_date = datetime.now()
                    log.write(f'{current_date.strftime("%d.%m.%Y %H:%M:%S")} ERROR {e} plot {self.current} created \n\n')


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
        return [ChieThread(f'{self.name}-{index}', f'{self.name}_{index}', self.command, number, self.num_plots) for
                index, number in
                enumerate(self.process)]


if __name__ == '__main__':
    configs = get_threads_configs()
    threads = [thread for conf in configs for thread in ChieThreadConfig(conf).get_threads()]
    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()
