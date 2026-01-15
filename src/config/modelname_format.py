def std_to_str(val):
    """
    将数值转换为字符串表示（科学计数法和小数混用）

    Args:
        val: 要转换的数值

    Returns:
        str: 格式化后的字符串表示
    """
    # 转换为字符串并计算有效位数
    val_str = str(val)

    # 去除小数点和负号来计算有效位数
    digits_only = val_str.replace(".", "").replace("-", "").lstrip("0")
    if not digits_only:  # 如果是0
        digits_only = "0"

    effective_digits = len(digits_only)

    if effective_digits <= 3:
        # 有效位数 ≤ 3，使用小数表示，小数点用'p'代替
        return val_str.replace(".", "p")
    else:
        # 有效位数 > 3，使用科学计数法
        s = f"{val:e}"
        # 解析科学计数法
        base, exp = s.split('e')
        # 清理基数部分：去除多余的零和小数点
        base = base.rstrip('0').rstrip('.') if '.' in base else base
        # 清理指数部分：去除前导零
        exp = exp.replace("+0", "").replace("-0", "-").replace("+", "")
        return f"{base}e{exp}"


def str_to_std(val_str):
    """
    将字符串表示反转换为数值

    Args:
        val_str (str): 格式化的字符串表示

    Returns:
        float or int: 解析出的数值
    """
    # 处理科学计数法
    if 'e' in val_str:
        return float(val_str)

    # 处理小数点替换
    if 'p' in val_str:
        return float(val_str.replace('p', '.'))

    # 处理整数
    try:
        return int(val_str)
    except ValueError:
        return float(val_str)


def encode_filename(config_dict, all_configs, custom_naming_params=None):
    """
    将配置参数编码为模型名称，支持自定义命名参数选择

    Args:
        config_dict (dict): 当前配置的参数字典
        all_configs (list): 所有配置的列表，用于判断哪些参数是多值
        custom_naming_params (list, optional): 自定义要包含在命名中的参数列表

    Returns:
        str: 生成的模型名称
    """
    # 参数简写映射表
    param_abbreviations = {
        'porosity': 'phi',
        'T_xi': 'xi',
        'T_delta': 'delta',
        'random_seed': 'seed',
        'substrate_seed_size': 'sub',
        'wire_seed_size': 'wire',
        'substrate_edge_seed_size': 'edge',
        'n_rows': 'n',
        'depth': 'd',
        'w': 'w',
        'l_1': 'l1',
        'l_2': 'l2',
        'm': 'm',
        'u1': 'u1',
        'u2': 'u2',
        'enable_restart': 'restart',
        'global_output': 'global',
        'origin': 'org',
        'wire_rotation_angle': 'rot'
    }

    # 构建模型名称
    USE_STANDARD_CIRCLES = config_dict['USE_STANDARD_CIRCLES']
    name_parts = []

    # 添加分布类型前缀（所有模型都需要）
    if USE_STANDARD_CIRCLES:
        name_parts.append("std")
    else:
        name_parts.append("uni")

    # 确定要包含在命名中的参数
    # 定义自动计算的参数（不应该出现在自动命名中）
    auto_calculated_params = {'n_cols', 'square_size', 'modelname', 'origin'}

    if custom_naming_params:
        # 使用自定义参数列表
        params_to_include = set(custom_naming_params)
    else:
        # 自动检测多值参数，但排除自动计算的参数
        params_to_include = set()
        if len(all_configs) > 1:
            for param_name in config_dict.keys():
                if param_name in auto_calculated_params:
                    continue  # 跳过自动计算的参数
                values = {config.get(param_name) for config in all_configs}
                if len(values) > 1:  # 有多个不同的值
                    params_to_include.add(param_name)

    # 添加选定的参数（按字母顺序排序以确保一致性）
    for param_name in sorted(config_dict.keys()):
        # 跳过USE_STANDARD_CIRCLES（已经作为前缀处理）
        if param_name == 'USE_STANDARD_CIRCLES':
            continue

        # 跳过modelname（避免循环引用）
        if param_name == 'modelname':
            continue

        # 对于auto_calculated_params中的其他参数：
        # - 如果使用自动命名模式，跳过它们
        # - 如果使用自定义命名模式，只有在params_to_include中才包含
        if param_name in auto_calculated_params:
            if not custom_naming_params:
                continue  # 自动模式：跳过所有自动计算的参数
            elif param_name not in params_to_include:
                continue  # 自定义模式：只包含明确指定的参数

        # 只包含选定的参数且有简写映射的参数
        if param_name in params_to_include and param_name in param_abbreviations:
            value = config_dict[param_name]
            abbrev = param_abbreviations[param_name]

            # 根据参数类型格式化值
            if isinstance(value, bool):
                value_str = str(value).lower()
            elif isinstance(value, int):
                value_str = str(value)
            elif isinstance(value, tuple):
                # 处理tuple类型（如origin），将(x,y,z)格式化为 x-y-z
                value_str = '-'.join(std_to_str(v) for v in value)
            else:  # float
                value_str = std_to_str(value)

            name_parts.append(f"{abbrev}{value_str}")

    return "_".join(name_parts)


