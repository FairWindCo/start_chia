from chia.ChiaConnector import ChiaConnector


# async def load(ca_crt_path, ca_key_path, crt_path, key_path):
#     self_hostname = 'localhost'
#     port = 8555
#     url = f'https://{self_hostname}:{str(port)}/'
#     session = aiohttp.ClientSession()
#     path = 'get_blockchain_state'
#     async with session.post(url + path, json={},
#                             ssl_context=ssl_context_for_client(ca_crt_path, ca_key_path, crt_path, key_path)
#                             ) as response:
#         response.raise_for_status()
#         res_json = await response.json()
#         if not res_json["success"]:
#             raise ValueError(res_json)
#         return res_json
#
#
# async def async_main_procedure():
#     config_path = r'C:\Users\serge\.chia\mainnet\config'
#     ca_crt_path = os.path.join(config_path, r'ssl/ca/private_ca.crt')  # path / config["private_ssl_ca"]["crt"],
#     ca_key_path = os.path.join(config_path, r'ssl/ca/private_ca.key')  # path / config["private_ssl_ca"]["key"],
#     crt_path = os.path.join(config_path,
#                             r'ssl/daemon/private_daemon.crt')  # root_path / net_config["daemon_ssl"]["private_crt"]
#     key_path = os.path.join(config_path,
#                             r'ssl/daemon/private_daemon.key')  # root_path / net_config["daemon_ssl"]["private_key"]
#     res = await load(ca_crt_path, ca_key_path, crt_path, key_path)
#     print(res)
#
#
# def async_main():
#     event_loop = asyncio.get_event_loop()
#     event_loop.run_until_complete(async_main_procedure())


if __name__ == '__main__':
    connector = ChiaConnector('dfgfd')
    # res = connector.get_farmed_amount()
    # print(res)
    # res = connector.get_connections()
    # print(res)
    # res = connector.get_blockchain_state()
    # print(res)
    # res = connector.wallet_sync_status(9256)
    # print(res)
    # res = connector.get_wallets_info(9256)
    # print(res)
    # print()
    res = connector.get_status_info()
    print(res)
    print(connector.add_connection('192.168.1.175', 8444))
    print(connector.add_connection('192.168.1.176', 8444))