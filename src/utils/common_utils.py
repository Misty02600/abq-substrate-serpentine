import sys
import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from datetime import datetime
import uuid


# =============================================================================
# 通用工具函数
# =============================================================================

def setup_python_path():
    """
    设置Python路径以便导入模块，专为ABAQUS环境优化

    ABAQUS环境特点：
    - noGUI模式：__file__ 总是可用
    - GUI Run Script模式：__file__ 不可用，需要特殊处理
    """
    import inspect
    import os

    # 脚本所在目录：noGUI 里 __file__ 一定有；Run Script 时看 ② 退路
    try:                                    # ① 绝大多数情况下
        SCRIPT_DIR = Path(__file__).parent.resolve()
    except NameError:                       # ② 只有 GUI ▸ Run Script 才会进这里
        fname = inspect.getfile(inspect.currentframe())
        SCRIPT_DIR = Path(fname).parent.resolve() if not fname.startswith('<')\
                     else Path(os.getcwd()).resolve()

    # 添加到系统路径
    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))


def select_files(title="选择文件", filetypes=None, multiple=True, initialdir=None):
    """
    通用文件选择对话框

    Args:
        title (str): 对话框标题
        filetypes (list): 文件类型过滤器，格式为 [("描述", "*.ext"), ...]
        multiple (bool): 是否允许多选
        initialdir (str): 初始目录

    Returns:
        list or str: 如果multiple=True返回文件路径列表，否则返回单个文件路径
    """
    # 创建隐藏的根窗口
    root = tk.Tk()
    root.withdraw()

    # 设置默认文件类型
    if filetypes is None:
        filetypes = [("所有文件", "*.*")]

    # 设置初始目录
    if initialdir is None:
        initialdir = str(Path.cwd())

    try:
        if multiple:
            # 多文件选择
            files = filedialog.askopenfilenames(
                title=title,
                initialdir=initialdir,
                filetypes=filetypes
            )
            result = list(files) if files else []
        else:
            # 单文件选择
            file = filedialog.askopenfilename(
                title=title,
                initialdir=initialdir,
                filetypes=filetypes
            )
            result = file if file else None
    finally:
        # 销毁根窗口
        root.destroy()

    return result


def save_to_json(data, filename, indent=2):
    """
    将数据保存为JSON文件

    Args:
        data: 要保存的数据
        filename (str): 输出文件名（包含扩展名）
        indent (int): JSON缩进空格数

    Returns:
        str: 保存的文件路径，如果保存失败返回None
    """
    output_path = Path(filename)

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)

        print(f"数据已保存到: {output_path.absolute()}")
        return str(output_path.absolute())

    except Exception as e:
        print(f"保存文件时发生错误: {str(e)}")
        return None


def load_from_json(file_path):
    """
    从JSON文件加载数据

    Args:
        file_path (str): JSON文件路径

    Returns:
        dict: 加载的数据，如果加载失败返回None
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载JSON文件失败: {str(e)}")
        return None


def get_timestamp(format_str="%Y%m%d_%H%M%S"):
    """
    获取当前时间戳字符串

    Args:
        format_str (str): 时间格式字符串

    Returns:
        str: 格式化的时间戳
    """
    return datetime.now().strftime(format_str)


def generate_unique_id():
    """
    生成唯一标识符

    Returns:
        str: 包含时间戳和UUID前8位的唯一ID
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    uuid_part = str(uuid.uuid4())[:8]
    return f"{timestamp}_{uuid_part}"



