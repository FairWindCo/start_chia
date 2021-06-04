import re

import requests as requests
from bs4 import BeautifulSoup

from chia.ChiaConnector import ChiaConnector
from utility.SeparateThread import SeparateCycleThread
from utility.utils import check_bool

wallet_height_reg = re.compile(r'Wallet height:\s*(\d*).*')
wallet_balance_reg = re.compile(r'Total Balance:\s*([\d]*\.[\d]*)\s*xch.*')
wallet_pending_balance_reg = re.compile(r'Pending Total Balance:\s*([\d]*\.[\d]*)\s*xch.*')
wallet_spendable_balance_reg = re.compile(r'Spendable:\s*([\d]*\.[\d]*)\s*xch.*')
wallet_sync_reg = re.compile(r'Sync status:\s*(.*)')

farm_sync_reg = re.compile(r'\s*([A-Z][a-z0-9A-Z\s]*):\s*(.*)')


def get_nodes_from_site(site, global_height):
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
                            node[2].text[2:-1].isdigit() and global_height <= int(node[2].text[2:-1])]
    return []


class InfoThread(SeparateCycleThread):

    def __init__(self, processor):
        self.main_processor = processor
        sleep_time = int(self.main_processor.main_config.get('info_update_time', 600))
        self.chia_config_path = self.main_processor.main_config.get('chia_config_path', '')
        self.chia_farm_rpc = int(self.main_processor.main_config.get('chia_farm_rpc', 8555))
        self.chia_wallet_rpc = int(self.main_processor.main_config.get('chia_wallet_rpc', 9256))
        self.chia_harvester_rpc = int(self.main_processor.main_config.get('chia_harvester_rpc', 8560))
        self.chia_farm_host = self.main_processor.main_config.get('chia_farm_host', 'localhost')

        self.local_nodes = self.main_processor.main_config.get('local_nodes', '').split(',')
        self.search_nodes_site = self.main_processor.main_config.get('search_nodes_site', '')
        self.search_nodes = check_bool(self.main_processor.main_config.get('search_nodes', 'true'))

        super().__init__(name='Information Thread',
                         inter_iteration_pause=sleep_time, pause_before=False)
        self.farm_info = {}
        self.wallet_info = {'_responses': {
            'blockchain_code': -100,
            'connections_code': -100,
            'wallets_code': -100,
            'farmed_amount_code': -100,
            'wallet_sync_code': -100,
            'plots_code': -100,
            'dirs_code': -100,
        }}
        self.global_sync = None
        self.connector = None
        self.global_height = 0
        self.balance = None
        self.work_dirs = []

    def on_start_thread(self):
        super().on_start_thread()
        self.connector = ChiaConnector(self.chia_config_path)
        work_dirs = self.main_processor.get_all_work_dirs()
        self.work_dirs = work_dirs
        for work_dir in work_dirs:
            self.connector.add_plot_directory(work_dir, self.chia_harvester_rpc)

    def add_directory(self, dir_name):
        if self.connector:
            self.connector.add_plot_directory(dir_name, self.chia_harvester_rpc)

    def work_procedure(self, iteration) -> bool:
        temp_global_sync = self.global_sync
        self.wallet_info = self.connector.get_status_info(self.chia_farm_rpc, self.chia_wallet_rpc,
                                                          self.chia_harvester_rpc) if self.connector else {}

        if 'blockchain' in self.wallet_info and self.wallet_info['_responses']['blockchain_code'] == 200:
            self.global_height = self.wallet_info['blockchain']['blockchain_state']['peak']['height']
            self.global_sync = self.wallet_info['blockchain']['blockchain_state']['sync']['synced']
        if 'wallet_sync' in self.wallet_info and self.wallet_info['_responses']['wallet_sync_code'] == 200:
            self.global_sync = self.wallet_info['wallet_sync']['synced'] if self.global_sync is None else (
                    self.global_sync and self.wallet_info['wallet_sync']['synced'])

        if 'wallet_balance' in self.wallet_info and self.wallet_info['_responses']['wallets_code'] == 200:
            balance = self.wallet_info['wallet_balance']['confirmed_wallet_balance']
            if balance != self.balance and self.balance is not None:
                self.main_processor.messager.send_message(f'BALANCE CHANGE {self.global_sync}')
            self.balance = balance

        if self.main_processor.main_config and check_bool(
                self.main_processor.main_config.get('recheck_work_dir', False), False):
            for work_dir in self.work_dirs:
                self.connector.add_plot_directory(work_dir, self.chia_harvester_rpc)

        # ADD NODES
        if not self.global_sync:
            for local_node in self.local_nodes:
                self.connect_node(local_node)
            if self.search_nodes_site and self.search_nodes:
                nodes = get_nodes_from_site(self.search_nodes_site, self.global_height)
                for node in nodes:
                    self.connect_node(node)
        if temp_global_sync != self.global_sync or temp_global_sync is None:
            self.main_processor.messager.send_message(f'SYNC STATUS CHANGE {self.global_sync}')
        return False

    def connect_node(self, node):
        node_address = node.split(':')
        host = node_address[0].strip()
        if len(node_address) > 1:
            port = node_address[1]
        else:
            port = 8444
        if self.connector:
            res = self.connector.add_connection(host, port)
            self.farm_info[host] = 'Connected' if res else f'Failed to port {port}'
            return res
        return False
