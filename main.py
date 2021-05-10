import os
from pathlib import Path

from sanic import Sanic, html, response
from sanic.exceptions import abort
from sanic.response import stream
from sanic_auth import Auth, User

from chia_thread_config import get_hash
from main_thread import MainThread

app = Sanic("Web Server")
auth = Auth(app)

# NOTE
# For demonstration purpose, we use a mock-up globally-shared session object.
session = {}

def handle_no_auth(request):
    return response.redirect('/login')

@app.middleware('request')
async def add_session(request):
    request.ctx.session = session


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
@auth.login_required(user_keyword='user', handle_no_auth=handle_no_auth)
async def control(request):
    return html(app.ctx.processor.control())


@app.route('/stop_all')
@auth.login_required(user_keyword='user', handle_no_auth=handle_no_auth)
async def stop_all(request):
    return html(app.ctx.processor.stop_all())


@app.route('/kill_threads')
@auth.login_required(user_keyword='user', handle_no_auth=handle_no_auth)
async def kill_threads(request):
    return html(app.ctx.processor.kill_threads())


@app.route('/show_config')
@auth.login_required(user_keyword='user', handle_no_auth=handle_no_auth)
async def show_config(request):
    return html(app.ctx.processor.show_config())


@app.route('/stat')
async def show_stat(request):
    return html(app.ctx.processor.show_stat())


@app.route('/stop_iteration_all')
@auth.login_required(user_keyword='user', handle_no_auth=handle_no_auth)
async def stop_iteration_all(request):
    return html(app.ctx.processor.stop_iteration_all())


@app.route('/restart_workers')
@auth.login_required(user_keyword='user', handle_no_auth=handle_no_auth)
async def restart_all(request):
    return html(app.ctx.processor.restart_all())


@app.route('/stop_iteration/<index_element:int>')
@auth.login_required(user_keyword='user', handle_no_auth=handle_no_auth)
def stop_iteration(request, index_element):
    res = app.ctx.processor.stop_iteration(index_element)
    if res:
        return html(res)


@app.route('/stop/<stop_index:int>')
@auth.login_required(user_keyword='user', handle_no_auth=handle_no_auth)
async def stop(requrst, stop_index):
    res = app.ctx.processor.stop(stop_index)
    if res:
        return html(res)


LOGIN_FORM = '''
<h2>Please sign in, you can try:</h2>
<p>{}</p>
<form action="" method="POST">
  <input class="username" id="name" name="username"
    placeholder="username" type="text" value=""><br>
  <input class="password" id="password" name="password"
    placeholder="password" type="password" value=""><br>
  <input id="submit" name="submit" type="submit" value="Sign In">
</form>
'''


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
            return response.redirect('/')
        message = 'invalid username or password'
    return response.html(LOGIN_FORM.format(message))


@app.route('/logout')
@auth.login_required
async def logout(request):
    auth.logout_user(request)
    return response.redirect('/login')


if __name__ == '__main__':
    processor = MainThread()
    app.ctx.processor = processor
    processor.start()
    app.run('0.0.0.0', 5050)
