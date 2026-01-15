# coding: utf-8
import os
import sys
import inspect
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

import pandas as pd
from abaqus import session

try:
    SCRIPT_DIR = Path(__file__).parent.resolve()
except NameError:
    fname = inspect.getfile(inspect.currentframe())
    SCRIPT_DIR = Path(fname).parent.resolve() if not fname.startswith('<') else Path(os.getcwd()).resolve()
sys.path.append(str(SCRIPT_DIR))

from extract_strechability import get_overall_critical_summary


def run_main_for_all_odb(step_index: int = 1, node_set_name: str = "SUBSTRATE-1.TPC_A"):
    if not session.odbs:
        print("错误：当前会话中没有打开的ODB文件。请先打开至少一个ODB文件。")
        return

    root = tk.Tk()
    root.withdraw()
    csv_path_str = filedialog.askopenfilename(
        title="选择要追加数据的CSV文件（如不存在请取消后重新运行选择保存位置）",
        filetypes=[("CSV 文件", "*.csv"), ("所有文件", "*.*")]
    )
    if not csv_path_str:
        print("操作已取消：未选择任何文件。")
        return

    csv_path = Path(csv_path_str) # 转换为Path对象，便于操作

    all_results = []
    total_odbs = len(session.odbs)
    print(f"检测到 {total_odbs} 个ODB文件，将使用以下参数进行分析:")
    print(f"  step_index = {step_index}")
    print(f"  node_set_name = '{node_set_name}'")

    for i, odb in enumerate(session.odbs.values(), 1):
        print(f"\n--- [{i}/{total_odbs}] 正在处理 ODB: {odb.name} ---")
        vp = session.viewports[session.currentViewportName]
        vp.setValues(displayedObject=odb)

        try:
            result_dict = get_overall_critical_summary(odb=odb, step_index=step_index, node_set_name=node_set_name)
            # 直接添加原始嵌套字典，pandas会自动处理
            all_results.append(result_dict)
            print(f"成功处理: {odb.name}")
        except Exception as e:
            print(f"!!!!!! 处理 '{odb.name}' 时发生错误: {e}")
            continue

    if not all_results:
        print("\n没有可供写入的分析结果。")
        return

    # 使用pandas处理数据并保存到CSV
    print(f"\n所有ODB处理完毕，准备将 {len(all_results)} 条结果追加到CSV文件...")

    # 使用pandas的json_normalize自动展开嵌套字典，使用下划线作为分隔符
    df_new = pd.json_normalize(all_results, sep='_')

    # 检查文件是否存在且有有效数据
    df_existing = None
    if csv_path.is_file() and csv_path.stat().st_size > 0:
        try:
            df_existing = pd.read_csv(csv_path, encoding='utf-8')
            if df_existing.empty:
                df_existing = None
        except (pd.errors.EmptyDataError, Exception) as e:
            print(f"读取现有文件时出错: {e}，将直接写入新数据")
            df_existing = None

    # 根据是否有现有数据决定操作
    if df_existing is not None:
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        print(f"文件已存在，将追加 {len(df_new)} 行数据到现有的 {len(df_existing)} 行数据后")
    else:
        df_combined = df_new
        if csv_path.is_file():
            print("文件存在但为空或无有效数据，将直接写入新数据")
        else:
            print(f"文件不存在，将创建新文件并写入 {len(df_new)} 行数据")

    # 保存到CSV
    df_combined.to_csv(csv_path, index=False, encoding='utf-8')

    print(f"\n成功！结果已全部保存到以下文件:")
    print(csv_path.resolve())
    print(f"总共包含 {len(df_combined)} 行数据，{len(df_combined.columns)} 列")


if __name__ == "__main__":
    run_main_for_all_odb(step_index=1)