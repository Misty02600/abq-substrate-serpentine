from typing import TYPE_CHECKING

import numpy as np
from abaqus import *
from abaqusConstants import *
from regionToolset import Region

if TYPE_CHECKING:
    from abaqus.Model.Model import Model

from .pores import calculate_circle_radius, generate_circles_grid
from ..utils.abaqus_utils import filter_edges_by_radius, pick_by_index, filter_objects_by_vertex_bounds


# region 多孔基底构建
def build_porous_substrate(
    modelname: str,
    partname: str,
    circles: np.ndarray,  # 圆孔位置和大小数组 (n_rows, n_cols, 3)
    square_size: float,  # 正方形边长
    depth: float = 0.25,  # 拉伸深度
    substrate_seed_size: float = 0.01,  # 基底布种尺寸
    generate_mesh: bool = True,  # 是否在此函数中生成网格
):
    """
    根据给定的圆孔布局创建多孔基底部件

    Parameters
    ----------
    modelname : str
        Abaqus 模型名称（mdb.models 的键）。
    partname : str
        生成的部件名称，与草图名称相同。
    circles : np.ndarray
        圆孔数据数组，其形状为 (n_rows, n_cols, 3)，每个元素为 (x, y, r)。
    square_size : float
        正方形边长。
    depth : float, optional
        拉伸深度，默认为 0.25。
    substrate_seed_size : float, optional
        基底布种尺寸，默认为 0.01。
    generate_mesh : bool, optional
        是否在此函数中生成网格，默认为 True。

    Returns
    -------
    Part
        创建好的部件对象，用于后续分析操作。
    """
    try:
        model = mdb.models[modelname]
    except KeyError:
        model = mdb.Model(name=modelname)

    # -------------- 计算关键尺寸 -------------- #
    n_rows, n_cols = circles.shape[:2]
    rect_length = n_cols * square_size
    rect_width = n_rows * square_size

    # --------------- 绘制草图 --------------- #
    part_sk = model.ConstrainedSketch(
        name="substrate_sketch", sheetSize=max(rect_length, rect_width) * 2
    )

    # 绘制矩形
    part_sk.rectangle(point1=(0.0, 0.0), point2=(rect_length, rect_width))

    # 绘制圆孔
    circle_probes = np.zeros((n_rows, n_cols, 2))
    for i in range(n_rows):
        for j in range(n_cols):
            x, y, r = circles[i, j]
            part_sk.CircleByCenterPerimeter(center=(x, y), point1=(x + r, y))
            circle_probes[i, j] = (x + r, y)

    # --------------- 创建部件 --------------- #
    part = model.Part(
        name=partname, dimensionality=THREE_D, type=DEFORMABLE_BODY
    )
    part.BaseSolidExtrude(sketch=part_sk, depth=depth)

    # --------------- 创建集 --------------- #
    # 获取面
    bottom_faces = part.faces.getByBoundingBox(zMin=0, zMax=0)
    part.Set(name="BottomFace", faces=bottom_faces)

    left_faces = part.faces.getByBoundingBox(xMin=0, xMax=0)
    part.Set(name="LeftFace", faces=left_faces)

    right_faces = part.faces.getByBoundingBox(xMin=rect_length, xMax=rect_length)
    part.Set(name="RightFace", faces=right_faces)

    top_faces = part.faces.getByBoundingBox(zMin=depth, zMax=depth)
    part.Set(name="TopFace", faces=top_faces)

    part.Surface(name="TopFace", side1Faces=top_faces)

    # 获取厚度方向四条边
    thickness_edges = part.edges.findAt(
        ((0.0, 0.0, depth / 2),),
        ((rect_length, 0.0, depth / 2),),
        ((0.0, rect_width, depth / 2),),
        ((rect_length, rect_width, depth / 2),)
    )
    part.Set(name="ThicknessEdges", edges=thickness_edges)

    # 获取三点式约束的控制点
    # TPC_A: 原点 (0,0,0)
    TPC_A = part.vertices.findAt(((0.0, 0.0, 0.0),))
    part.Set(name="TPC_A", vertices=TPC_A)

    # TPC_B: (0, rect_width, 0) 点
    TPC_B = part.vertices.findAt(((0.0, rect_width, 0.0),))
    part.Set(name="TPC_B", vertices=TPC_B)

    # --------------- 划分部件 --------------- #
    # 构造草图划分正方形，仅当n较小时划分
    if n_rows < 8:
        partition_sketch = model.ConstrainedSketch(
            name="partition_sketch1",
            sheetSize=max(rect_length, rect_width) * 2,
            transform=(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, depth)  # 平移到顶面
        )

        for i in range(1, n_cols):
            x = i * square_size
            partition_sketch.Line(point1=(x, 0.0), point2=(x, rect_width))
        for j in range(1, n_rows):
            y = j * square_size
            partition_sketch.Line(point1=(0.0, y), point2=(rect_length, y))

        part.PartitionFaceBySketch(sketch=partition_sketch, faces=top_faces)

    # 构造草图划分圆间隙
    partition_sketch = model.ConstrainedSketch(
        name="partition_sketch2",
        sheetSize=max(rect_length, rect_width) * 2,
        transform=(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, depth)  # 平移到顶面
    )

    top_faces = part.sets["TopFace"].faces

    # 水平拆分线：对每一行，连接左边界到各个圆的右端点，最后到右边界
    for i in range(n_rows):
        # 取该行第一个圆和最后一个圆的右端点y坐标，保证首尾为直线
        first_y = circle_probes[i, 0][1]
        last_y = circle_probes[i, -1][1]

        # 起点：左边界与第一个圆右端点y相同
        start_point = (0.0, first_y)

        # 依次连接该行每个圆的右端点
        for j in range(n_cols):
            circle_right_x, circle_right_y = circle_probes[i, j]
            partition_sketch.Line(point1=start_point, point2=(circle_right_x, circle_right_y))
            start_point = (circle_right_x, circle_right_y)

        # 终点：右边界与最后一个圆右端点y相同
        end_point = (rect_length, last_y)
        partition_sketch.Line(point1=start_point, point2=end_point)

    # 垂直拆分线：连接上下边界，每列单元中心位置
    for j in range(n_cols):
        center_x = (j + 0.5) * square_size
        point1 = (center_x, 0.0)           # 下边界
        point2 = (center_x, rect_width)   # 上边界
        partition_sketch.Line(point1=point1, point2=point2)

    part.PartitionFaceBySketch(sketch=partition_sketch, faces=top_faces)

    # ---------------- 创建边集 --------------- #
    # 获取顶面所有边
    top_edges = part.edges.getByBoundingBox(zMin=depth, zMax=depth)
    part.Set(name="TopEdges", edges=top_edges)

    # 获取顶面圆形边
    top_circular_edges = filter_edges_by_radius(top_edges, non_arc=False)
    part.Set(name="TopCircleEdges", edges=top_circular_edges)

    # 获取顶面直线边
    top_line_edges = filter_edges_by_radius(top_edges, non_arc=True)
    part.Set(name="TopLineEdges", edges=top_line_edges)

    # --------------- 定义材料 --------------- #
    pdms = model.Material(name="PDMS")
    pdms.Hyperelastic(
        materialType=ISOTROPIC,
        testData=OFF,
        type=MOONEY_RIVLIN,
        volumetricResponse=VOLUMETRIC_DATA,
        table=((0.27027, 0.067568, 0.12),),
    )

    # -------------- 创建分配截面 ------------- #
    model.HomogeneousSolidSection(name="PDMS-section", material="PDMS")
    cells = part.cells
    region = Region(cells=cells)
    part.SectionAssignment(region=region, sectionName="PDMS-section")

    # --------------- 布种划分网格 -------------- #
    # 使用全局布种
    part.seedPart(size=substrate_seed_size, deviationFactor=0.1, minSizeFactor=0.1)
    # 厚度边使用偏置布种
    thickness_edges = part.sets["ThicknessEdges"].edges
    part.seedEdgeByBias(
        biasMethod=SINGLE,
        end2Edges=thickness_edges,
        ratio=2,
        number=7,
        constraint=FINER,
    )

    # 根据参数决定是否生成网格
    if generate_mesh:
        part.generateMesh()

    return part
