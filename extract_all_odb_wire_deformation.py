"""
批量提取所有已打开 ODB 文件的 Wire 位移数据并保存为 CSV 文件

此脚本会遍历所有打开的 ODB 文件，提取 Wire-1 部件的位移数据，
并将每个 ODB 的数据保存为单独的 CSV 文件。
"""

import inspect
import sys
from pathlib import Path
import os
import tkinter as tk
from tkinter import filedialog, messagebox

from abaqus import *
from abaqusConstants import *

# 脚本所在目录：noGUI 里 __file__ 一定有；Run Script 时看 ② 退路
try:  # ① 绝大多数情况下
    SCRIPT_DIR = Path(__file__).parent.resolve()
except NameError:  # ② 只有 GUI ▸ Run Script 才会进这里
    fname = inspect.getfile(inspect.currentframe())
    SCRIPT_DIR = (
        Path(fname).parent.resolve()
        if not fname.startswith("<")
        else Path(os.getcwd()).resolve()
    )

# 把脚本目录放到 import 搜索路径最前
sys.path.append(str(SCRIPT_DIR))

# 导入已有的提取函数
from extract_wire_deformation import extract_wire_displacement


def select_variable():
    """
    弹窗让用户选择要提取的变量

    Returns:
        str or None: 用户选择的变量名，如果取消则返回 None
    """
    root = tk.Tk()
    root.title("选择变量")
    root.geometry("250x250")
    root.resizable(False, False)

    # 居中显示窗口
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (250 // 2)
    y = (root.winfo_screenheight() // 2) - (250 // 2)
    root.geometry(f"250x250+{x}+{y}")

    selected_var = tk.StringVar()

    # 标题标签
    title_label = tk.Label(root, text="请选择要提取的变量:", font=("Arial", 11))
    title_label.pack(pady=10)

    # 变量选项
    variables = ['U1', 'U2', 'U3', 'UR1', 'UR2', 'UR3']

    # 创建单选按钮
    for var in variables:
        rb = tk.Radiobutton(root, text=var, variable=selected_var, value=var,
                           font=("Arial", 10))
        rb.pack(anchor='w', padx=30, pady=2)

    # 设置默认选择
    selected_var.set('U1')

    result = [None]  # 使用列表来存储结果

    def on_confirm():
        result[0] = selected_var.get()
        root.destroy()

    def on_cancel():
        result[0] = None
        root.destroy()

    # 绑定回车键确认
    root.bind('<Return>', lambda event: on_confirm())
    root.bind('<KP_Enter>', lambda event: on_confirm())

    # 绑定ESC键取消
    root.bind('<Escape>', lambda event: on_cancel())

    # 运行对话框
    root.mainloop()

    return result[0]


def extract_all_odb_wire_displacement(step=1, frame=None, variable_name=None):
    """
    批量提取所有已打开 ODB 的 Wire 位移数据并保存为 CSV 文件

    Args:
        step (int): 分析步索引，默认为 1（第二个分析步 Step-2）
        frame (int or None): 帧索引，默认为 None（使用当前步的最后一帧）
        variable_name (str or None): 要提取的变量名，如 'U1', 'U2', 'U3', 'UR1' 等。
                                   如果为 None，将弹窗让用户选择
    """
    # 如果 variable_name 为 None，弹窗让用户选择
    if variable_name is None:
        variable_name = select_variable()
        if variable_name is None:
            print("操作已取消: 未选择变量。")
            return

    # 检查是否有打开的 ODB
    if not session.odbs:
        print("错误: 当前会话中没有打开的 ODB 文件！")
        print("请先打开至少一个 ODB 文件。")
        return

    # 使用 tkinter 选择保存文件夹
    save_dir = filedialog.askdirectory(
        title="选择 CSV 文件保存文件夹",
        initialdir=os.getcwd()
    )

    if not save_dir:
        print("操作已取消: 未选择保存文件夹。")
        return

    save_dir_path = Path(save_dir)
    print(f"CSV 文件将保存到: {save_dir_path}")

    # 统计信息
    total_odbs = len(session.odbs)

    print("批量提取 Wire 位移数据")
    print(f"参数设置: step={step}, frame={frame if frame is not None else 'last'}, variable={variable_name}")


    # 遍历所有 ODB
    for idx, (odb_key, odb) in enumerate(session.odbs.items(), 1):
        odb_name = Path(odb.name).stem
        print(f"[{idx}/{total_odbs}] 正在处理 ODB: {odb_name}")
        print(f"  完整路径: {odb.name}")

        # 设置当前视口显示此 ODB
        vp = session.viewports[session.currentViewportName]
        vp.setValues(displayedObject=odb)


        # 使用已有的提取函数
        xy_data = extract_wire_displacement(
            step=step,
            frame=frame,
            variable_name=variable_name
        )

        if xy_data is None:
            print(f"失败: 无法提取数据")
            continue

        # 保存为 CSV 文件
        csv_filename = f"{odb_name}_{variable_name}.csv"
        csv_path = save_dir_path / csv_filename

        session.writeXYReport(
            fileName=str(csv_path),
            xyData=(xy_data,),
            appendMode=OFF
        )

        print(f"成功保存到: {csv_filename}")


        print()

    # 打印总结
    print("=" * 70)
    print("处理完成！")
    print(f"保存位置: {save_dir_path}")
    print("=" * 70)


if __name__ == "__main__":
    extract_all_odb_wire_displacement(step=0, frame=None, variable_name=None)
