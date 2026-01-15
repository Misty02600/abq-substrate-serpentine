import re
import subprocess
from abaqus import session


def current_display_info(viewport_name=None):
    """返回指定视口或当前激活视口里正在显示的对象信息。

    Args:
        viewport_name (str, optional): 视口名称，如果为None则使用当前激活视口

    Returns:
        dict: 包含以下可能的键：
            - viewport (str): 视口名。
            - kind (str): 显示对象类型（'PART'/'ASSEMBLY'/'SKETCH'/'ODB'/'XY'/'OTHER'）。
            - model_name (str|None): 若为 CAE 模型对象，所属模型名。
            - object_name (str|None): 对象名（Part 名、草图名、XYPlot 名等）。
            - odb_path (str|None): 若为 ODB，给出其路径。
    """
    if viewport_name is None:
        viewport_name = session.currentViewportName

    if viewport_name not in session.viewports:
        raise ValueError(f"视口 '{viewport_name}' 不存在")

    vp = session.viewports[viewport_name]
    obj = vp.displayedObject

    info = dict(viewport=vp.name, kind='OTHER',
                model_name=None, object_name=None, odb_path=None)

    if obj is None:
        return info

    cls = obj.__class__.__name__
    info['object_name'] = getattr(obj, 'name', None)

    if cls in ('Part',):
        # Part 对象自带 modelName
        info['kind'] = 'PART'
        info['model_name'] = getattr(obj, 'modelName', None)

    elif cls in ('Assembly', 'RootAssembly'):
        # 装配对象（根装配）通常也有 modelName
        info['kind'] = 'ASSEMBLY'
        info['model_name'] = getattr(obj, 'modelName', None)

    elif cls in ('ConstrainedSketch',):
        info['kind'] = 'SKETCH'
        info['model_name'] = getattr(obj, 'modelName', None)

    elif cls in ('Odb',):
        info['kind'] = 'ODB'
        # 对于ODB对象，name属性就是完整路径
        odb_full_path = getattr(obj, 'name', None)
        info['odb_path'] = odb_full_path

        # 从完整路径中提取文件名（不含扩展名）作为模型名
        if odb_full_path:
            from pathlib import Path
            odb_filename = Path(odb_full_path).stem  # 获取不含扩展名的文件名
            info['model_name'] = odb_filename

    elif cls in ('XYPlot',):
        info['kind'] = 'XY'

    return info


def get_physical_cpu_cores():
    """
    获取物理CPU核心数量

    Returns:
        int: 物理CPU核心数量
    """
    try:
        out = subprocess.check_output(
            "WMIC CPU get NumberOfCores", shell=True, text=True
        )
        cores = [int(n) for n in re.findall(r"\d+", out)]
        physical_cores = sum(cores)
        return int(physical_cores)
    except Exception as e:
        print(f"获取CPU核心数失败: {e}")
        return 2  # 默认返回2核心


def pick_by_index(abaqus_array, indices):
    """
    根据索引列表从Abaqus数组中获取指定元素，返回Abaqus Sequence

    Parameters:
        abaqus_array: Abaqus Array
            Abaqus几何对象数组（如EdgeArray、VertexArray等）
        indices: 索引列表（list of int）

    Returns:
        Abaqus Sequence：只包含指定索引的元素
    """

    result = abaqus_array[0:0]
    for idx in indices:
        result += abaqus_array[idx : idx + 1]
    return result


