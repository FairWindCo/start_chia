from datetime import datetime


class LogInterface:
    log = None

    def __init__(self, name) -> None:
        super().__init__()
        self.log = open(f'{name}.log', 'at')

    def write_log(self, text, need_time_stamp=True, need_stdout=False, need_flush=False):
        date = datetime.now().strftime("%d.%m.%Y %H:%M:%S ") if need_time_stamp else ''
        if need_stdout:
            print(f'{date}{text}')
        if self.log:
            try:
                self.log.write(f'{date}{text}\n')
                if need_flush and self.log:
                    self.log.flush()
            except IOError:
                pass

    def close_log(self):
        if self.log:
            self.log.close()
            self.log = None

    def __del__(self):
        if self.log:
            try:
                self.log.close()
            except IOError:
                pass