def decode_filename(model_name):
    """
    从模型名称反向解析出参数值

    Args:
        model_name (str): 要解析的模型名称

    Returns:
        dict: 包含解析出的参数值的字典

    Example:
        decode_filename("std_phi0p3_delta0p05_seed1")
        返回: {
            'USE_STANDARD_CIRCLES': True,
            'porosity': 0.3,
            'T_delta': 0.05,
            'random_seed': 1
        }
    """
    # 参数简写到完整名称的映射（反向映射）
    abbreviation_to_param = {
        'phi': 'porosity',
        'xi': 'T_xi',
        'delta': 'T_delta',
        'seed': 'random_seed',
        'sub': 'substrate_seed_size',
        'wire': 'wire_seed_size',
        'edge': 'substrate_edge_seed_size',
        'n': 'n_rows',
        'd': 'depth',
        'w': 'w',
        'l1': 'l_1',
        'l2': 'l_2',
        'm': 'm',
        'u1': 'u1',
        'u2': 'u2',
        'restart': 'enable_restart',
        'global': 'global_output'
    }

    # 参数类型映射，用于正确转换数据类型
    param_types = {
        'porosity': float,
        'T_xi': float,
        'T_delta': float,
        'random_seed': int,
        'substrate_seed_size': float,
        'wire_seed_size': float,
        'substrate_edge_seed_size': float,
        'n_rows': int,
        'depth': float,
        'w': float,
        'l_1': float,
        'l_2': float,
        'm': int,
        'u1': float,
        'u2': float,
        'enable_restart': bool,
        'global_output': bool,
        'USE_STANDARD_CIRCLES': bool
    }

    # 分割模型名称
    parts = model_name.split('_')

    if not parts:
        raise ValueError(f"无效的模型名称格式: {model_name}")

    # 解析结果字典
    parsed_params = {}

    # 解析分布类型前缀
    prefix = parts[0].lower()
    if prefix == 'std':
        parsed_params['USE_STANDARD_CIRCLES'] = True
    elif prefix == 'uni':
        parsed_params['USE_STANDARD_CIRCLES'] = False
    else:
        raise ValueError(f"未知的分布类型前缀: {prefix}")

    # 解析参数部分
    for part in parts[1:]:
        # 寻找参数简写和值的分界点
        param_found = False

        # 按照简写长度从长到短匹配，避免短简写被误匹配
        for abbrev in sorted(abbreviation_to_param.keys(), key=len, reverse=True):
            if part.startswith(abbrev):
                param_name = abbreviation_to_param[abbrev]
                value_str = part[len(abbrev):]

                if not value_str:
                    continue  # 如果没有值部分，继续尝试其他简写

                try:
                    # 根据参数类型转换值
                    param_type = param_types.get(param_name, str)

                    if param_type == bool:
                        # 布尔类型特殊处理
                        parsed_value = value_str.lower() in ('true', '1', 'yes', 'on')
                    elif param_type in (int, float):
                        # 数值类型
                        parsed_value = param_type(str_to_std(value_str))
                    else:
                        # 字符串类型
                        parsed_value = value_str

                    parsed_params[param_name] = parsed_value
                    param_found = True
                    break

                except (ValueError, TypeError) as e:
                    # 如果转换失败，继续尝试其他简写
                    continue

        if not param_found:
            print(f"警告: 无法解析模型名称部分: {part}")

    return parsed_params


