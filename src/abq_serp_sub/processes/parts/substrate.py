from __future__ import annotations
from typing import TYPE_CHECKING

import numpy as np
from abaqus import *
from abaqusConstants import *
from regionToolset import Region

if TYPE_CHECKING:
    from abaqus.Model.Model import Model
    from abaqus.Part.Part import Part

from abq_serp_sub.core.pores import calculate_circle_radius, generate_circles_grid
from abq_serp_sub.utils.abaqus_utils import (
    filter_edges_by_radius,
    pick_by_index,
    filter_objects_by_vertex_bounds,
)

# 配置类从 core/context 子包导入
from abq_serp_sub.core.context import (
    HyperelasticMaterialConfig,
    SolidSubstrateGeomConfig,
    PorousSubstrateGeomConfig,
    SubstrateMeshConfig,
    SubstrateConfig,
    SolidSubstrateConfig,
    PorousSubstrateConfig,
)


def build_substrate(config: SubstrateConfig):
    """
    根据配置类型自动选择构建实心或多孔基底。

    Parameters
    ----------
    config : SubstrateConfig
        基底配置，可以是 SolidSubstrateConfig 或 PorousSubstrateConfig

    Returns
    -------
    Part
        创建好的基底部件
    """
    if isinstance(config, PorousSubstrateConfig):
        return build_porous_substrate(config)
    else:
        return build_solid_substrate(config)


# region 私有辅助函数
def _get_or_create_model(modelname: str) -> Model:
    """
    获取已存在的模型，或创建新模型。

    Parameters
    ----------
    modelname : str
        Abaqus 模型名称（mdb.models 的键）。

    Returns
    -------
    Model
        Abaqus 模型对象。
    """
    try:
        return mdb.models[modelname]
    except KeyError:
        return mdb.Model(name=modelname)


def _create_hyperelastic_material(model: Model, config: HyperelasticMaterialConfig) -> None:
    """
    在模型中创建超弹性材料（Mooney-Rivlin 模型）。

    Parameters
    ----------
    model : Model
        Abaqus 模型对象。
    config : HyperelasticMaterialConfig
        超弹性材料配置，必须显式提供。
    """
    material = model.Material(name=config.name)
    return material.Hyperelastic(
        materialType=ISOTROPIC,
        testData=OFF,
        type=MOONEY_RIVLIN,
        volumetricResponse=VOLUMETRIC_DATA,
        table=((config.c1, config.c2, config.d),),
    )


def _assign_section_to_part(model: Model, part: Part, material_name: str) -> None:
    """
    创建均质实体截面并赋予部件的所有单元。

    Parameters
    ----------
    model : Model
        Abaqus 模型对象。
    part : Part
        要赋予截面的部件。
    material_name : str
        材料名称。
    """
    section_name = f"{material_name}-section"
    model.HomogeneousSolidSection(name=section_name, material=material_name)
    cells = part.cells
    region = Region(cells=cells)
    return part.SectionAssignment(region=region, sectionName=section_name)


def _seed_substrate_part(sub_part: Part, seed_size: float) -> None:
    """
    对基底部件进行布种，包括全局布种和厚度边偏置布种。

    Parameters
    ----------
    part : Part
        要布种的部件。
    seed_size : float
        全局布种尺寸。
    """
    # 全局布种
    sub_part.seedPart(size=seed_size, deviationFactor=0.1, minSizeFactor=0.1)

    # 厚度边使用偏置布种
    thickness_edges = sub_part.sets["ThicknessEdges"].edges
    sub_part.seedEdgeByBias(
        biasMethod=SINGLE,
        end2Edges=thickness_edges,
        ratio=2,
        number=7,
        constraint=FINER,
    )

    # 生成网格
    sub_part.generateMesh()
# endregion


# region 多孔基底构建
def build_porous_substrate(config: PorousSubstrateConfig):
    """
    根据给定的圆孔布局创建多孔基底部件。

    Parameters
    ----------
    config : PorousSubstrateConfig
        多孔基底配置对象，包含：
        - geom.circles: 圆孔数据数组 (n_rows, n_cols, 3)
        - geom.square_size: 正方形边长
        - geom.depth: 拉伸深度
        - part.modelname: 模型名称
        - part.partname: 部件名称
        - part.seed_size: 布种尺寸

    Returns
    -------
    Part
        创建好的部件对象，用于后续分析操作。
    """
    # 提取配置
    circles = config.geom.circles
    square_size = config.geom.square_size
    depth = config.geom.depth
    modelname = config.modelname
    partname = config.partname
    substrate_seed_size = config.mesh.seed_size

    model = _get_or_create_model(modelname)

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

    # --------------- 定义材料与截面 --------------- #
    _create_hyperelastic_material(model, config.material)
    _assign_section_to_part(model, part, config.material.name)

    # --------------- 布种划分网格 -------------- #
    _seed_substrate_part(part, substrate_seed_size)

    return part
# endregion


# region 实心基底构建
def build_solid_substrate(config: SolidSubstrateConfig):
    """
    创建实心矩形基底部件（无孔洞）。

    Parameters
    ----------
    config : SolidSubstrateConfig
        实心基底配置对象，包含：
        - geom.length: 基底长度（X方向）
        - geom.width: 基底宽度（Y方向）
        - geom.depth: 拉伸深度（Z方向）
        - part.modelname: 模型名称
        - part.partname: 部件名称
        - part.seed_size: 布种尺寸

    Returns
    -------
    Part
        创建好的部件对象，用于后续分析操作。
    """
    # 提取配置
    length = config.geom.length
    width = config.geom.width
    depth = config.geom.depth
    modelname = config.modelname
    partname = config.partname
    substrate_seed_size = config.mesh.seed_size

    model = _get_or_create_model(modelname)

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
    _create_hyperelastic_material(model, config.material)
    _assign_section_to_part(model, part, config.material.name)
    # endregion

    # region 布种划分网格
    _seed_substrate_part(part, substrate_seed_size)
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
