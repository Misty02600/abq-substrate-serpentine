from pathlib import Path
import configparser
from .modelname_format import encode_filename


def parse_and_convert_config_value(value_str, target_type):
    """
    解析配置值并转换为指定类型，支持单值和多值

    Args:
        value_str (str): 配置文件中的值字符串
        target_type (type): 目标类型类 (int, float, bool, str)

    Returns:
        list: 转换后的值列表

    Examples:
        ("0.5", float) -> [0.5]
        ("0.3,0.5,0.7", float) -> [0.3, 0.5, 0.7]
        ("1,2,3", int) -> [1, 2, 3]
        ("true", bool) -> [True]
        ("true,false", bool) -> [True, False]
    """
    # 去除空格
    value_str = value_str.strip()

    # 如果是空字符串，返回空列表
    if not value_str:
        return []

    # 如果包含逗号，说明是多值
    if ',' in value_str:
        string_values = [v.strip() for v in value_str.split(',') if v.strip()]
    else:
        string_values = [value_str]

    # 转换类型
    converted_values = []
    for v in string_values:
        if target_type == bool:
            converted_values.append(v.lower() in ('true', '1', 'yes', 'on'))
        elif target_type in (int, float):
            converted_values.append(target_type(v))
        else:  # str
            converted_values.append(v)

    return converted_values


def load_config(config_file=None, config_processor=None):
    """
    从INI文件加载配置，自动支持单值和多值参数，可选择后处理方法

    Args:
        config_file (str, optional): 配置文件路径，默认为脚本目录下的config.ini
        config_processor (Callable, optional): 配置后处理函数，如process_config_v1, process_config_v3等
                                             默认为None，不进行后处理

    Returns:
        list: 配置字典列表，每个字典代表一个配置组合
              单值参数时返回长度为1的列表
              多值参数时返回所有组合的列表
              如果指定了config_processor，返回后处理后的配置列表
    """
    if config_file is None:
        script_dir = Path(__file__).parent
        config_file = script_dir / "config.ini"

    # 读取INI配置文件
    config = configparser.ConfigParser()
    try:
        config.read(config_file, encoding='utf-8')
        print(f"已加载配置文件: {config_file}")
    except FileNotFoundError:
        raise FileNotFoundError(f"配置文件 {config_file} 不存在")
    except configparser.Error as e:
        raise configparser.Error(f"配置文件格式错误: {e}")

    # 定义参数及其类型（使用实际的Python类型）
    param_definitions = {
        'substrate': {
            'n_rows': int,
            'n_cols': int,
            'porosity': float,
            'depth': float,
            'substrate_seed_size': float,
            'substrate_edge_seed_size': float
        },
        'loading': {
            'u1': float,
            'u2': float
        },
        'wire': {
            'w': float,
            'l_1': float,
            'l_2': float,
            'm': int,
            'wire_seed_size': float,
            'wire_rotation_angle': float,
            'origin': str  # 添加origin参数支持，使用str类型后续转换为tuple
        },
        'pores': {
            'USE_STANDARD_CIRCLES': bool,
            'T_xi': float,
            'T_delta': float,
            'random_seed': int
        },
        'computing': {
            'num_cpus': int,
            'enable_restart': bool
        },
        'interaction': {
            'use_cohesive': bool
        },
        'analysis': {
            'stabilization_magnitude': float,
            'adaptive_damping_ratio': float
        },
        'output': {
            'global_output': bool
        },
        'naming': {
            'custom_naming_params': str
        }
    }

    # 解析所有参数的可能值
    param_values = {}
    custom_naming_params = None

    for section_name, params in param_definitions.items():
        for param_name, param_type in params.items():
            # 特殊处理命名配置参数
            if param_name == 'custom_naming_params':
                raw_value = config.get(section_name, param_name, fallback='')
                if raw_value.strip():
                    # 解析自定义命名参数列表
                    custom_naming_params = [p.strip() for p in raw_value.split(',') if p.strip()]
                continue

            # 特殊处理origin参数，转换为tuple
            if param_name == 'origin':
                raw_value = config.get(section_name, param_name, fallback='')
                if raw_value.strip():
                    # 解析origin字符串为tuple列表
                    # 支持单个origin: "0.5,1.0,0.1" -> [(0.5, 1.0, 0.1)]
                    # 支持多个origin (分号分隔): "0.5,1.0,0.1;0.6,1.1,0.1" -> [(0.5,1.0,0.1), (0.6,1.1,0.1)]
                    try:
                        origin_tuples = []
                        # 使用分号分隔多个origin
                        origin_strings = [s.strip() for s in raw_value.split(';') if s.strip()]

                        for origin_str in origin_strings:
                            origin_values = [float(v.strip()) for v in origin_str.split(',')]
                            if len(origin_values) == 3:
                                origin_tuples.append(tuple(origin_values))
                            else:
                                print(f"警告: origin参数需要3个值(x,y,z)，跳过: {origin_str}")

                        if origin_tuples:
                            param_values[param_name] = origin_tuples
                    except ValueError as e:
                        print(f"警告: origin参数格式错误，跳过: {raw_value}, 错误: {e}")
                continue

            # 特殊处理global_output参数，提供默认值
            if param_name == 'global_output':
                raw_value = config.get(section_name, param_name, fallback='false')
            else:
                raw_value = config.get(section_name, param_name, fallback='')

            # 跳过空值或不存在的配置项
            if not raw_value.strip():
                print(f"跳过空配置项: [{section_name}] {param_name}")
                continue

            # 解析并转换类型
            typed_values = parse_and_convert_config_value(raw_value, param_type)
            param_values[param_name] = typed_values

    # 生成所有参数组合
    import itertools

    # 获取所有参数名和对应的值列表
    param_names = list(param_values.keys())
    value_lists = [param_values[name] for name in param_names]

    # 生成笛卡尔积（所有可能的组合）
    combinations = list(itertools.product(*value_lists))

    # 将每个组合转换为配置字典
    config_list = []
    for combination in combinations:
        config_dict = dict(zip(param_names, combination))
        config_list.append(config_dict)

    # 为每个配置生成模型名称
    for config_dict in config_list:
        config_dict['modelname'] = encode_filename(config_dict, config_list, custom_naming_params)

    # 应用配置后处理（如果指定）
    if config_processor is not None:
        print(f"应用配置后处理: {config_processor.__name__}")
        processed_config_list = []
        for config_dict in config_list:
            processed_config = config_processor(config_dict)
            processed_config_list.append(processed_config)
        config_list = processed_config_list

    print(f"生成了 {len(config_list)} 个配置组合")
    return config_list


# 测试和调试部分
if __name__ == "__main__":
    print("=" * 50)
    print("Testing config.py functions")

    # 1. 加载配置
    try:
        configs = load_config()
        print(f"\nLoaded {len(configs)} configuration(s).")

        if configs:
            # 2. 为第一个配置生成模型名
            first_config = configs[0]
            model_name = encode_filename(first_config, configs)
            print(f"\nGenerated model name for the first config: {model_name}")

            # 3. 打印第一个配置的详细信息
            print("\nDetails of the first configuration:")
            for key, value in first_config.items():
                print(f"  - {key}: {value}")

    except FileNotFoundError as e:
        print(f"\nError: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

    print("=" * 50)
