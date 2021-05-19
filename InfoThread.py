import re

from utility.SeparateSubprocessThread import SeparateCycleProcessCommandThread

wallet_height_reg = re.compile(r'Wallet height:\s*(\d*).*')
wallet_balance_reg = re.compile(r'Total Balance:\s*([\d]*\.[\d]*)\s*xch.*')
wallet_pending_balance_reg = re.compile(r'Pending Total Balance:\s*([\d]*\.[\d]*)\s*xch.*')
wallet_spendable_balance_reg = re.compile(r'Spendable:\s*([\d]*\.[\d]*)\s*xch.*')
wallet_sync_reg = re.compile(r'Sync status:\s*(.*)')

farm_sync_reg = re.compile(r'\s*([A-Z][a-z0-9A-Z\s]*):\s*(.*)')


class InfoThread(SeparateCycleProcessCommandThread):

    def __init__(self, processor):
        self.main_processor = processor
        sleep_time = int(self.main_processor.main_config.get('info_update_time', 600))
        self.chia_exe = self.main_processor.main_config.get('chia_path')
        super().__init__(self.chia_exe, self.main_processor.main_config, name='Information Thread', inter_iteration_pause=sleep_time)
        self.wallet_info = {}

    def work_procedure(self, iteration) -> bool:
        for line in self.run_command_and_get_output(f'{self.chia_exe} wallet show', iteration):
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

        for line in self.run_command_and_get_output(f'{self.chia_exe} farm summary', iteration):
            if line.startswith('Connection error.'):
                self.wallet_info['error'] = line
            elif res := farm_sync_reg.search(line):
                self.wallet_info[res.group(1)] = res.group(2)
        return False
