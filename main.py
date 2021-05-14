import os
import sys
from pathlib import Path

import jinja2
from sanic import Sanic, html, response
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


@app.route('/stop_all')
@auth.login_required(handle_no_auth=handle_no_auth)
async def stop_all(request):
    context = app.ctx.processor.stop_all()
    app.add_task(lambda _: app.stop())
    return html(context)


@app.route('/kill_threads')
@auth.login_required(handle_no_auth=handle_no_auth)
async def kill_threads(request):
    return html(app.ctx.processor.kill_threads())


@app.route('/show_config')
@auth.login_required(handle_no_auth=handle_no_auth)
async def show_config(request):
    return html(app.ctx.processor.show_config())


@app.route('/stat')
async def show_stat(request):
    return html(app.ctx.processor.show_stat())


@app.route('/stop_iteration_all')
@auth.login_required(handle_no_auth=handle_no_auth)
async def stop_iteration_all(request):
    return html(app.ctx.processor.stop_iteration_all())


@app.route('/restart_workers')
@auth.login_required(handle_no_auth=handle_no_auth)
async def restart_all(request):
    return html(app.ctx.processor.restart_all())


@app.route('/stop_iteration/<index_element:int>')
@auth.login_required(handle_no_auth=handle_no_auth)
def stop_iteration(request, index_element):
    res = app.ctx.processor.stop_iteration(index_element)
    if res:
        return html(res)


@app.route('/stop/<stop_index:int>')
@auth.login_required(handle_no_auth=handle_no_auth)
async def stop(request, stop_index):
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
    return html(processor.show_wallet())


@app.route('/test')
async def get_log(request):
    current_path = get_current_path('templates', 'test.html')
    return jinja.render('test.html', request, greetings="Hello, sanic!")


@app.route('/control')
@auth.login_required(handle_no_auth=handle_no_auth)
async def get_control(request):
    return jinja.render('control.html', request, **app.ctx.processor.get_main_info())


@app.route('/')
async def get_log(request):
    return jinja.render('main.html', request, **app.ctx.processor.get_main_info())


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
