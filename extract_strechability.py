import inspect
import itertools
import os
import sys
from pathlib import Path
import pandas as pd

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
from src.postprocess.display_wire import display_wire_strain_contours


def get_node_displacement(
    odb, node_set_name, step_index, frame_index, component="U1"
):
    """
    使用 session.xyDataListFromField 提取指定节点集在指定步和帧的某一分量位移（如U1/U2/U3）。

    Args:
        odb: ODB对象。
        node_set_name (str): 节点集名称。
        step_index (int): 步骤索引（从0开始）。
        frame_index (int): 帧索引（从0开始）。
        component (str): 位移分量（'U1'、'U2'、'U3'），默认'U1'。

    Returns:
        float: 位移值，如无数据返回None。
    """
    # 获取step名称
    step_names = list(odb.steps.keys())
    step_name = step_names[step_index]

    active_frames = ((step_name, (frame_index,)),)

    # 获取ODB名称并设置activeFrames
    odb_name = odb.name
    session.odbData[odb_name].setValues(activeFrames=active_frames)

    # 提取指定分量的位移数据
    xydata_list = session.xyDataListFromField(
        odb=odb,
        outputPosition=NODAL,
        variable=(("U", NODAL, ((COMPONENT, component),)),),
        nodeSets=(node_set_name,),
    )

    # 只有一个节点集和一个分量，xydata_list只有一个XYData对象
    xy_data = xydata_list[0]

    # XYData.data是一个包含(time, value)元组的列表
    # 这里我们只需要位移值（第二个元素）
    return xy_data.data[0][1]


def create_wire_paths(odb):
    """
    从Wire-1部件的节点集创建Path对象。

    Args:
        odb: ODB对象。

    Returns:
        list: 创建的Path对象列表。
    """
    # 设置当前视口显示ODB
    vp = session.viewports[session.currentViewportName]
    vp.setValues(displayedObject=odb)
    wire_instance = odb.rootAssembly.instances["WIRE-1"]
    wire_node_sets = wire_instance.nodeSets

    last_segment_i = 0
    for i in itertools.count(1):
        if "TOP-{}-1".format(i) not in wire_node_sets:
            last_segment_i = i - 1
            break

    top_node_sets = [
        wire_node_sets[f"TOP-{i}-{j}"]
        for i in range(1, last_segment_i + 1)
        for j in range(1, 7)
        if f"TOP-{i}-{j}" in wire_node_sets
    ]

    top_sorted_nodes = sort_nodes_along_line(*top_node_sets)

    bottom_node_sets = [
        wire_node_sets[f"BOTTOM-{i}-{j}"]
        for i in range(1, last_segment_i + 1)
        for j in range(1, 7)
        if f"BOTTOM-{i}-{j}" in wire_node_sets
    ]

    bottom_sorted_nodes = sort_nodes_along_line(*bottom_node_sets)

    # 确保两者节点数量一致
    if len(top_sorted_nodes) != len(bottom_sorted_nodes):
        print(
            "错误: Top节点数({})与Bottom节点数({})不匹配！".format(
                len(top_sorted_nodes), len(bottom_sorted_nodes)
            )
        )
        return []

    # 创建Path
    created_paths = []
    total_nodes = len(top_sorted_nodes)
    for i in range(total_nodes):
        path_name = "Path-{}".format(i + 1)

        # 创建Path，连接对应的Top和Bottom节点
        top_node_label = top_sorted_nodes[i].label
        bottom_node_label = bottom_sorted_nodes[i].label
        combined_nodes = (top_node_label, bottom_node_label)

        path = session.Path(
            name=path_name,
            type=NODE_LIST,
            expression=(("WIRE-1", combined_nodes),),
        )
        created_paths.append(path)

    print("\n总共创建了 {} 个Path".format(total_nodes))
    return created_paths