# endregion


# region 实心基底构建
def build_solid_substrate(
    modelname: str,
    partname: str,
    length: float,
    width: float,
    depth: float = 0.25,
    substrate_seed_size: float = 0.01,
    generate_mesh: bool = True,
):
    """
    创建实心矩形基底部件（无孔洞）

    Parameters
    ----------
    modelname : str
        Abaqus 模型名称（mdb.models 的键）。
    partname : str
        生成的部件名称。
    length : float
        基底长度（X方向）。
    width : float
        基底宽度（Y方向）。
    depth : float, optional
        拉伸深度（Z方向），默认为 0.25。
    substrate_seed_size : float, optional
        基底布种尺寸，默认为 0.01。
    generate_mesh : bool, optional
        是否在此函数中生成网格，默认为 True。

    Returns
    -------
    Part
        创建好的部件对象，用于后续分析操作。
    """
    try:
        model = mdb.models[modelname]
    except KeyError:
        model = mdb.Model(name=modelname)

    # region 绘制草图
    part_sk = model.ConstrainedSketch(
        name="solid_substrate_sketch", sheetSize=max(length, width) * 2
    )
    part_sk.rectangle(point1=(0.0, 0.0), point2=(length, width))
    # endregion

    # region 创建部件
    part = model.Part(
        name=partname, dimensionality=THREE_D, type=DEFORMABLE_BODY
    )
    part.BaseSolidExtrude(sketch=part_sk, depth=depth)
    # endregion

    # region 创建集
    # 底面
    bottom_faces = part.faces.getByBoundingBox(zMin=0, zMax=0)
    part.Set(name="BottomFace", faces=bottom_faces)

    # 左面
    left_faces = part.faces.getByBoundingBox(xMin=0, xMax=0)
    part.Set(name="LeftFace", faces=left_faces)

    # 右面
    right_faces = part.faces.getByBoundingBox(xMin=length, xMax=length)
    part.Set(name="RightFace", faces=right_faces)

    # 顶面
    top_faces = part.faces.getByBoundingBox(zMin=depth, zMax=depth)
    part.Set(name="TopFace", faces=top_faces)
    part.Surface(name="TopFace", side1Faces=top_faces)

    # 厚度方向四条边
    thickness_edges = part.edges.findAt(
        ((0.0, 0.0, depth / 2),),
        ((length, 0.0, depth / 2),),
        ((0.0, width, depth / 2),),
        ((length, width, depth / 2),)
    )
    part.Set(name="ThicknessEdges", edges=thickness_edges)

    # 三点式约束控制点
    TPC_A = part.vertices.findAt(((0.0, 0.0, 0.0),))
    part.Set(name="TPC_A", vertices=TPC_A)

    TPC_B = part.vertices.findAt(((0.0, width, 0.0),))
    part.Set(name="TPC_B", vertices=TPC_B)

    # 顶面所有边
    top_edges = part.edges.getByBoundingBox(zMin=depth, zMax=depth)
    part.Set(name="TopEdges", edges=top_edges)

    # 顶面直线边（实心基底没有圆形边）
    top_line_edges = filter_edges_by_radius(top_edges, non_arc=True)
    part.Set(name="TopLineEdges", edges=top_line_edges)
    # endregion

    # region 定义材料与截面
    pdms = model.Material(name="PDMS")
    pdms.Hyperelastic(
        materialType=ISOTROPIC,
        testData=OFF,
        type=MOONEY_RIVLIN,
        volumetricResponse=VOLUMETRIC_DATA,
        table=((0.27027, 0.067568, 0.12),),
    )

    model.HomogeneousSolidSection(name="PDMS-section", material="PDMS")
    cells = part.cells
    region = Region(cells=cells)
    part.SectionAssignment(region=region, sectionName="PDMS-section")
    # endregion

    # region 布种划分网格
    part.seedPart(size=substrate_seed_size, deviationFactor=0.1, minSizeFactor=0.1)

    # 厚度边使用偏置布种
    thickness_edges = part.sets["ThicknessEdges"].edges
    part.seedEdgeByBias(
        biasMethod=SINGLE,
        end2Edges=thickness_edges,
        ratio=2,
        number=7,
        constraint=FINER,
    )

    if generate_mesh:
        part.generateMesh()
    # endregion

    return part
