from datetime import datetime
from functools import reduce

from sanic import Sanic

from utility.SeparateThread import SeparateCycleThread


class TelegramThread(SeparateCycleThread):
    def __init__(self, processor):
        self.main_processor = processor
        self.api_id = self.main_processor.main_config.get('api_id')
        self.api_hash = self.main_processor.main_config.get('api_hash')
        self.send_to = self.main_processor.main_config.get('send_to', '').split(',')
        self.short_message = self.main_processor.main_config.get('short_message', False)
        sleep_time = int(self.main_processor.main_config.get('telegram_time', 600))
        super().__init__(name='Telegram Thread', inter_iteration_pause=sleep_time, pause_before=True)
        self.last_send = datetime.now()
        self.last_plots = 0

    def on_start_thread(self):
        self.last_plots = reduce(lambda _sum, el: el.current_iteration + _sum, self.main_processor.threads, 0)
        self.event.wait(5)
        super().on_start_thread()

    def work_procedure(self, iteration) -> bool:
        if self.api_id and self.api_hash and self.send_to:
            try:
                now = datetime.now()
                current = reduce(lambda _sum, el: el.current_iteration + _sum, self.main_processor.threads, 0)
                delta = now - self.last_send
                created = current - self.last_plots
                if created > 0:
                    speed = delta / created
                else:
                    speed = 0
                if self.short_message:
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
                self.main_processor.messager.send_message(message)
                self.last_send = now
                self.last_plots = current
            except Exception as e:
                print(e)
        return False
