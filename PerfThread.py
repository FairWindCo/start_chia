from datetime import datetime

import psutil

from utility.SeparateThread import SeparateCycleThread
from utility.utils import check_bool, get_disks_info

class PerfThread(SeparateCycleThread):

    def __init__(self, processor):
        self.main_processor = processor
        sleep_time = int(self.main_processor.main_config.get('perf_update_time', 600))

        super().__init__(name='Performance Thread',
                         inter_iteration_pause=sleep_time, pause_before=False)
        self.disk_info = {
            'last_info': None,
            'disks': []
        }
        self.performance = {
            'load_avg': [None, None, None],
            'update_time': None
        }

    def on_start_thread(self):
        super().on_start_thread()

    def work_procedure(self, iteration) -> bool:
        self.disk_info['last_info'] = datetime.now()
        self.disk_info['disks'] = get_disks_info()
        self.performance['update_time'] = datetime.now()
        self.performance['load_avg'] = psutil.getloadavg()
        self.performance['cpu'] = psutil.cpu_times()
        return False

