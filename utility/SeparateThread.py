from datetime import datetime, timedelta
from itertools import count
from threading import Thread, Event


def calc_wakeup_time(pause: float):
    return (datetime.now() + timedelta(seconds=pause)).strftime('%d.%m.%Y %H:%M:%S')


class SeparateCycleThread(Thread):

    def __init__(self, before_start_pause: float = 0, inter_iteration_pause: float = 0, name: str = 'SeparateThread',
                 demon=None,
                 start_iteration_number: int = 0, pause_before: bool = True) -> None:
        super().__init__(name=name, daemon=demon)
        self.event = Event()
        self.start_iteration_number = start_iteration_number
        self.inter_iteration_pause = inter_iteration_pause
        self.pause_before = pause_before
        self.before_start_pause = before_start_pause
        self.worked = False
        self.stop_iteration_flag = False
        self.start_process_time = None
        self.start_iteration_time = None
        self.current_iteration = 0
        self.status = 'INIT'
        self.speed = timedelta(seconds=0)
        self.thread_paused = False
        self.last_iteration_time = timedelta(seconds=0)
        self.pause_once = False

    def on_start_thread(self):
        pass

    def on_stop_thread(self):
        pass

    def on_start_iteration(self, index):
        pass

    def on_end_iteration(self, index):
        pass

    def execute_pause(self, pause):
        at_run = calc_wakeup_time(pause)
        self.set_status(f'ПАУЗА ДО {at_run}')
        self.thread_paused = True
        self.event.wait(pause)
        self.event.clear()
        self.thread_paused = False

    def run(self) -> None:
        self.worked = True
        self.on_start_thread()
        if self.before_start_pause > 0:
            self.execute_pause(self.before_start_pause)
        self.start_process_time = datetime.now()
        for iteration_index in count(self.start_iteration_number):
            self.current_iteration = iteration_index
            if self.check_skip_iteration(iteration_index):
                continue
            if self.check_stop_iteration(iteration_index) or self.stop_iteration_flag:
                break
            self.on_start_iteration(iteration_index)
            if self.pause_before and self.inter_iteration_pause > 0:
                self.execute_pause(self.inter_iteration_pause)
                if self.pause_once:
                    self.inter_iteration_pause = 0
            self.set_status(f'START ITERATION {iteration_index}')
            self.start_iteration_time = datetime.now()
            try:
                need_break = self.work_procedure(iteration_index)
            except Exception as e:
                # DON`T ABORT THREAD ON EXCEPTION
                print(e)
                self.set_status(str(e))
                need_break = True
            self.last_iteration_time = datetime.now() - self.start_iteration_time
            self.on_end_iteration(iteration_index)
            if need_break:
                break
            if not self.pause_before and self.inter_iteration_pause > 0:
                self.execute_pause(self.inter_iteration_pause)
                if self.pause_once:
                    self.inter_iteration_pause = 0
        self.worked = False
        self.on_stop_thread()
        self.set_status('SHUTDOWN')
        print(f'Thread {self.name} - shutdown')

    def work_procedure(self, iteration) -> bool:
        pass

    def set_pause(self, pause_time: int):
        self.inter_iteration_pause = pause_time

    def set_pause_before(self, pause_before=True):
        self.pause_before = pause_before

    def check_skip_iteration(self, iteration_index: int) -> bool:
        return False

    def check_stop_iteration(self, iteration_index: int) -> bool:
        return self.stop_iteration_flag

    def stop(self):
        self.stop_iteration_flag = True

    def shutdown(self):
        self.stop()
        self.wakeup()

    def get_state(self):
        return self.worked

    def wakeup(self):
        self.event.set()
        self.set_status('RESUME')

    def get_statistics(self):
        now = datetime.now()
        work_time = now - self.start_process_time
        speed = (work_time / (self.current_iteration - 1)) if self.current_iteration > 1 else self.last_iteration_time
        return {
            'now': now,
            'current': self.current_iteration,
            'current_start': self.start_iteration_time,
            'last_time': self.last_iteration_time,
            'start_process_time': self.start_process_time,
            'work_time': work_time,
            'speed': speed
        }

    def set_status(self, text):
        self.status = f'{text} at [{datetime.now().strftime("%d.%m.%Y %H:%M:%S")}]'
