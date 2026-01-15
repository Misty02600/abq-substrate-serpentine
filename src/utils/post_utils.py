from abaqus import *
from abaqusConstants import *
from odbAccess import *
import numpy as np


def sort_nodes_along_line(*node_sets):
    """将一系列顺次连接的节点集按物理路径排序。

    该函数接收任意数量的Abaqus节点集对象，这些节点集被假定为
    代表了多段首尾相连的几何边。函数会返回一个沿着整条路径
    连续排列的、无重复的节点对象元组。

    工作原理:
    1.  **端点识别**: Abaqus中由边生成的节点集，其前两个节点是边的端点。
    2.  **边方向确定**: 通过比较相邻边的端点重合关系确定边的方向。
    3.  **内部节点排序**: 通过比较内部节点首个节点与当前边起终点的距离
        来确定内部节点的正确方向。
    4.  **路径拼接**: 将每段排好序的节点列表（不含重复的连接点）拼接
        起来，形成最终的完整路径。

    Args:
        *node_sets: 任意数量的Abaqus节点集（NodeSet）对象，要求这些
                    节点集对应的原始几何边是首尾顺次连接的。

    Returns:
        tuple: 一个包含所有已排序的Abaqus节点（MeshNode）对象的元组。
               如果未提供任何节点集，则返回一个空元组。
    """
    if not node_sets:
        return tuple()

    # 辅助函数，用于计算两个节点坐标之间的欧氏距离的平方
    def get_distance_sq(node1, node2):
        return np.sum((np.array(node1.coordinates) - np.array(node2.coordinates))**2)

    sorted_path_nodes = []
    last_end_node = None

    for i, current_set in enumerate(node_sets):
        nodes_on_edge = current_set.nodes

        # 1. 分离端点和内部节点
        endpoint1, endpoint2 = nodes_on_edge[0], nodes_on_edge[1]
        internal_nodes = list(nodes_on_edge[2:])

        # 2. 确定当前边的起点和终点
        # 这是第一条边
        if last_end_node is None:
            # 只有第一条边需要通过下一条边的信息来确定方向
            if i + 1 < len(node_sets):  # 有下一条边时
                next_set_endpoints = {node.label for node in node_sets[i+1].nodes[:2]}
                if endpoint1.label in next_set_endpoints:
                    current_start_node = endpoint2
                    current_end_node = endpoint1
                else:
                    current_start_node = endpoint1
                    current_end_node = endpoint2
            else: # 只有一条边，方向任意
                current_start_node = endpoint1
                current_end_node = endpoint2

        else:  # 后续的边：非起点的端点就是终点
            if endpoint1.label == last_end_node.label:
                current_start_node = endpoint1
                current_end_node = endpoint2
            else:
                # 断言确保边是连接的
                assert endpoint2.label == last_end_node.label, \
                    f"边 {i-1} 和边 {i} 之间没有公共连接点！"
                current_start_node = endpoint2
                current_end_node = endpoint1

        # 3. 确定内部节点的排列方向
        sorted_internal_nodes = []
        if internal_nodes:
            # 比较内部节点的第一个点与当前边起终点的距离
            first_internal = internal_nodes[0]
            dist_to_start = get_distance_sq(first_internal, current_start_node)
            dist_to_end = get_distance_sq(first_internal, current_end_node)

            # 如果内部节点的第一个点离起点更近，保持原顺序
            # 如果离终点更近，则反向排列
            if dist_to_start <= dist_to_end:
                sorted_internal_nodes = list(internal_nodes)
            else:
                sorted_internal_nodes = list(reversed(internal_nodes))

        # 4. 拼接路径
        if not sorted_path_nodes:  # 如果是第一条边，加入起点
            sorted_path_nodes.append(current_start_node)

        sorted_path_nodes.extend(sorted_internal_nodes)
        sorted_path_nodes.append(current_end_node)

        # 更新最后一段的终点，用于下一次迭代
        last_end_node = current_end_node

    return tuple(sorted_path_nodes)
