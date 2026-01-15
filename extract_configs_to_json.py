import sys
from pathlib import Path
import inspect
import os

try:
    SCRIPT_DIR = Path(__file__).parent.resolve()
except NameError:
    fname = inspect.getfile(inspect.currentframe())
    SCRIPT_DIR = Path(fname).parent.resolve() if not fname.startswith('<') else Path(os.getcwd()).resolve()
sys.path.append(str(SCRIPT_DIR))

from src.config.process_config import process_config_v3
from src.utils.common_utils import select_files, save_to_json, get_timestamp, generate_unique_id
from src.config.parse_config import load_config


def extract_and_process_configs(config_files=None, config_processor=None, save_json=True):
    """
    从INI配置文件中提取、处理配置，并可选择保存为JSON文件

    Args:
        config_files (list, optional): 配置文件路径列表，如果为None则打开文件选择对话框
        config_processor (Callable, optional): 配置后处理函数
        save_json (bool): 是否保存JSON文件，默认为True

    Returns:
        list: 处理好的配置字典列表，可直接用于模型生成
    """
    # 如果没有指定配置文件，则选择文件
    if config_files is None:
        print("请选择要处理的配置文件...")
        config_files = select_files(
            title="选择配置文件（可多选）",
            filetypes=[
                ("INI配置文件", "*.ini"),
                ("所有文件", "*.*")
            ],
            multiple=True
        )

        if not config_files:
            print("未选择配置文件，操作取消")
            return []

    print("开始提取和处理配置文件")

    all_processed_configs = []

    # 处理每个INI配置文件
    for i, config_file in enumerate(config_files, 1):
        config_path = Path(config_file)
        print(f"\n[{i}/{len(config_files)}] 处理配置文件: {config_path.name}")

        try:
            # 加载配置（包含后处理）
            config_list = load_config(config_file, config_processor)
            print(f"  找到 {len(config_list)} 个配置组合")

            # 添加所有配置到总列表
            all_processed_configs.extend(config_list)

        except Exception as e:
            print(f"  错误: 处理文件 {config_path.name} 时发生错误: {str(e)}")

    print(f"\n总共处理了 {len(all_processed_configs)} 个配置组合")

    # 可选择保存JSON文件
    if save_json:
        # 生成唯一ID和文件名
        unique_id = generate_unique_id()
        json_filename = f"configs_{unique_id}.json"

        # 创建JSON数据结构
        metadata = {
            'id': unique_id,
            'total_configs': len(all_processed_configs),
            'created_date': get_timestamp("%Y-%m-%d %H:%M:%S")
        }

        json_data = {
            'metadata': metadata,
            'configurations': all_processed_configs
        }

        # 保存JSON文件
        json_path = save_to_json(json_data, json_filename)

        if json_path:
            print(f"配置JSON文件已保存: {json_path}")
            print(f"唯一ID: {unique_id}")
        else:
            print("保存JSON文件时出错")

    return all_processed_configs


if __name__ == "__main__":
    print("配置文件解析和导出工具")

    # 提取和处理配置（不使用后处理，直接保存JSON）
    processed_configs = extract_and_process_configs(
        config_files=None,
        config_processor=process_config_v3,
        save_json=True
    )

    if processed_configs:
        print(f"\n处理完成！包含 {len(processed_configs)} 个配置组合")
    else:
        print("未找到有效配置或处理失败")