def check_frame_strain(
    odb, paths, step_index, frame_index, strain_threshold=0.003, num_intervals=20
):
    """
    检查单个帧中指定Path列表的高应变区域占比，并判断是否有Path超过阈值。

    Args:
        odb: ODB对象（ABAQUS输出数据库）。
        paths (list): 要检查的Path对象列表。
        step_index (int): 步骤索引（从0开始）。
        frame_index (int): 帧索引（从0开始）。
        strain_threshold (float, optional): 应变阈值，默认0.003。
        num_intervals (int, optional): Path插值间隔数，默认20。

    Returns:
        tuple: (any_exceed, ratio, path_idx)
            any_exceed (bool): 是否有任何一个Path高应变区域占比超过50%。
            ratio (float): 若有超过则为首个超出Path的占比，否则为最大占比。
            path_idx (int): 对应Path编号（1-based）。
    """
    try:
        # 从ODB中获取指定步骤的名称
        step_name = list(odb.steps.keys())[step_index]

        # 验证帧索引是否在有效范围内
        if frame_index >= len(odb.steps[step_name].frames):
            print(f"错误: 帧索引 {frame_index} 超出范围。")
            return (False, 0.0, None)
    except IndexError:
        # 处理步骤索引越界的情况
        print(f"错误: 步骤索引 {step_index} 超出范围。")
        return (False, 0.0, None)

    # 初始化跟踪变量：最大应变占比和对应的路径索引
    max_ratio = 0.0
    max_idx = 0

    # 遍历指定的路径列表
    for i, path in enumerate(paths):
        xy_data_name = f"Data-frame{frame_index}-path{i}"

        # 从指定路径提取XY数据（应变值沿路径的分布）
        xy_data = session.XYDataFromPath(
            name=xy_data_name,  # 临时数据对象名称
            path=path,  # 要分析的路径
            includeIntersections=False,  # 不包含交点
            pathStyle=UNIFORM_SPACING,  # 均匀间距采样
            numIntervals=num_intervals,  # 插值间隔数
            shape=UNDEFORMED,  # 使用未变形几何
            labelType=SEQ_ID,  # 标签类型
            step=step_index,  # 分析步骤
            frame=frame_index,  # 分析帧
        )

        # 提取应变数据（每个数据点的y坐标为应变值）
        strains = np.array([point[1] for point in xy_data.data])
        n = len(strains)

        # 获取相邻点的应变值
        s1 = strains[:-1]  # 前一个点的应变
        s2 = strains[1:]  # 后一个点的应变

        # 识别完全在高应变区域内的路径段（两端点应变都超过阈值）
        mask_high = (s1 > strain_threshold) & (s2 > strain_threshold)
        high_strain_segments = np.sum(mask_high)

        # 识别跨越应变阈值的路径段（一端超过阈值，一端未超过）
        mask_cross = ((s1 > strain_threshold) & (s2 <= strain_threshold)) | (
            (s1 <= strain_threshold) & (s2 > strain_threshold)
        )
        cross_idx = np.where(mask_cross)[0]

        # 对于跨越阈值的路径段，计算高应变部分的段数贡献
        cross_segments_contribution = 0.0
        if cross_idx.size > 0:
            # 使用线性插值计算跨越点的位置比例
            frac = np.abs(s1[cross_idx] - strain_threshold) / np.abs(
                s1[cross_idx] - s2[cross_idx]
            )
            # 累加跨越段中高应变部分的贡献
            cross_segments_contribution = np.sum(
                np.where(
                    s1[cross_idx] > strain_threshold,  # 如果起点应变高
                    frac,  # 高应变部分占比
                    1.0 - frac,  # 高应变部分占比
                )
            )

        # 计算总段数和高应变区域占比
        total_segments = n - 1
        ratio = (
            high_strain_segments + cross_segments_contribution
        ) / total_segments

        del session.xyDataObjects[xy_data_name]

        # 检查是否超过50%阈值
        if ratio > 0.5:
            print(
                f"步骤'{step_name}' Frame {frame_index}: Path-{i+1} 高应变(>{strain_threshold:.3f})区域占比超过50% ({ratio*100:.3f}%)"
            )
            return True, ratio, i + 1  # 立即返回第一个超过阈值的路径

        # 更新最大占比记录
        if ratio > max_ratio:
            max_ratio = ratio
            max_idx = i + 1

    # 如果没有路径超过阈值，输出最大占比信息
    print(
        f"步骤'{step_name}' Frame {frame_index}: 所有Path均未超过阈值，最大占比为 Path-{max_idx}: {max_ratio*100:.3f}%"
    )

    return False, max_ratio, max_idx


