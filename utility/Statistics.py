import datetime


class Statistics:
    def __init__(self):
        self.global_start_time = datetime.datetime.now()
        self.threads_statistics = {}
        self.threads_stat_info = {}

    def update_statistics(self, name:str, statistics):
        pass


