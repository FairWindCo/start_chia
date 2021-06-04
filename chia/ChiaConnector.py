import os
import ssl
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

import requests
import urllib3
from requests.adapters import HTTPAdapter, DEFAULT_POOLSIZE, DEFAULT_RETRIES, DEFAULT_POOLBLOCK
from urllib3 import poolmanager
from urllib3.exceptions import NewConnectionError


class TLSAdapter(HTTPAdapter):

    def __init__(self, ca_cert,
                 ca_key,
                 private_cert_path,
                 private_key_path,
                 pool_connections=DEFAULT_POOLSIZE,
                 pool_maxsize=DEFAULT_POOLSIZE, max_retries=DEFAULT_RETRIES,
                 pool_block=DEFAULT_POOLBLOCK) -> None:
        self.ca_cert = ca_cert
        self.ca_key = ca_key
        self.private_cert_path = private_cert_path
        self.private_key_path = private_key_path
        super().__init__(pool_connections, pool_maxsize, max_retries, pool_block)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        """Create and initialize the urllib3 PoolManager."""
        ssl_context = ssl_context_for_client(self.ca_cert, None, self.private_cert_path, self.private_key_path)
        self.poolmanager = poolmanager.PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_version=ssl.PROTOCOL_TLS,
            ssl_context=ssl_context)


def ssl_context_for_client(
        ca_cert: Path,
        ca_key: Path,
        private_cert_path: Path,
        private_key_path: Path,
) -> Optional[ssl.SSLContext]:
    ssl_context = ssl._create_unverified_context(purpose=ssl.Purpose.SERVER_AUTH, cafile=str(ca_cert))
    ssl_context.check_hostname = False
    ssl_context.load_cert_chain(certfile=str(private_cert_path), keyfile=str(private_key_path))
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    return ssl_context


