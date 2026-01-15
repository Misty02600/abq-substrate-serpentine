import inspect
import sys
from pathlib import Path

from abaqus import *
from abaqusConstants import *
import numpy as np

# 脚本所在目录：noGUI 里 __file__ 一定有；Run Script 时看 ② 退路
try:  # ① 绝大多数情况下
    SCRIPT_DIR = Path(__file__).parent.resolve()
except NameError:  # ② 只有 GUI ▸ Run Script 才会进这里
    import os
    fname = inspect.getfile(inspect.currentframe())
    SCRIPT_DIR = (
        Path(fname).parent.resolve()
        if not fname.startswith("<")
        else Path(os.getcwd()).resolve()
    )

# 把脚本目录放到 import 搜索路径最前
sys.path.append(str(SCRIPT_DIR))

from src.utils.post_utils import sort_nodes_along_line


def extract_wire_displacement(step=0, frame=None, variable_name='U1'):
    """
    从当前视口的 ODB 中提取 Wire-1 部件 Top-1-1, Top-1-2, Top-1-3 节点集的位移数据。

    Args:
        step (int): 分析步索引，默认为 0（第一个分析步）
        frame (int or None): 帧索引，默认为 None（使用当前步的最后一帧）

    Returns:
        XYData: 提取的位移数据对象
    """
    # 获取当前视口和 ODB
    vp = session.viewports[session.currentViewportName]
    odb = vp.displayedObject

    # 确定提取变量类型 (位移或转角)
    field_type = 'UR' if variable_name.startswith('UR') else 'U'

    if not hasattr(odb, 'rootAssembly'):
        print("错误: 当前视口未显示有效的 ODB 文件！")
        return None

    # 确定要使用的帧
    step_obj = odb.steps[odb.steps.keys()[step]]
    if frame is None:
        # 使用当前步的最后一帧
        frame = len(step_obj.frames) - 1

    # 获取 Wire-1 实例
    try:
        wire_instance = odb.rootAssembly.instances["WIRE-1"]
    except KeyError:
        print("错误: 未找到 WIRE-1 实例！")
        return None

    wire_node_sets = wire_instance.nodeSets

    # 获取三个节点集
    top_1_1 = wire_node_sets["TOP-1-1"]
    top_1_2 = wire_node_sets["TOP-1-2"]
    top_1_3 = wire_node_sets["TOP-1-3"]

    print("开始对节点进行排序...")

    # 使用 sort_nodes_along_line 函数对节点进行排序
    sorted_nodes = sort_nodes_along_line(top_1_1, top_1_2, top_1_3)

    # 提取排序后的节点标签
    combined_nodes = tuple(node.label for node in sorted_nodes)

    # 创建 Path
    path_name = "Wire_Top_Path"
    try:
        pth = session.Path(
            name=path_name,
            type=NODE_LIST,
            expression=(("WIRE-1", combined_nodes),)
        )
        print("Path '{}' 创建成功".format(path_name))
    except Exception as e:
        print("创建 Path 时发生错误: {}".format(e))
        return None

    # 使用 Path 提取位移数据
    xy_data_name = "Wire_Data"

    xy_data = session.XYDataFromPath(
        name=xy_data_name,
        path=pth,
        includeIntersections=False,
        projectOntoMesh=False,
        pathStyle=PATH_POINTS,
        shape=UNDEFORMED,
        labelType=TRUE_DISTANCE,
        removeDuplicateXYPairs=True,
        includeAllElements=False,
        step=step,
        frame=frame,
        variable=((field_type, NODAL, ((COMPONENT, variable_name),)),)
    )
    print("位移数据提取成功: '{}'".format(xy_data_name))

    # 输出数据点数量
    print("提取了 {} 个数据点".format(len(xy_data.data)))

    return xy_data


if __name__ == "__main__":
    xy_data = extract_wire_displacement(variable_name='U1')
