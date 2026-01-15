import os
import sys
from pathlib import Path
import inspect

from abaqus import *
from abaqusConstants import *

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

from src.config.process_config import process_config_v1, process_config_v3
from common_scripts.inp_writer import write_all_jobs_to_inp


def main(config_processor=process_config_v1):
    """主函数：批量创建模型、写入inp文件、保存cae文件"""

    # 指定配置文件路径（从当前工作目录读取所有ini文件）
    current_dir = Path.cwd()
    config_files = [str(f) for f in current_dir.glob("*.ini")]

    print("开始批量处理流程...")
    print(f"配置文件: {[Path(f).name for f in config_files]}")

    # 检查配置文件是否存在
    for config_file in config_files:
        if not Path(config_file).exists():
            print(f"错误: 配置文件 {config_file} 不存在")
            return

    # 第一步：创建模型
    print("\n=== 步骤1: 创建模型 ===")
    # 使用extract_and_process_configs处理预定义的配置文件
    from extract_configs_to_json import extract_and_process_configs
    from generate_frome_ini import generate_porous_models

    all_processed_configs = extract_and_process_configs(
        config_files=config_files,
        config_processor=config_processor,
        save_json=True
    )

    # 直接生成模型
    if all_processed_configs:
        generate_porous_models(all_processed_configs, max_models=200)

    # 检查是否有任何模型被创建（通过检查mdb中的模型数量）
    if not mdb.models or len(mdb.models) <= 1:
        print("没有创建任何模型，流程终止")
        return

    model_count = len([name for name in mdb.models.keys() if name != 'Model-1'])
    print(f"成功创建了 {model_count} 个模型")

    # 第二步：运行inp写入器
    print("\n=== 步骤2: 运行inp写入器 ===")
    write_all_jobs_to_inp()

    # 第三步：保存cae文件
    print("\n=== 步骤3: 保存cae文件 ===")
    cae_filename = str(Path.cwd() / "1.cae")

    mdb.saveAs(pathName=cae_filename)
    print(f"cae文件已保存为: {cae_filename}")


    print("\n=== 批量处理流程完成 ===")
    print(f"- 创建模型数量: {model_count}")
    print(f"- cae文件位置: {cae_filename}")
    print("- inp文件已生成在各模型对应的工作目录中")


if __name__ == "__main__":
    main(config_processor=process_config_v3)
