import asyncio
import platform
import queue

from utility.SeparateThread import SeparateCycleThread
from utility.telegram_message import run_send_message_to_clients


class TelegramSenderThread(SeparateCycleThread):
    def __init__(self, processor):
        self.main_processor = processor
        self.api_id = self.main_processor.main_config.get('api_id')
        self.api_hash = self.main_processor.main_config.get('api_hash')
        self.send_to = self.main_processor.main_config.get('send_to', '').split(',')
        self.wait_message_sleep_time = int(self.main_processor.main_config.get('telegram_time', 600))
        self.machine_name = self.main_processor.main_config.get('machine_name', platform.node())
        super().__init__(name='Telegram Thread', inter_iteration_pause=0, pause_before=True)
        self.queue = queue.Queue()

    def send_message(self, message):
        self.queue.put_nowait(message)

    def on_start_thread(self):
        event_loop_a = asyncio.new_event_loop()
        asyncio.set_event_loop(event_loop_a)
        self.event.wait(5)

    def wakeup(self):
        self.queue.put_nowait(None)
        super().wakeup()

    def work_procedure(self, iteration) -> bool:
        if self.api_id and self.api_hash and self.send_to:
            message = self.queue.get(True, self.wait_message_sleep_time)
            if message:
                run_send_message_to_clients(self.send_to, f'[{self.machine_name}]:: {message}', self.api_id,
                                            self.api_hash)
            self.queue.task_done()
            return False
        else:
            return True
