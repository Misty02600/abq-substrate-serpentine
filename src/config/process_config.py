from typing import Dict, Any


def process_config_v1(config_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理配置参数，补充计算得出的参数 - 版本1

    Args:
        config_params: 原始配置参数字典

    Returns:
        处理后的配置参数字典（直接修改原字典）
    """
    # n_cols = n_rows * 2（列数自动为行数的2倍）
    config_params['n_cols'] = config_params['n_rows'] * 2

    # square_size = 2 / n_rows（正方形边长自动为2/n_rows）
    config_params['square_size'] = 2 / config_params['n_rows']

    # 计算蛇形线原点坐标（仅在未手动指定origin时计算）
    if 'origin' not in config_params:
        substrate_width = config_params['n_cols'] * config_params['square_size']
        substrate_height = config_params['n_rows'] * config_params['square_size']
        origin = (substrate_width / 4, substrate_height / 2, config_params['depth'])
        config_params['origin'] = origin

    # 添加重启动控制参数，默认为False
    config_params.setdefault('enable_restart', False)

    return config_params


def process_config_v2(config_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理配置参数，补充计算得出的参数 - 版本2

    Args:
        config_params: 原始配置参数字典

    Returns:
        处理后的配置参数字典（直接修改原字典）
    """
    config_params['n_cols'] = config_params['n_rows'] * 2

    config_params['square_size'] = 1 / config_params['n_rows']

    # 计算蛇形线原点坐标（仅在未手动指定origin时计算）
    if 'origin' not in config_params:
        substrate_width = config_params['n_cols'] * config_params['square_size']
        substrate_height = config_params['n_rows'] * config_params['square_size']
        origin = (substrate_width / 4, substrate_height / 2, config_params['depth'])
        config_params['origin'] = origin

    # 添加重启动控制参数，默认为False
    config_params.setdefault('enable_restart', False)

    return config_params


def process_config_v3(config_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理配置参数，补充计算得出的参数 - 版本3

    Args:
        config_params: 原始配置参数字典

    Returns:
        处理后的配置参数字典（直接修改原字典）
    """
    import math

    config_params['n_cols'] = config_params['n_rows'] * 2

    config_params['square_size'] = 1 / config_params['n_rows']

    # 计算蛇形线原点坐标（仅在未手动指定origin时计算）
    if 'origin' not in config_params:
        substrate_width = config_params['n_cols'] * config_params['square_size']
        substrate_height = config_params['n_rows'] * config_params['square_size']
        origin = (substrate_width / 4, substrate_height / 2, config_params['depth'])
        config_params['origin'] = origin

    # 添加重启动控制参数，默认为False
    config_params.setdefault('enable_restart', False)

    return config_params