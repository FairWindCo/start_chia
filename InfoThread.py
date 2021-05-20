import re

import requests as requests
from bs4 import BeautifulSoup

from utility.SeparateSubprocessThread import SeparateCycleProcessCommandThread
from utility.utils import check_bool

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

        self.local_nodes = self.main_processor.main_config.get('local_nodes', '').split(',')
        self.search_nodes_site = self.main_processor.main_config.get('search_nodes_site', '')
        self.search_nodes = check_bool(self.main_processor.main_config.get('search_nodes', 'true'))

        super().__init__(self.chia_exe, self.main_processor.main_config, name='Information Thread',
                         inter_iteration_pause=sleep_time, pause_before=False)
        self.wallet_info = {}
        self.farm_info = {}
        self.global_sync = False
        self.global_height = 0

    def work_procedure(self, iteration) -> bool:
        for line in self.run_command_and_get_output(f'{self.chia_exe} wallet show', iteration):
            if line.startswith('Connection error.'):
                self.wallet_info['error'] = line
                break
            if res := wallet_height_reg.search(line):
                if 'error' in self.wallet_info:
                    del self.wallet_info['error']
                self.wallet_info['Wallet height'] = res.group(1)
                self.global_height = int(res.group(1).strip())

            elif res := wallet_sync_reg.search(line):
                self.wallet_info['Sync status'] = res.group(1)
                if res.group(1).strip().startswith('Sync'):
                    self.global_sync = True
                else:
                    self.global_sync = False

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
        for line in self.run_command_and_get_output(f'{self.chia_exe} show -s', iteration):
            if line.startswith('Connection error.'):
                self.farm_info['error'] = line
                break
            clear_text = line.strip()
            if clear_text.startswith('Current Blockchain Status'):
                ln = len('Current Blockchain Status')
                sub_text = clear_text[ln + 1:]
                status, peak = sub_text.split('.')
                self.farm_info['Current Blockchain Status'] = status
                if status.strip().startswith('Sync'):
                    self.global_sync = True
                else:
                    self.global_sync = False
            elif clear_text.startswith('Time:'):
                height = clear_text.find('Height:', 5)
                self.farm_info['Last Sync Time'] = clear_text[5:height].strip()
            elif (pos := clear_text.find('|')) > 0:
                self.farm_info[clear_text[:pos]] = clear_text[pos + 1:]
            elif (pos := clear_text.find(':')) > 0:
                self.farm_info[clear_text[:pos]] = clear_text[pos + 1:]
        if not self.global_sync:
            for local_node in self.local_nodes:
                self.connect_node(local_node, iteration)
            if self.search_nodes_site and self.search_nodes:
                nodes = self.get_nodes_from_site(self.search_nodes_site)
                for node in nodes:
                    self.connect_node(node, iteration)
        return False

    def connect_node(self, node, iteration_index):
        for line in self.run_command_and_get_output(f'{self.chia_exe} show -a {node}', iteration_index):
            if line.startswith('Connecting to'):
                ip, port = line[14:].split(',')
                self.farm_info[ip.strip()] = 'Connected'
            elif line.startswith('Failed to connect to'):
                ip, port = line[21:].split(':')
                self.farm_info[ip.strip()] = f'Failed to port {port}'

    def get_nodes_from_site(self, site):
        result = requests.get(site)
        if result.status_code == 200:
            soup = BeautifulSoup(result.content, 'html.parser')
            if soup:
                table = soup.find('table')
                if table:
                    rows = table.find_all('tr')
                    if rows:
                        res = [row.find_all('td') for row in rows]

                        return [f'{node[0].text}:{node[1].text}' for node in res if
                                node[2].text[2:-1].isdigit() and self.global_height <= int(node[2].text[2:-1])]
        return []