# endregion


# region 基底边细化
def refine_substrate_edges_around_wire(
    modelname: str,
    partname: str,
    wire_bounds: tuple,
    substrate_edge_seed_size: float
):
    """
    导线周围基底边细化函数

    使用filter_objects_by_vertex_bounds获取区域内的边，然后直接应用基底细化逻辑

    Parameters
    ----------
    modelname : str
        Abaqus 模型名称
    partname : str
        部件名称
    wire_bounds : tuple
        导线区域边界 (x1, y1, z1, x2, y2, z2)
    substrate_edge_seed_size : float
        基底边在导线区域内的布种尺寸
    """
    model = mdb.models[modelname]
    part = model.parts[partname]

    x1, y1, z1, x2, y2, z2 = wire_bounds
    min_x, max_x = min(x1, x2), max(x1, x2)
    min_y, max_y = min(y1, y2), max(y1, y2)
    min_z, max_z = min(z1, z2), max(z1, z2)

    print(f"开始导线周围边细化: ({min_x:.3f}, {min_y:.3f}, {min_z:.3f}) 到 ({max_x:.3f}, {max_y:.3f}, {max_z:.3f})")

    # 使用filter_objects_by_vertex_bounds获取区域内的边
    edges_to_refine = filter_objects_by_vertex_bounds(
        part=part,
        obj_type='edges',
        xMin=min_x, xMax=max_x,
        yMin=min_y, yMax=max_y,
        zMin=min_z, zMax=max_z
    )

    # 为筛选到的边创建一个 Abaqus 集，便于后续引用和调试

    set_name = "EdgesToRefine"
    part.Set(name=set_name, edges=edges_to_refine)
    print(f"已创建集合 '{set_name}'，包含 {len(edges_to_refine) if edges_to_refine else 0} 条边")


    # 直接应用基底细化逻辑
    if edges_to_refine and len(edges_to_refine) > 0:
        part.seedEdgeBySize(
            edges=edges_to_refine,
            size=substrate_edge_seed_size,
            constraint=FINER
        )
        print(f"已对导线区域内的 {len(edges_to_refine)} 条边应用布种尺寸: {substrate_edge_seed_size}")
    else:
        print("导线区域内未找到需要细化的边")

    # 重新生成网格
    part.generateMesh()
    print("导线周围边细化完成")
# endregion