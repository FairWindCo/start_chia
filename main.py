import os
import sys
from collections import deque
from pathlib import Path

import jinja2
from sanic import Sanic, response
from sanic.exceptions import abort
from sanic.response import stream
from sanic_auth import Auth, User
from sanic_jinja2 import SanicJinja2
from sanic_session import Session

from chia_thread_config import get_hash
from main_thread import MainThread


def get_current_path(*relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.getcwd()
    return os.path.join(base_path, *relative_path)


app = Sanic(name="Web Server")
auth = Auth(app)
session = Session(app)
jinja = SanicJinja2(app, session=session, loader=jinja2.FileSystemLoader(get_current_path('templates')))


def handle_no_auth(request):
    return response.redirect('/login')


def shutdown_server():
    app.stop()


@app.route('/get_self_program')
async def get_self_program(request):
    current_path = os.getcwd()
    path = os.path.join(current_path, 'main.exe')
    return await response.file(path, filename='main.exe')


@app.route('/log/<name>')
async def get_log(request, name):
    current_path = os.getcwd()
    path_to_log_file = Path(current_path).joinpath(f'{name}.log')
    print(path_to_log_file)
    if path_to_log_file.exists():
        return await response.file(path_to_log_file, filename=f'{name}.log')
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
                    if line and not line == '\n' and not line == '\r':
                        await response.write(f'{line}')

        return stream(gen_stream)
    else:
        abort(404)


@app.route('/lastlog/<name>')
async def view_log(request, name):
    current_path = os.getcwd()
    path_to_log_file = Path(current_path).joinpath(f'{name}.log')
    if path_to_log_file.exists():
        lines = []
        with open(path_to_log_file, 'rt') as file:
            lines = deque(filter(lambda el: el and el[0] not in ['\n', '\r'], file.readlines()), 30)
            lines.reverse()
            print(lines)
        return jinja.render('lastlog.html', request, lines=lines, name=name)
    else:
        abort(404)


async def stop_web_server():
    app.stop()


@app.route('/stop_all')
@auth.login_required(handle_no_auth=handle_no_auth)
async def stop_all(request):
    context = app.ctx.processor.stop_all()
    app.add_task(stop_web_server)
    return jinja.render('menu.html', request, context=context)


@app.route('/kill_threads')
@auth.login_required(handle_no_auth=handle_no_auth)
async def kill_threads(request):
    res = app.ctx.processor.kill_threads()
    return jinja.render('menu.html', request, context=res)


@app.route('/show_config')
@auth.login_required(handle_no_auth=handle_no_auth)
async def show_config(request):
    return jinja.render('configs.html', request, **app.ctx.processor.show_config())


@app.route('/stat')
async def show_stat(request):
    return jinja.render('statistics.html', request, threads=app.ctx.processor.threads)


@app.route('/stop_iteration_all')
@auth.login_required(handle_no_auth=handle_no_auth)
async def stop_iteration_all(request):
    res = app.ctx.processor.stop_iteration_all()
    return jinja.render('menu.html', request, context=res)


@app.route('/restart_workers')
@auth.login_required(handle_no_auth=handle_no_auth)
async def restart_all(request):
    res = app.ctx.processor.restart_all()
    return jinja.render('menu.html', request, context=res)


@app.route('/stop_iteration/<index_element:int>')
@auth.login_required(handle_no_auth=handle_no_auth)
def stop_iteration(request, index_element: int):
    res = app.ctx.processor.stop_iteration(index_element)
    return jinja.render('menu.html', request, context=res)


@app.route('/wakeup/<index_element:int>')
@auth.login_required(handle_no_auth=handle_no_auth)
def wakeup(request, index_element: int):
    res = app.ctx.processor.wakeup_thread(index_element)
    return jinja.render('menu.html', request, context=res)


@app.route('/pause/<index_element:int>', methods=['GET', 'POST'])
@auth.login_required(handle_no_auth=handle_no_auth)
def pause(request, index_element: int):
    if 0 <= index_element < len(app.ctx.processor.threads):
        thread_info = app.ctx.processor.threads[index_element]
        if request.method == 'POST':
            try:
                new_pause = int(request.form.get('pause', 0))
                res = app.ctx.processor.pause_thread(index_element, new_pause)
            except ValueError:
                res = 'Не верное значение'
            return jinja.render('menu.html', request, context=res)
        message = 'ПОТОК УЖЕ НА ПАУЗЕ' if thread_info.thread_paused else ''
        return jinja.render('pause.html', request, name=thread_info.name, count_task=thread_info.last,
                            current_task=thread_info.current, message=message)
    else:
        abort(404)


@app.route('/stop/<stop_index:int>')
@auth.login_required(handle_no_auth=handle_no_auth)
async def stop(request, stop_index: int):
    res = app.ctx.processor.stop(stop_index)
    jinja.flash(request, 'SEND STOP REQUEST')
    if res:
        context = 'SEND STOP REQUEST'

    else:
        context = 'NO PROCESSOR'
    return jinja.render('menu.html', request, context=context)


@app.route('/login', methods=['GET', 'POST'])
async def login(request):
    message = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # for demonstration purpose only, you should use more robust method
        if username == 'admin' and get_hash(password) == processor.main_config['password']:
            # use User proxy in sanic_auth, this should be some ORM model
            # object in production, the default implementation of
            # auth.login_user expects User.id and User.name available
            user = User(id=1, name=username)
            auth.login_user(request, user)
            jinja.flash(request, f'User login {username}')
            return response.redirect('/')
        if username or password:
            jinja.flash(request, 'invalid username or password')
            message = 'invalid username or password'
    return jinja.render('login.html', request, message=message)


@app.route('/logout')
@auth.login_required
async def logout(request):
    auth.logout_user(request)
    return response.redirect('/login')


@app.route('/wallet')
async def get_wallet(request):
    return jinja.render('wallet.html', request, wallet=app.ctx.processor.info.wallet_info)


@app.route('/control')
@auth.login_required(handle_no_auth=handle_no_auth)
async def get_control(request):
    return jinja.render('control.html', request, **app.ctx.processor.get_main_info())


@app.route('/')
async def get_log(request):
    return jinja.render('main.html', request, **app.ctx.processor.get_main_info())


@app.route('/modify/<index:int>', methods=['GET', 'POST'])
@auth.login_required(handle_no_auth=handle_no_auth)
async def modify_count(request, index: int):
    if 0 <= index < len(app.ctx.processor.threads):
        thread_info = app.ctx.processor.threads[index]
        message = ''
        if request.method == 'POST':
            try:
                new_count = int(request.form.get('count', thread_info.last))
                thread_info.last = new_count
            except ValueError as e:
                message = e
        return jinja.render('modify.html', request, name=thread_info.name, count_task=thread_info.last,
                            current_task=thread_info.current, message=message)
    else:
        abort(404)


if __name__ == '__main__':
    processor = MainThread()
    app.ctx.processor = processor
    app.ctx.jinja = jinja
    processor.start()
    try:
        app.static('/assert', get_current_path('assert'))
        try:
            app.run('0.0.0.0', 5050)
        except Exception:
            processor.kill_all()
    except OSError:
        processor.kill_all()
