import os
from pathlib import Path

from sanic import Sanic, html, response
from sanic.exceptions import abort
from sanic.response import stream

from main_thread import MainThread
from utils import line_by_line

app = Sanic("Web Server")


def shutdown_server():
    app.stop()


@app.route('/')
async def index(request):
    return html(app.ctx.processor.index())


@app.route('/get_self_program')
async def get_self_program(request):
    current_path = os.getcwd()
    return await response.file(directory=current_path, filename='main.exe')


@app.route('/log/<name>')
async def get_log(request, name):
    current_path = os.getcwd()
    path_to_log_file = Path(current_path).joinpath(f'{name}.log')
    print(path_to_log_file)
    if path_to_log_file.exists():
        return await response.file(directory=current_path, filename=f'{name}.log')
    else:
        abort(404)


@app.route('/view_log/<name>')
async def view_log(request, name):
    current_path = os.getcwd()
    path_to_log_file = Path(current_path).joinpath(f'{name}.log')
    if path_to_log_file.exists():
        async def gen_stream(response):
            with open(path_to_log_file, 'rt') as file:
                for line in file:
                    await response.write(f'{line}\n')
        return stream(gen_stream)
    else:
        abort(404)


@app.route('/control')
async def control(request):
    return html(app.ctx.processor.control())


@app.route('/stop_all')
async def stop_all(request):
    return html(app.ctx.processor.stop_all())


@app.route('/kill_threads')
async def kill_threads(request):
    return html(app.ctx.processor.kill_threads())

@app.route('/show_config')
async def show_config(request):
    return html(app.ctx.processor.show_config())

@app.route('/stat')
async def show_stat(request):
    return html(app.ctx.processor.show_stat())


@app.route('/stop_iteration_all')
async def stop_iteration_all(request):
    return html(app.ctx.processor.stop_iteration_all())

@app.route('/restart_workers')
async def restart_all(request):
    return html(app.ctx.processor.restart_all())


@app.route('/stop_iteration/<index_element:int>')
def stop_iteration(request, index_element):
    res = app.ctx.processor.stop_iteration(index_element)
    if res:
        return html(res)

@app.route('/stop/<stop_index:int>')
async def stop(requrst, stop_index):
    res = app.ctx.processor.stop(stop_index)
    if res:
        return html(res)


if __name__ == '__main__':
    processor = MainThread()
    app.ctx.processor = processor
    processor.start()
    app.run('0.0.0.0', 5050)