def filter_objects_by_vertex_bounds(
    part,
    obj_type,
    xMin=None,
    yMin=None,
    zMin=None,
    xMax=None,
    yMax=None,
    zMax=None,
):
    """
    根据几何对象顶点是否在指定的xyz边界范围内来筛选对象

    Parameters
    ----------
    part : Part
        Abaqus部件对象
    obj_type : str
        几何对象类型，可选: 'edges', 'faces', 'vertices', 'cells'
    xMin, yMin, zMin : float, optional
        各方向最小值，不指定则为该方向全范围
    xMax, yMax, zMax : float, optional
        各方向最大值，不指定则为该方向全范围

    Returns
    -------
    objects_in_region : Array
        符合条件的几何对象Array
    """
    valid_obj_types = ["edges", "faces", "vertices", "cells"]
    if obj_type not in valid_obj_types:
        raise ValueError(
            f"obj_type必须是{valid_obj_types}之一，当前为: {obj_type}"
        )

    # 设置默认值为全范围
    if xMin is None:
        xMin = -1e6
    if yMin is None:
        yMin = -1e6
    if zMin is None:
        zMin = -1e6
    if xMax is None:
        xMax = 1e6
    if yMax is None:
        yMax = 1e6
    if zMax is None:
        zMax = 1e6

    # 直接获取指定类型的几何对象集合
    all_objects = getattr(part, obj_type)

    # 筛选在区域内的对象
    objects_in_region_indices = []

    for i, obj in enumerate(all_objects):
        # 获取对象的顶点索引
        vertex_indices = obj.getVertices()

        # 检查是否有顶点在指定区域内
        has_vertex_in_region = False
        for vertex_idx in vertex_indices:
            vertex = part.vertices[vertex_idx]
            x, y, z = vertex.pointOn[0]

            # 检查顶点是否在xyz边界范围内
            if (xMin <= x <= xMax and
                yMin <= y <= yMax and
                zMin <= z <= zMax):
                has_vertex_in_region = True
                break

        if has_vertex_in_region:
            objects_in_region_indices.append(i)

    # 使用pick_by_index获取筛选后的对象数组
    objects_in_region = pick_by_index(all_objects, objects_in_region_indices)

    return objects_in_region


def filter_edges_by_radius(
    edges, radius=None, min_radius=None, max_radius=None, non_arc=False
):
    """
    从EdgeArray中筛选出半径等于或在指定范围内的圆弧边，或非圆弧边，返回EdgeSequence。
    非圆弧边可通过参数选择是否返回。

    Parameters:
        edge_array: EdgeArray，Abaqus的边数组
        radius: float，可选，筛选等于该半径的圆弧边
        min_radius: float，可选，筛选半径大于等于该值的圆弧边
        max_radius: float，可选，筛选半径小于等于该值的圆弧边
        non_arc: bool，若为True则仅返回非圆弧边，忽略半径参数
    Returns:
        Sequence：只包含符合条件的边
    """
    tol = 1e-6
    result = edges[0:0]
    for i, edge in enumerate(edges):
        try:
            r = edge.getRadius()
            is_arc = True
        except Exception:
            is_arc = False
        if non_arc:
            if not is_arc:
                result += edges[i : i + 1]
        else:
            if not is_arc:
                continue
            if radius is not None:
                if abs(r - radius) < tol:
                    result += edges[i : i + 1]
            else:
                if min_radius is not None and r < min_radius - tol:
                    continue
                if max_radius is not None and r > max_radius + tol:
                    continue
                result += edges[i : i + 1]
    return result


def get_bounding_box(obj):
    """
    获取部件或部件实例的边界盒

    通过对象的边序列的getBoundingBox方法自动计算边界盒范围

    Parameters
    ----------
    obj : Part or PartInstance
        Abaqus部件对象或部件实例对象

    Returns
    -------
    dict
        包含'low'和'high'键的字典，格式与ABAQUS API一致
        {'low': (xMin, yMin, zMin), 'high': (xMax, yMax, zMax)}
    """
    edges = obj.edges

    if len(edges) == 0:
        raise ValueError("对象中没有边，无法计算边界盒")

    # 直接返回ABAQUS API的原始格式
    return edges.getBoundingBox()


def get_part_bounding_box(part):
    """
    获取部件的边界盒（已弃用，请使用 get_bounding_box）

    .. deprecated::
        使用 get_bounding_box 代替，该函数同时支持部件和部件实例
    """
    return get_bounding_box(part)