from datetime import datetime, timedelta
from pathlib import Path


def get_html_dict(dict_to_html, title=''):
    dict_info = '\n'.join([f'<tr><td>{k}</td><td>{v}</td></tr>' for k, v in dict_to_html.items()])
    return f'<div><h3>{title}</h3><table>{dict_info}</table></div>'


GIGABYTE = 1024 * 1024 * 1024


def line_by_line(file_path):
    if Path(file_path).exists():
        yield '<a href="/">НАЗАД</a><BR>'
        with open(file_path, 'rt') as file:
            for row in file:
                yield f'{row}<BR>\n'
        yield '<a href="/">НАЗАД</a>'
    else:
        raise Exception(f'FILE {file_path} not found')


def check_bool(value, string_default=False):
    if value is None:
        return False
    value_type = type(value)
    if value_type == bool:
        return value
    if value_type == float or value_type == int:
        return value
    if value_type == str:
        if value.isnumeric():
            return bool(int(value))
        else:
            value = value.lower()
            if value == 'false' or value == 'f':
                return False
            elif value == 'true' or value == 't':
                return True
            else:
                return string_default
    return bool(value)


def find_chia():
    for found_path in Path('/').rglob('chia.exe'):
        if 20_000_000 > found_path.stat().st_size > 4_000_000:
            return found_path
        else:
            print(f'PATH FOUND: {found_path} {found_path.stat().st_size:3d}')


def read_params_from_section(config_, section, default=None, copy_list_name: [str] = None):
    if default is None:
        default = {}
    else:
        if copy_list_name is None:
            default = default.copy()
        else:
            default = {k: default.get(k, None) for k in copy_list_name}
    from_file = {key: config_[section][key] for key in config_[section] if config_[section][key]}
    default.update(from_file)
    default['name'] = section
    return default



def calc_wakeup_time(pause: float):
    return (datetime.now() + timedelta(seconds=pause)).strftime('%d.%m.%Y %H:%M:%S')
