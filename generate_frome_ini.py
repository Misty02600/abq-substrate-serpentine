import os
import sys
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

from src.config.process_config import process_config_v1, process_config_v2, process_config_v3
from src.model.assembly import create_porous_model
from extract_configs_to_json import extract_and_process_configs


def generate_porous_models(config_list, max_models=None):
    """
    多孔基底模型生成函数

    Args:
        config_list (list): 已处理的配置字典列表，每个字典包含创建一个模型所需的所有参数
        max_models (int, optional): 最大模型数量限制

    Returns:
        list: 配置字典列表（原样返回，用于JSON记录）
    """
    total_configs = len(config_list)

    # 检查是否超过限制
    if max_models and total_configs > max_models:
        print(f"警告: 配置生成了 {total_configs} 个模型组合，超过限制 {max_models}，取消模型创建")
        return config_list

    # 获取现有的模型名称
    existing_models = set(mdb.models.keys())

    # 直接创建模型
    created_count = 0
    skipped_count = 0

    for i, config_params in enumerate(config_list, 1):
        model_name = config_params['modelname']

        print(f"\n[{i}/{total_configs}] 处理配置: {model_name}")

        if model_name in existing_models:
            print(f"跳过已存在的模型: {model_name}")
            skipped_count += 1
        else:
            # 直接创建模型
            create_porous_model(**config_params)
            created_count += 1
            print(f"模型 {model_name} 创建成功")

    print(f"\n处理完成！跳过 {skipped_count} 个已存在的模型，成功创建 {created_count} 个新模型")

    return config_list


def create_models_from_config_file(config_processor=process_config_v1, max_models=None):
    """
    从配置文件批量创建多孔基底模型（便捷函数）
    同时生成配置组合的JSON文件

    Args:
        config_processor (Callable, optional): 配置处理函数，默认使用 process_config_v1
        max_models (int, optional): 最大模型数量限制
    """
    print("批量创建模型工具")

    # 一次性提取和处理所有配置文件，同时保存JSON（函数内部会选择文件）
    all_processed_configs = extract_and_process_configs(
        config_files=None,  # 函数内部选择文件
        config_processor=config_processor,
        save_json=True
    )

    # 直接使用处理好的配置生成模型
    if all_processed_configs:
        print(f"\n开始创建模型...")
        final_configs = generate_porous_models(all_processed_configs, max_models)
        print(f"模型创建完成，处理了 {len(final_configs)} 个配置")
    else:
        print("没有找到有效的配置，跳过模型创建")

    print(f"\n批量处理完成！")


if __name__ == "__main__":
    create_models_from_config_file(max_models=200, config_processor=process_config_v3)