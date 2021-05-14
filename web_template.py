HEAD = ''


def get_base_html_template(body='', head=''):
    html = f'''
        <HTML>
            <HEAD>{head}</HEAD>
            <BODY>{body}</BODY>
        </HTML>
    '''
    return html


def get_back_template(body):
    return get_base_html_template(f'{body}<BR><a href="/">ДОМОЙ</a>', HEAD)


def get_back_control_template(body):
    return get_back_template(f'{body}<BR><a href="/control">BACK</a>')
