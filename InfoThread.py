import re
import subprocess
from threading import Thread, Event

from utils import get_command_for_execute_with_shell

wallet_height_reg = re.compile(r'Wallet height:\s*(\d*).*')
wallet_balance_reg = re.compile(r'Total Balance:\s*([\d]*\.[\d]*)\s*xch.*')
wallet_pending_balance_reg = re.compile(r'Pending Total Balance:\s*([\d]*\.[\d]*)\s*xch.*')
wallet_spendable_balance_reg = re.compile(r'Spendable:\s*([\d]*\.[\d]*)\s*xch.*')
wallet_sync_reg = re.compile(r'Sync status:\s*(.*)')

farm_sync_reg = re.compile(r'\s*([A-Z][a-z0-9A-Z\s]*):\s*(.*)')


class InfoThread(Thread):
    def __init__(self, processor):
        super().__init__(name='Information Thread')
        self.main_processor = processor
        self.worked = True
        self.event = Event()
        self.wallet_info = {}

    def run(self) -> None:
        sleep_time = int(self.main_processor.main_config.get('info_update_time', 600))
        chia_exe = self.main_processor.main_config.get('chia_path')
        print(chia_exe)
        while self.worked:
            for line in self.run_command_and_get_output(f'{chia_exe} wallet show'):
                if line.startswith('Connection error.'):
                    self.wallet_info['error'] = line
                    break
                if res := wallet_height_reg.search(line):
                    if 'error' in self.wallet_info:
                        del self.wallet_info['error']
                    self.wallet_info['Wallet height'] = res.group(1)

                elif res := wallet_sync_reg.search(line):
                    self.wallet_info['Sync status'] = res.group(1)

                elif res := wallet_balance_reg.search(line):
                    self.wallet_info['Total Balance'] = res.group(1)

                elif res := wallet_pending_balance_reg.search(line):
                    self.wallet_info['Pending Total Balance'] = res.group(1)

                elif res := wallet_spendable_balance_reg.search(line):
                    self.wallet_info['Spendable'] = res.group(1)

            for line in self.run_command_and_get_output(f'{chia_exe} farm summary'):
                if line.startswith('Connection error.'):
                    self.wallet_info['error'] = line
                elif res := farm_sync_reg.search(line):
                    self.wallet_info[res.group(1)] = res.group(2)
            self.event.wait(sleep_time)
        print(f'{self.name} - shutdown')

    def shutdown(self):
        self.worked = False
        self.event.set()

    def run_command_and_get_output(self, cmd):
        start_shell = self.main_processor.main_config.get('start_shell', False)
        code_page = self.main_processor.main_config.get('code_page', 'utf8')
        cmd = get_command_for_execute_with_shell(cmd, self.main_processor.main_config)
        process = subprocess.Popen(cmd,
                                   stderr=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   shell=start_shell, encoding=code_page,
                                   universal_newlines=True)

        while self.worked and process.poll() is None:
            text = process.stdout.readline()
            if text:
                yield text
