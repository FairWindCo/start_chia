import asyncio
from datetime import datetime
from functools import reduce
from threading import Thread, Event

from telegram_message import run_send_message_to_clients


class TelegramThread(Thread):
    def __init__(self, processor):
        super().__init__(name='Telegram Thread')
        self.main_processor = processor
        self.worked = True
        self.event = Event()
        self.last_send = None
        self.last_plots = 0

    def run(self) -> None:
        api_id = self.main_processor.main_config.get('api_id')
        api_hash = self.main_processor.main_config.get('api_hash')
        send_to = self.main_processor.main_config.get('send_to', '').split(',')
        short_message = self.main_processor.main_config.get('short_message', False)

        sleep_time = int(self.main_processor.main_config.get('telegram_time', 600))
        event_loop_a = asyncio.new_event_loop()
        asyncio.set_event_loop(event_loop_a)
        self.event.wait(5)
        self.last_plots = reduce(lambda _sum, el: el.current + _sum, self.main_processor.threads, 0)
        self.last_send = datetime.now()
        while self.worked:
            if api_id and api_hash and send_to:
                self.event.wait(sleep_time)
                try:
                    now = datetime.now()
                    current = reduce(lambda _sum, el: el.current + _sum, self.main_processor.threads, 0)
                    delta = now - self.last_send
                    created = current - self.last_plots
                    if created > 0:
                        speed = delta / created
                    else:
                        speed = 0
                    if short_message:
                        message = f'{now.strftime("%d.%m.%Y %H:%M:%S")}\n \
                        Создано {created} за {str(delta)}\n \
                        Скорость плот за {str(speed)} \n\
                        С момента старта создано всего {current}'
                    else:
                        info = self.main_processor.get_telegram_message()
                        message = f'{info}\n \
                        Создано {created} за {str(delta)}\n \
                        Скорость плот за {str(speed)} \n\
                        С момента старта создано всего {current}'
                    run_send_message_to_clients(send_to, message, api_id, api_hash)
                    self.last_send = now
                    self.last_plots = current
                except Exception as e:
                    print(e)

            else:
                break
        self.worked = False
        print(f'{self.name} - shutdown')

    def shutdown(self):
        self.worked = False
        self.event.set()