class ChiaConnector:
    def __init__(self, chia_config_path: str = r'C:\Users\serge\.chia\mainnet\config', hostname='localhost') -> None:
        super().__init__()
        urllib3.disable_warnings()

        if not os.path.exists(chia_config_path) or not os.path.isdir(chia_config_path):
            for found_path in Path('/').rglob('.chia'):
                path = os.path.join(found_path, 'mainnet', 'config')
                if os.path.exists(path) and os.path.isdir(path):
                    print('FOUND', path)
                    chia_config_path = path
                    break

        self.chia_config_path = chia_config_path
        self.ca_crt_path = os.path.join(chia_config_path,
                                        r'ssl/ca/private_ca.crt')  # path / config["private_ssl_ca"]["crt"],
        self.ca_key_path = os.path.join(chia_config_path,
                                        r'ssl/ca/private_ca.key')  # path / config["private_ssl_ca"]["key"],
        self.crt_path = os.path.join(chia_config_path,
                                     r'ssl/daemon/private_daemon.crt')  # root_path / net_config["daemon_ssl"]["private_crt"]
        self.key_path = os.path.join(chia_config_path,
                                     r'ssl/daemon/private_daemon.key')  # root_path / net_config["daemon_ssl"]["private_key"]
        self.self_hostname = hostname
        self.adapter = TLSAdapter(self.ca_crt_path, self.ca_key_path, self.crt_path, self.key_path)
        self.session = requests.Session()
        self.session.mount('https://', self.adapter)

    def info_request(self, path, params=None, port=8555, del_success: bool = True) -> (Dict, int):
        if params is None:
            params = {}
        url = f'https://{self.self_hostname}:{str(port)}/'
        try:
            res = self.session.post(url + path, json=params, verify=False)
            if res.status_code == 200:
                response = res.json()
                if del_success and ('success' in response):
                    del response['success']
                return response, res.status_code
            else:
                return None, res.status_code
        except NewConnectionError:
            return None, -2
        except ConnectionError:
            return None, -1
        except IOError:
            return None, -3

    def get_connections(self, port=8555) -> (Dict, int):
        return self.info_request('get_connections', {}, port)

    def get_blockchain_state(self, port=8555) -> (Dict, int):
        return self.info_request('get_blockchain_state', {}, port)

    def get_farmed_amount(self, port=9256) -> (Dict, int):
        return self.info_request('get_farmed_amount', {}, port)

    def wallet_sync_status(self, port=9256) -> (Dict, int):
        return self.info_request('get_sync_status', {}, port)

    def get_height_info(self, port=9256) -> (Dict, int):
        return self.info_request('get_height_info', {}, port)

    def get_wallet_balance(self, wallet_id: str, port=9256) -> (Dict, int):
        return self.info_request('get_wallet_balance', {"wallet_id": wallet_id}, port)

    def get_wallets(self, port=9256) -> (Dict, int):
        return self.info_request('get_wallets', {}, port)

    def get_wallets_info(self, port=9256) -> (Dict, int):
        wallets, code = self.get_wallets(port)
        if code == 200:
            wallet_balances = {}
            wallets['wallet_balances'] = wallet_balances
            for wallet in wallets["wallets"]:
                wallet_id = wallet["id"]
                response, code = self.get_wallet_balance(wallet_id, port)
                if code == 200:
                    wallet_balances[wallet_id] = response
            syncstat, code = self.wallet_sync_status(port)
            if code == 200:
                wallets['sync_status'] = syncstat
            return wallets, 200
        return None, code

    def get_plots(self, port=8560) -> (Dict[str, Any], int):
        return self.info_request("get_plots", {}, port)

    def refresh_plots(self, port=8560) -> (None, int):
        return self.info_request("refresh_plots", {}, port)

    def delete_plot(self, filename: str, port=8560) -> (bool, int):
        return self.info_request("delete_plot", {"filename": filename}, port)

    def add_plot_directory(self, dirname: str, port=8560) -> (bool, int):
        res_obj, code = self.info_request("add_plot_directory", {"dirname": dirname}, port)
        if code == 200:
            return res_obj["success"]
        else:
            return False

    def get_plot_directories(self, port=8560) -> (List[str], int):
        return self.info_request("get_plot_directories", {}, port)

    async def remove_plot_directory(self, dirname: str, port=8560) -> bool:
        res_obj, code = self.info_request("remove_plot_directory", {"dirname": dirname}, port)
        if code == 200:
            return res_obj["success"]
        else:
            return False

    def add_connection(self, host: str, port: int = 8444, rpc_port=8555):
        res, res_code = self.info_request("open_connection", {"host": host, "port": int(port)}, rpc_port)
        if res_code == 200:
            if 'error' in res:
                return False
            return True
        else:
            return False

    def get_status_info(self, farm_rpc_port=8555, wallet_rpc_port=9256, harvester_rpc=8560):
        blockchain, blockchain_code = self.get_blockchain_state(farm_rpc_port)
        connections, connections_code = self.get_connections(farm_rpc_port)
        wallets, wallets_code = self.get_wallets(wallet_rpc_port)
        farmed_amount, farmed_amount_code = self.get_farmed_amount(wallet_rpc_port)
        plots, plots_code = self.get_plots(harvester_rpc)
        plot_dirs, dirs_code = self.get_plot_directories(harvester_rpc)
        wallet_sync, wallet_sync_code = self.wallet_sync_status(wallet_rpc_port)
        if plots_code == 200:
            count_plots = len(plots['plots'])
            for plot in plots['plots']:
                plot['file_size'] = plot['file_size'] / 1024 / 1024 / 1024
                plot['time_modified'] = datetime.fromtimestamp(plot['time_modified'])
        else:
            count_plots = 'Не известно'
        if wallets_code == 200:
            wallet_balances = [self.get_wallet_balance(wallet["id"]) for wallet in wallets['wallets']]
        else:
            wallet_balances = []

        return {
            'count_plots': count_plots,
            'blockchain': blockchain,
            'connections': connections,
            'wallets': wallets,
            'farmed_amount': farmed_amount,
            'wallet_sync': wallet_sync,
            'wallet_balances': wallet_balances,
            'plots': plots,
            'plot_dirs': plot_dirs,
            '_responses': {
                'blockchain_code': blockchain_code,
                'connections_code': connections_code,
                'wallets_code': wallets_code,
                'farmed_amount_code': farmed_amount_code,
                'wallet_sync_code': wallet_sync_code,
                'plots_code': plots_code,
                'dirs_code': dirs_code,
            }
        }
