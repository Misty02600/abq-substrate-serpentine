import os
import sys
import json
from pathlib import Path
import inspect

from abaqus import *

# 脚本所在目录：noGUI 里 __file__ 一定有；Run Script 时看 ② 退路
try:                                    # ① 绝大多数情况下
    SCRIPT_DIR = Path(__file__).parent.resolve()
except NameError:                       # ② 只有 GUI ▸ Run Script 才会进这里
    import os
    fname = inspect.getfile(inspect.currentframe())
    SCRIPT_DIR = Path(fname).parent.resolve() if not fname.startswith('<')\
                 else Path(os.getcwd()).resolve()

# 把脚本目录放到 import 搜索路径最前
sys.path.append(str(SCRIPT_DIR))

from src.model.assembly import create_porous_model
from src.utils.common_utils import select_files


def load_configs_from_json(json_file_path):
    """
    从JSON文件中加载配置

    Args:
        json_file_path (str): JSON文件路径

    Returns:
        tuple: (metadata, configurations) 元数据和配置列表
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        metadata = json_data.get('metadata', {})
        configurations = json_data.get('configurations', [])

        # 将origin从列表转换为元组（JSON不支持元组，只能存储为列表）
        for config in configurations:
            if 'origin' in config and isinstance(config['origin'], list):
                config['origin'] = tuple(config['origin'])

        print(f"成功加载JSON文件: {Path(json_file_path).name}")
        print(f"文件ID: {metadata.get('id', 'N/A')}")
        print(f"创建日期: {metadata.get('created_date', 'N/A')}")
        print(f"配置数量: {len(configurations)}")

        return metadata, configurations

    except FileNotFoundError:
        print(f"错误: 找不到文件 {json_file_path}")
        return None, []
    except json.JSONDecodeError as e:
        print(f"错误: JSON文件格式错误 - {str(e)}")
        return None, []
    except Exception as e:
        print(f"错误: 加载JSON文件时发生未知错误 - {str(e)}")
        return None, []


def generate_models_from_json(json_file_path, max_models=None):
    """
    从JSON文件中的配置生成模型

    Args:
        json_file_path (str): JSON配置文件路径
        max_models (int, optional): 最大模型数量限制

    Returns:
        dict: 创建结果统计
    """
    # 加载配置
    metadata, configurations = load_configs_from_json(json_file_path)

    if not configurations:
        print("没有找到有效的配置，退出")
        return {'total': 0, 'created': 0}

    total_configs = len(configurations)
    print(f"发现 {total_configs} 个配置")

    # 检查是否超过限制
    if max_models and total_configs > max_models:
        print(f"错误: 配置包含 {total_configs} 个模型，超过限制 {max_models}，操作终止")
        return {'total': total_configs, 'created': 0}

    # 统计变量
    created_count = 0

    print(f"开始创建模型...")

    for i, config_params in enumerate(configurations, 1):
        model_name = config_params.get('modelname', f'Model_{i}')

        print(f"[{i}/{total_configs}] 创建: {model_name}")

        # 创建模型
        create_porous_model(**config_params)
        created_count += 1

    # 打印结果统计
    print(f"\n创建完成: {created_count}/{total_configs}")

    return {
        'total': total_configs,
        'created': created_count
    }


def generate_models_from_multiple_json(json_files, max_models=None):
    """
    从多个JSON文件中的配置生成模型

    Args:
        json_files (list): JSON文件路径列表
        max_models (int, optional): 最大模型数量限制

    Returns:
        dict: 创建结果统计
    """
    print(f"处理 {len(json_files)} 个JSON文件")

    total_created = 0
    total_configs = 0

    for i, json_file in enumerate(json_files, 1):
        print(f"\n[{i}/{len(json_files)}] 处理文件: {Path(json_file).name}")

        result = generate_models_from_json(json_file, max_models=max_models)

        total_created += result['created']
        total_configs += result['total']

        # 如果有最大限制且已达到，停止处理后续文件
        if max_models and total_created >= max_models:
            print(f"已达到最大模型数量限制 {max_models}，停止处理后续文件")
            break

    print(f"\n多文件处理完成: 总配置 {total_configs}, 成功创建 {total_created}")

    return {
        'total': total_configs,
        'created': total_created
    }


def generate_models_from_json_interactive(max_models=None):
    """
    交互式从JSON文件生成模型（会打开文件选择对话框，支持多选）

    Args:
        max_models (int, optional): 最大模型数量限制
    """
    print("从JSON配置文件生成模型")
    print("请选择JSON配置文件（可多选）...")

    # 选择JSON文件（支持多选）
    json_files = select_files(
        title="选择JSON配置文件（可多选）",
        filetypes=[
            ("JSON文件", "*.json"),
            ("所有文件", "*.*")
        ],
        multiple=True
    )

    if not json_files:
        print("未选择文件，操作取消")
        return

    # 处理多个文件
    result = generate_models_from_multiple_json(json_files, max_models=max_models)

    if result['created'] > 0:
        print(f"\n总共成功创建 {result['created']} 个模型")
    else:
        print("\n未创建任何模型")


if __name__ == "__main__":
    print("JSON配置文件模型生成器")

    # 可以直接指定JSON文件路径
    # json_file_path = "configs_20241227_123456.json"
    # result = generate_models_from_json(json_file_path, max_models=10)

    # 或者使用交互式选择
    generate_models_from_json_interactive(max_models=300)