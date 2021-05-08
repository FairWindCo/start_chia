from pathlib import Path


def get_html_dict(dict_to_html, title=''):
    dict_info = '\n'.join([f'<tr><td>{k}</td><td>{v}</td></tr>' for k, v in dict_to_html.items()])
    return f'<div><h3>{title}</h3><table>{dict_info}</table></div>'


GIGABYTE = 1024 * 1024 * 1024


def get_command_for_execute_with_shell(cmd, config):
    run_in_shell = check_bool(config.get('start_shell', False))
    shelling_info = check_bool(config.get('p_open_shell', False))
    shell_name = config.get('shell_name', '')
    return [shell_name, cmd] if run_in_shell and shell_name else [el for el in cmd.split(' ') if
                                                                  el] if not shelling_info else cmd


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


def read_params_from_section(config_, section, default=None):
    if default is None:
        default = {}
    else:
        default = default.copy()
    from_file = {key: config_[section][key] for key in config_[section] if config_[section][key]}
    default.update(from_file)
    default['name'] = section
    return default


def convert_param_to_attribute(key, value):
    if key == 'thread_per_plot' and value:
        return f'-r {value}'
    if key == 'temp_dir' and value:
        return f'-t {value}'
    if key == 'work_dir' and value:
        return f'-d {value}'
    if key == 'memory' and value:
        return f'-b {value}'
    if key == 'bucket' and value:
        return f'-u {value}'
    if key == 'k_size' and value:
        return f'-r {value}'
    if key == 'bitfield_disable' and (value == 'True' or value == 'true'):
        return f'-e'
    if key == 'fingerprint' and value:
        return f'-a {value}'
    if key == 'pool_pub_key' and value:
        return f'-p {value}'
    if key == 'farmer_pub_key' and value:
        return f'-f {value}'
    return ''


def get_command_args(config_dict):
    args = [convert_param_to_attribute(key, val) for key, val in config_dict.items()]
    command = config_dict['chia_path']
    return f'{command} plots create {" ".join(args)}'