def interpolate_disp_at_threshold(
    disp_before,
    disp_after,
    ratio_before,
    ratio_after,
    threshold=0.5,
):
    """
    基于给定的位移值和应变占比，插值估算恰好达到阈值时的位移量。

    Args:
        disp_before (float): 阈值前一帧的位移值
        disp_after (float): 超过阈值帧的位移值
        ratio_before (float): 阈值前一帧的应变占比
        ratio_after (float): 超过阈值帧的应变占比
        threshold (float, optional): 区域占比阈值，默认0.5

    Returns:
        float: 插值后的位移量，如果参数无效则返回None
    """
    # 参数有效性检查
    if None in (disp_before, disp_after, ratio_before, ratio_after):
        print("插值参数不完整，无法进行插值！")
        return None

    if ratio_after == ratio_before:
        return disp_before

    # 进行线性插值
    alpha = (threshold - ratio_before) / (ratio_after - ratio_before)
    interp_disp = (1 - alpha) * disp_before + alpha * disp_after

    return interp_disp


def get_face_critical_frame(
    odb, paths, face_name, step_index, strain_threshold, num_intervals, node_set_name="SUBSTRATE-1.TPC_A"
):
    """
    对单个面进行关键帧分析，包括二分搜索、位移提取和插值计算。

    Args:
        odb: ODB对象。
        paths (list): 要分析的Path对象列表。
        face_name (str): 面的名称（"TOP" 或 "BOTTOM"）。
        step_index (int): 步骤索引。
        strain_threshold (float): 应变阈值。
        num_intervals (int): Path插值间隔数。
        node_set_name (str): 节点集名称。

    Returns:
        dict: 包含该面完整分析结果的字典，包括：
            found (bool): True表示找到关键帧，False表示关键帧在范围外
            crit_frame (int): 关键帧号或边界帧号
            crit_ratio (float): 关键帧应变占比
            crit_path (int): 关键帧对应的Path编号
            prev_ratio (float): 上一帧应变占比（仅found=True时有效）
            prev_path (int): 上一帧Path编号（仅found=True时有效）
            disp_prev (float): 上一帧位移（仅found=True时有效）
            disp_crit (float): 关键帧位移
            interp_disp (float): 插值位移（仅found=True时有效）
    """
    display_wire_strain_contours(face_name)

    # 获取总帧数
    step = list(odb.steps.values())[step_index]
    total_frames = len(step.frames)

    # 创建缓存字典避免重复检查同一帧
    frame_cache = {}

    def cached_check(frame_idx):
        """带缓存的帧检查函数，避免重复计算"""
        if frame_idx not in frame_cache:
            exceed, ratio, path_idx = check_frame_strain(
                odb, paths, step_index, frame_idx, strain_threshold, num_intervals
            )
            frame_cache[frame_idx] = (exceed, ratio, path_idx)
        return frame_cache[frame_idx]

    # 第一次检查：起始帧是否已经超过阈值
    exceed_start, ratio_start, path_start = cached_check(0)
    if exceed_start:
        # 边界情况1：起始帧超过阈值，直接返回
        disp_crit = get_node_displacement(odb, node_set_name, step_index, 0, component="U1")
        return {
            "found": False,
            "crit_frame": 0,
            "crit_ratio": ratio_start,
            "crit_path": path_start,
            "prev_ratio": None,
            "prev_path": None,
            "disp_prev": None,
            "disp_crit": disp_crit,
            "interp_disp": None,
        }

    # 第二次检查：最后一帧是否超过阈值
    exceed_end, ratio_end, path_end = cached_check(total_frames - 1)
    if not exceed_end:
        # 边界情况2：整个步骤中均未找到，直接返回
        disp_crit = get_node_displacement(odb, node_set_name, step_index, total_frames - 1, component="U1")
        return {
            "found": False,
            "crit_frame": total_frames - 1,
            "crit_ratio": ratio_end,
            "crit_path": path_end,
            "prev_ratio": None,
            "prev_path": None,
            "disp_prev": None,
            "disp_crit": disp_crit,
            "interp_disp": None,
        }

    # 正常情况：起始帧未超过，结束帧超过，使用二分搜索找到首次超过阈值的帧
    left = 0
    right = total_frames - 1

    while left < right:
        mid = (left + right) // 2
        exceed, _, _ = cached_check(mid)
        if exceed:
            right = mid
        else:
            left = mid + 1

    # 第三次检查：获取关键帧和上一帧的详细信息
    critical_frame = left
    _, critical_ratio, critical_path = cached_check(critical_frame)
    _, prev_ratio, prev_path = cached_check(critical_frame - 1)

    # 两次位移提取：上一帧和关键帧
    prev_frame = critical_frame - 1
    disp_prev = get_node_displacement(odb, node_set_name, step_index, prev_frame, component="U1")
    disp_crit = get_node_displacement(odb, node_set_name, step_index, critical_frame, component="U1")

    # 插值计算
    interp_disp = interpolate_disp_at_threshold(
        disp_prev, disp_crit, prev_ratio, critical_ratio, threshold=0.5
    )

    return {
        "found": True,
        "crit_frame": critical_frame,
        "crit_ratio": critical_ratio,
        "crit_path": critical_path,
        "prev_ratio": prev_ratio,
        "prev_path": prev_path,
        "disp_prev": disp_prev,
        "disp_crit": disp_crit,
        "interp_disp": interp_disp,
    }


