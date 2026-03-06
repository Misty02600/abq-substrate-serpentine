import json
from pathlib import Path

from abaqus import *

from abq_serp_sub.processes.assembly import create_model_from_dict
from abq_serp_sub.utils.common_utils import select_files


def load_configs_from_json(json_file_path):
    """
    从JSON文件中加载配置

    支持两种格式:
    1. 单个配置对象: {"substrate": {...}, "wire": {...}, ...}
    2. 多配置列表: {"metadata": {...}, "configurations": [{...}, {...}]}

    Args:
        json_file_path (str): JSON文件路径

    Returns:
        tuple: (metadata, configurations) 元数据和配置列表
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        # 检测格式：如果有 'configurations' 键，使用旧格式
        if 'configurations' in json_data:
            metadata = json_data.get('metadata', {})
            configurations = json_data.get('configurations', [])
        else:
            # 新格式：单个配置对象
            metadata = {'source': Path(json_file_path).name}
            configurations = [json_data]

        print(f"成功加载JSON文件: {Path(json_file_path).name}")
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


def generate_models_from_json(json_file_path):
    """
    从JSON文件中的配置生成模型。
    每个配置独立处理，单个配置失败不会中断其余配置的创建。

    Args:
        json_file_path (str): JSON配置文件路径

    Returns:
        dict: 创建结果统计 {'total': int, 'created': int, 'failed': list}
    """
    # 加载配置
    metadata, configurations = load_configs_from_json(json_file_path)

    if not configurations:
        print("没有找到有效的配置，退出")
        return {'total': 0, 'created': 0, 'failed': []}

    total_configs = len(configurations)
    print(f"发现 {total_configs} 个配置")

    # 统计变量
    created_count = 0
    failed_list = []  # 记录失败的配置 (索引, 名称, 错误信息)

    print(f"开始创建模型...")

    for i, config_params in enumerate(configurations, 1):
        model_name = config_params.get('modelname', f'Model_{i}')

        print(f"[{i}/{total_configs}] 创建: {model_name}")

        try:
            create_model_from_dict(config_params)
            created_count += 1
        except Exception as e:
            error_msg = str(e)
            failed_list.append((i, model_name, error_msg))
            print(f"  ✗ 创建失败: {error_msg}")
            print(f"  跳过此配置，继续处理下一个...")

    # 打印结果总结
    print(f"\n{'='*50}")
    print(f"创建完成: 成功 {created_count}/{total_configs}")
    if failed_list:
        print(f"失败 {len(failed_list)} 个:")
        for idx, name, err in failed_list:
            print(f"  [{idx}] {name}: {err}")
    print(f"{'='*50}")

    return {
        'total': total_configs,
        'created': created_count,
        'failed': failed_list,
    }


def generate_models_from_multiple_json(json_files):
    """
    从多个JSON文件中的配置生成模型

    Args:
        json_files (list): JSON文件路径列表

    Returns:
        dict: 创建结果统计
    """
    print(f"处理 {len(json_files)} 个JSON文件")

    total_created = 0
    total_configs = 0
    all_failed = []

    for i, json_file in enumerate(json_files, 1):
        print(f"\n[{i}/{len(json_files)}] 处理文件: {Path(json_file).name}")

        result = generate_models_from_json(json_file)

        total_created += result['created']
        total_configs += result['total']
        all_failed.extend(result['failed'])

    # 最终总结
    print(f"\n{'='*50}")
    print(f"多文件处理完成: 总配置 {total_configs}, 成功创建 {total_created}")
    if all_failed:
        print(f"共 {len(all_failed)} 个配置创建失败:")
        for idx, name, err in all_failed:
            print(f"  [{idx}] {name}: {err}")
    print(f"{'='*50}")

    return {
        'total': total_configs,
        'created': total_created,
        'failed': all_failed,
    }


def generate_models_from_json_interactive():
    """
    交互式从JSON文件生成模型（会打开文件选择对话框，支持多选）
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
    result = generate_models_from_multiple_json(json_files)

    if result['created'] > 0:
        print(f"\n总共成功创建 {result['created']} 个模型")
    else:
        print("\n未创建任何模型")


if __name__ == "__main__":
    print("JSON配置文件模型生成器")

    # 可以直接指定JSON文件路径
    # json_file_path = "configs_20241227_123456.json"
    # result = generate_models_from_json(json_file_path)

    # 或者使用交互式选择
    generate_models_from_json_interactive()