def validate_parsed_params(parsed_params, original_name):
    """
    验证解析出的参数是否合理

    Args:
        parsed_params (dict): 解析出的参数字典
        original_name (str): 原始模型名称

    Returns:
        bool: 验证是否通过
        list: 警告信息列表
    """
    warnings = []

    # 检查必需的参数
    required_params = ['USE_STANDARD_CIRCLES']
    for param in required_params:
        if param not in parsed_params:
            warnings.append(f"缺少必需参数: {param}")

    # 检查参数值的合理性
    if 'porosity' in parsed_params:
        porosity = parsed_params['porosity']
        if not (0 < porosity <= 0.7854):
            warnings.append(f"孔隙率值不合理: {porosity} (应在 0-0.7854 范围内)")

    if 'n_rows' in parsed_params:
        n_rows = parsed_params['n_rows']
        if not isinstance(n_rows, int) or n_rows <= 0:
            warnings.append(f"行数值不合理: {n_rows} (应为正整数)")

    if 'random_seed' in parsed_params:
        seed = parsed_params['random_seed']
        if not isinstance(seed, int) or seed < 0:
            warnings.append(f"随机种子值不合理: {seed} (应为非负整数)")

    # 检查重新生成的名称是否一致（简单验证）
    if len(parsed_params) > 1:  # 如果有足够的参数
        try:
            # 这里可以添加重新生成名称并比较的逻辑
            pass
        except Exception as e:
            warnings.append(f"参数一致性检查失败: {str(e)}")

    return len(warnings) == 0, warnings


# 测试和调试函数
def test_model_name_functions():
    """
    测试模型名称生成和解析功能
    """
    print("=" * 60)
    print("测试模型名称格式化和解析功能")
    print("=" * 60)

    # 测试用例
    test_cases = [
        {
            'USE_STANDARD_CIRCLES': True,
            'porosity': 0.3,
            'T_delta': 0.05,
            'random_seed': 1
        },
        {
            'USE_STANDARD_CIRCLES': False,
            'porosity': 0.5,
            'T_xi': 0.02,
            'T_delta': 0.1,
            'random_seed': 2,
            'n_rows': 16
        },
        {
            'USE_STANDARD_CIRCLES': True,
            'substrate_seed_size': 0.009,
            'enable_restart': True
        }
    ]

    for i, test_config in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}:")
        print(f"原始配置: {test_config}")

        # 生成模型名称
        model_name = encode_filename(test_config, [test_config])
        print(f"生成的模型名称: {model_name}")

        # 解析模型名称
        parsed = decode_filename(model_name)
        print(f"解析结果: {parsed}")

        # 验证解析结果
        is_valid, warnings = validate_parsed_params(parsed, model_name)
        if is_valid:
            print("验证通过")
        else:
            print(f"验证警告: {warnings}")

        # 检查关键参数是否一致
        key_matches = []
        for key in ['USE_STANDARD_CIRCLES', 'porosity', 'random_seed']:
            if key in test_config and key in parsed:
                match = test_config[key] == parsed[key]
                key_matches.append(f"{key}: {match}")

        if key_matches:
            print(f"关键参数匹配: {', '.join(key_matches)}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_model_name_functions()