def get_overall_critical_summary(
    odb, step_index=1, strain_threshold=0.003, num_intervals=30, node_set_name="SUBSTRATE-1.TPC_A"
):
    """
    对两个面进行关键帧分析和插值计算，并自动选择最优结果。

    Args:
        odb: ODB对象。
        step_index (int, optional): 步骤索引，默认为1 (Step-2)，从0开始。
        strain_threshold (float, optional): 应变阈值，默认为0.003 (0.3%)。
        num_intervals (int, optional): Path插值间隔数，默认为30。
        node_set_name (str, optional): 节点集名称，默认为"SUBSTRATE-1.TPC_A"。

    Returns:
        dict: 包含ODB名称、顶部面、底部面分析结果及自动选择结果的字典，包括：
            odb: ODB文件名
            top: 顶部面完整分析结果
            bottom: 底部面完整分析结果
            selected: 选择的面名称（"TOP"/"BOTTOM"或None）
    """
    # 获取步骤对象
    step_name = list(odb.steps.keys())[step_index]

    print( "开始检查步骤索引 {} ({})".format(step_index, step_name ))

    # 创建路径
    created_paths = create_wire_paths(odb)

    # 分别对TOP和BOTTOM面进行完整分析
    print("开始分析顶部面")
    top_data = get_face_critical_frame(
        odb, created_paths, "TOP", step_index, strain_threshold, num_intervals, node_set_name
    )
    print("开始分析底部面")
    bottom_data = get_face_critical_frame(
        odb, created_paths, "BOTTOM", step_index, strain_threshold, num_intervals, node_set_name
    )

    # 选择更靠前的帧（帧号小者）
    # 进行更严谨的检查，考虑一个面找到关键帧而另一个面未找到的情况
    selected_face = None
    if top_data["found"] is True and bottom_data["found"] is True:
        # 两个面都找到关键帧，选择帧号更小的
        if top_data["crit_frame"] < bottom_data["crit_frame"]:
            selected_face = "TOP"
        else:
            selected_face = "BOTTOM"
    elif top_data["found"] is True and bottom_data["found"] is False:
        # 只有顶部面找到关键帧，检查其帧号是否小于底部面的边界帧号
        if top_data["crit_frame"] <= bottom_data["crit_frame"]:
            selected_face = "TOP"
    elif top_data["found"] is False and bottom_data["found"] is True:
        # 只有底部面找到关键帧，检查其帧号是否小于顶部面的边界帧号
        if bottom_data["crit_frame"] <= top_data["crit_frame"]:
            selected_face = "BOTTOM"

    return {
        "odb": Path(odb.name).stem,
        "top": top_data,
        "bottom": bottom_data,
        "selected": selected_face,
    }


def main():
    # 获取当前视图中的ODB文件并执行分析
    vp = session.viewports[session.currentViewportName]
    odb = vp.displayedObject
    record = get_overall_critical_summary(odb=odb, step_index=1)

    # 将返回的字典展平为一行 CSV 格式，方便复制
    df = pd.json_normalize([record], sep='_')
    # 输出 CSV header 和该行数据
    print(df.to_csv(index=False, lineterminator='\n'))


if __name__ == "__main__":
    main()