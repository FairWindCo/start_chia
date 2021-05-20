import random
import sys
import time
from random import randint

from utility.utils import calc_wakeup_time

if __name__ == '__main__':
    def sleep_this(max_pause: int = 100):
        sleep_time = randint(1, max_pause)
        print(f'PAUSE {sleep_time} wakeup at {calc_wakeup_time(sleep_time)}')
        time.sleep(sleep_time)


    if 'plots' in sys.argv:
        sleep_this(3)
        print('Starting phase 1/4: Forward Propagation into tmp files... Thu May  6 18:53:00 2021')
        sleep_this()
        print('Time for phase 1 = 10872.973 seconds. CPU (211.410%) Thu May  6 21:54:13 2021')
        print('Starting phase 2/4: Backpropagation into tmp files... Thu May  6 21:54:13 2021')
        sleep_this()
        print('Time for phase 2 = 4256.909 seconds. CPU (96.860%) Thu May  6 23:05:10 2021')
        sleep_this()
        print(
            'Starting phase 3/4: Compression from tmp files into "D:\\plot-k32-2021-05-06-18-53-dbb77889eeff038560aed1947fa6f4e571a886f18df500cc9c94ce412900c400.plot.2.tmp" ... Thu May  6 23:05:10 2021')
        sleep_this()
        print('Time for phase 3 = 12527.374 seconds. CPU (86.320%) Fri May  7 02:33:57 2021')
        print(
            'Starting phase 4/4: Write Checkpoint tables into "D:\\plot-k32-2021-05-06-18-53-dbb77889eeff038560aed1947fa6f4e571a886f18df500cc9c94ce412900c400.plot.2.tmp" ... Fri May  7 02:33:57 2021')
        sleep_this()
        print('Time for phase 4 = 978.967 seconds. CPU (73.060%) Fri May  7 02:50:16 2021')
        print('Approximate working space used (without final file): 269.403 GiB')
        print('Final File size: 101.387 GiB')
        print('Total time = 28636.224 seconds. CPU (134.930%) Fri May  7 02:50:16 2021')
    elif 'wallet' in sys.argv:
        text = ['Wallet height: 231665',
                'Sync status: Not synced',
                'Balances, fingerprint: 465454656',
                'Wallet ID 1 type STANDARD_WALLET',
                '   -Total Balance: 0.0 xch (0 mojo)',
                '   -Pending Total Balance: 0.0 xch (0 mojo)',
                '   -Spendable: 0.0 xch (0 mojo)']
        for line in text:
            print(line)
        sleep_this(5)
    elif 'farm' in sys.argv:
        text = ['Farming status: Syncing',
                'Total chia farmed: 0.0',
                'User transaction fees: 0.0',
                'Block rewards: 0.0',
                'Last height farmed: 0',
                'Plot count: Unknown',
                'Total size of plots: Unknown',
                'Estimated network space: 4501.810 PiB',
                'Expected time to win: Unknown',
                "Note: log into your key using 'chia wallet show' to see rewards for each key"]
        for line in text:
            print(line)
        sleep_this(5)
    elif 'show' in sys.argv:
        if '-c' in sys.argv:
            text = [
                'Connections:',
                'Type         IP             Ports             NodeID   Last Connect            MiB  Up|Dwn',
                'FULL_NODE  192.168.1.175  8444/8444        439bec42...      May 20 10: 46:17    0.0|0.0'
                '                             - SB      Height: 307608 - Hash: bcbc5833...'
            ]
            for line in text:
                print(line)
            sleep_this(2)
        elif '-s' in sys.argv:
            text = [
                'Current Blockchain Status: Not Synced. Peak height: 295099',
                '      Time: Mon May 17 2021 17:06:17 Ôèíëÿíäèÿ (ëåòî)                  Height:     295099',
                '',
                'Estimated network space: 5.988 EiB',
                'Current VDF sub_slot_iters: 114294784',
                'Total iterations since the start of the blockchain: 953377155836',
                '  Height: |   Hash:',
                '   295099 | 4a2fb2cf33fb28cdb80926154883166d2058573ae73647179704787695f95c86',
                '   295093 | 4a2fb2cf33fb28cdb80926154883166d2058573ae73647179704787695f95c86',
                '   465466 | 4a2fb2cf33fb28cdb80926154883166d2058573ae73647179704787695f95c86',
                '   295299 | 4a2fb2cf33fb28cdb80926154883166d2058573ae73647179704787695f95c86',
                '   295294 | 4a2fb2cf33fb28cdb80926154883166d2058573ae73647179704787695f95c86',
                '   295396 | 4a2fb2cf33fb28cdb80926154883166d2058573ae73647179704787695f95c86',
                '   295498 | 4a2fb2cf33fb28cdb80926154883166d2058573ae73647179704787695f95c86',
                '   295099 | 4a2fb2cf33fb28cdb80926154883166d2058573ae73647179704787695f95c86',
            ]
            for line in text:
                print(line)
            sleep_this(2)
        elif '-a' in sys.argv:
            text = ['Connecting to 192.168.1.107, 8444']
            for line in text:
                print(line)
            if random.randint(0, 1) == 1:
                print('Failed to connect to 192.168.1.107:8444')
            sleep_this(2)
