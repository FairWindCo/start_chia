import os
from datetime import datetime, timedelta
from pathlib import Path

import psutil


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


def disk_space(space: float) -> str:
    if space < 1024:
        return str(space)
    elif space < 1024 ** 2:
        return '{:.2f}Kb'.format(space / 1024)
    elif space < 1024 ** 3:
        return '{:.2f}Mb'.format(space / 1024 ** 2)
    elif space < 1024 ** 4:
        return '{:.2f}Gb'.format(space / 1024 ** 3)
    elif space < 1024 ** 5:
        return '{:.2f}Tb'.format(space / 1024 ** 4)
    else:
        return '{:.2f}Pb'.format(space / 1024 ** 5)


def work_free_space(path=None):
    print('ANALISE PATH', path)
    if path is None or not path:
        return 'unknown'
    try:
        if os.path.exists(path):
            space = disk_space(psutil.disk_usage(path).free)
            print('FOUND SPACE', space)
            return space
        else:
            head, tail = os.path.split(path)
            if tail or os.path.exists(head):
                return work_free_space(head)
            else:
                return 'unknown'
    except Exception as e:
        return 'unknown'
