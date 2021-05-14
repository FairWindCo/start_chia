import asyncio
from threading import Thread, Event

from telegram_message import run_send_message_to_clients


class TelegramThread(Thread):
    def __init__(self, processor):
        super().__init__(name='Telegram Thread')
        self.main_processor = processor
        self.worked = True
        self.event = Event()

    def run(self) -> None:
        api_id = self.main_processor.main_config.get('api_id')
        api_hash = self.main_processor.main_config.get('api_hash')
        send_to = self.main_processor.main_config.get('send_to', '').split(',')

        sleep_time = self.main_processor.main_config.get('telegram_time', 600)
        event_loop_a = asyncio.new_event_loop()
        asyncio.set_event_loop(event_loop_a)

        while self.worked:
            if api_id and api_hash and send_to:
                try:
                    run_send_message_to_clients(send_to, self.main_processor.get_telegram_message(), api_id, api_hash)
                except Exception as e:
                    print(e)
                self.event.wait(sleep_time)
            else:
                break
        self.worked = False

    def shutdown(self):
        self.worked = False
        self.event.set()
