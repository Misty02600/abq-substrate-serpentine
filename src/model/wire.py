# ------------------------------------ #
#       修正导线两端粘结圆部分的位置，使圆心处于对称轴上       #
# ------------------------------------ #
from typing import TYPE_CHECKING

import numpy as np
from abaqus import *
from abaqusConstants import *

if TYPE_CHECKING:
    from abaqus.Model.Model import Model


def build_serpentine_wire(
    modelname: str,
    partname: str,
    w: float = 0.05,  # 蛇形线宽
    l_1: float = 0.5,  # 单元体水平节距（一个完整周期宽度）
    l_2: float = 0.5,  # 竖直直线段长度
    m: int = 4,  # 周期数
    wire_seed_size: float = 0.005,  # 蛇形线布种尺寸
    pi_thickness: float = 0.003,  # PI 单层厚度
    cu_thickness: float = 0.0006,  # Cu 单层厚度
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0),  # 草图原点坐标
):
    """
    在指定模型中创建一个二维蛇形导线（PI-Cu-PI）壳单元草图，
    并生成同名 Part。

    Parameters
    ----------
    modelname : str
        Abaqus 模型名称（`mdb.models` 的键）。
    partname : str
        生成的 Part 与草图名称。
    w : float
        蛇形导线带状线宽。
    l_1 : float
        一个完整周期沿 X 方向的宽度。
    l_2 : float
        每条竖直直线段的长度（决定 y_top）。
    m : int
        周期数（完整周期的个数）。
    wire_seed_size : float
        蛇形线布种尺寸。
    pi_thickness : float
        PI 单层厚度（上下两层相同）。
    cu_thickness : float
        Cu 单层厚度（中间层）。
    origin : tuple[float, float, float]
        草图原点坐标。

    Returns
    -------
    Part
        创建好的 Part 对象，便于后续引用。
    """

    try:
        model = mdb.models[modelname]
    except KeyError:
        model = mdb.Model(name=modelname)

    # ---------------- 计算关键坐标 ----------------
    x_0: float = -w / 2  # 修改起始坐标为 -w/2
    x_1: float = x_0 + w  # 内左
    x_2: float = x_0 + l_1 / 2.0  # 内右
    x_3: float = x_2 + w  # 外右

    y_mid: float = 0.0
    y_bot: float = y_mid - l_2 / 2.0
    y_top: float = y_mid + l_2 / 2.0

    # 部件最右侧(最后一个周期末)端点坐标
    x_inner_right: float = m * l_1 - w / 2  # 平移总体左移 w/2
    x_outer_right: float = x_inner_right + w

    # ---------------- 创建草图 ----------------
    sk = model.ConstrainedSketch(
        name=partname,
        sheetSize=10.0,
        transform=(1, 0, 0, 0, 1, 0, 0, 0, 1) + origin,
    )

    # 竖直线（半周期）
    line_0 = sk.Line(point1=(x_0, y_top), point2=(x_0, y_mid))  # 外左
    line_1 = sk.Line(point1=(x_1, y_top), point2=(x_1, y_mid))  # 内左
    line_2 = sk.Line(point1=(x_2, y_top), point2=(x_2, y_mid))  # 内右
    line_3 = sk.Line(point1=(x_3, y_top), point2=(x_3, y_mid))  # 外右

    # 顶部同心圆弧（半周期）
    arc_0 = sk.ArcByStartEndTangent(
        point1=(x_0, y_top),
        point2=(x_3, y_top),
        entity=line_0,
    )
    arc_1 = sk.ArcByStartEndTangent(
        point1=(x_1, y_top),
        point2=(x_2, y_top),
        entity=line_1,
    )

    half_objs = (line_0, line_1, line_2, line_3, arc_0, arc_1)

    # 通过 180° 旋转复制 → 完整一个周期
    rotate_center = ((x_2 + x_3) * 0.5, y_mid)
    sk.copyRotate(
        centerPoint=rotate_center,
        angle=180.0,
        objectList=half_objs,
    )

    # 线性阵列复制 m 个周期（仅当m>1时执行）
    if m > 1:
        sk.linearPattern(
            geomList=sk.geometry.values(),
            number1=m,
            spacing1=l_1,
            angle1=0.0,
            number2=1,
            spacing2=l_1,
            angle2=90.0,
        )

    # 左右端封闭圆弧
    sk.ArcByCenterEnds(
        center=((x_0 + x_1) * 0.5, y_mid),
        point1=(x_0, y_mid + w),
        point2=(x_1, y_mid + w),
        direction=COUNTERCLOCKWISE,
    )

    sk.ArcByCenterEnds(
        center=((x_inner_right + x_outer_right) * 0.5, y_mid),
        point1=(x_inner_right, y_mid - w),
        point2=(x_outer_right, y_mid - w),
        direction=CLOCKWISE,
    )

    # 裁去多余线段
    g = sk.geometry

    trim_p_left_outer = (x_0, y_mid + w / 2)
    trim_p_left_inner = (x_1, y_mid + w / 2)
    trim_p_right_inner = (x_inner_right, y_mid - w / 2)
    trim_p_right_outer = (x_outer_right, y_mid - w / 2)

    trim_line_left_outer = g.findAt(trim_p_left_outer)
    trim_line_left_inner = g.findAt(trim_p_left_inner)
    sk.autoTrimCurve(curve1=trim_line_left_outer, point1=trim_p_left_outer)
    sk.autoTrimCurve(curve1=trim_line_left_inner, point1=trim_p_left_inner)

    line_right_inner = g.findAt(trim_p_right_inner)
    line_right_outer = g.findAt(trim_p_right_outer)
    sk.autoTrimCurve(curve1=line_right_inner, point1=trim_p_right_inner)
    sk.autoTrimCurve(curve1=line_right_outer, point1=trim_p_right_outer)

    # ---------------- 生成 Part ----------------
    part = model.Part(
        name=partname,
        dimensionality=THREE_D,
        type=DEFORMABLE_BODY,
    )

    part.BaseShell(sketch=sk)

    # ---------------- 创建集 --------------- #
    f = part.faces
    part.Set(faces=f, name="All")
    part.Surface(side1Faces=f, name="Top")
    part.Surface(side2Faces=f, name="Bottom")

    # --------------- 拆分部件 --------------- #
    # 上部拆分线
    v1 = part.vertices.findAt(
        tuple(np.array((x_0, y_top, 0)) + np.array(origin))
    )
    v2 = part.vertices.findAt(
        tuple(np.array((x_3 + (m - 1) * l_1, y_top, 0)) + np.array(origin))
    )
    part.PartitionFaceByShortestPath(point1=v1, point2=v2, faces=f)

    # 下部拆分线
    v3 = part.vertices.findAt(
        tuple(np.array((x_2, y_bot, 0)) + np.array(origin))
    )
    v4 = part.vertices.findAt(
        tuple(np.array((x_outer_right, y_bot, 0)) + np.array(origin))
    )
    part.PartitionFaceByShortestPath(point1=v3, point2=v4, faces=f)

    # 左端圆盘划分线
    v_left1 = part.vertices.findAt(
        tuple(np.array((x_0, y_mid + w, 0)) + np.array(origin))
    )
    v_left2 = part.vertices.findAt(
        tuple(np.array((x_1, y_mid + w, 0)) + np.array(origin))
    )
    part.PartitionFaceByShortestPath(
        point1=v_left1, point2=v_left2, faces=f
    )

    # 右端圆盘划分线
    v_right1 = part.vertices.findAt(
        tuple(np.array((x_inner_right, y_mid - w, 0)) + np.array(origin))
    )
    v_right2 = part.vertices.findAt(
        tuple(np.array((x_outer_right, y_mid - w, 0)) + np.array(origin))
    )
    part.PartitionFaceByShortestPath(
        point1=v_right1, point2=v_right2, faces=f
    )

    # --------------- 创建边集合 --------------- #
    # 为每个单元体的上下侧边创建集合
    edges = part.edges

    for i in range(m):  # 遍历每个单元体
        # 计算当前单元体的基准x坐标
        unit_x_offset = i * l_1

        # 圆弧半径和圆心坐标
        arc_radius = l_1 / 4
        top_arc_center_x = l_1 / 4 + unit_x_offset
        bottom_arc_center_x = 3 * l_1 / 4 + unit_x_offset

        # 计算边集合定位点的y坐标（基于实际几何形状）
        # 直线段定位点：原硬编码值为0.15和-0.125
        y_quarter_top = y_mid + l_2 / 4
        y_quarter_bot = y_mid - l_2 / 4

        # 圆弧段超出边界，圆弧半径为l_1/4，圆心在y_top和y_bot
        # 每个圆弧都有上半部分和下半部分
        y_arc_top_upper = y_top + arc_radius + w/2  # 顶部圆弧上半部分
        y_arc_top_lower = y_top + arc_radius - w/2  # 顶部圆弧下半部分
        y_arc_bot_upper = y_bot - arc_radius + w/2  # 底部圆弧上半部分
        y_arc_bot_lower = y_bot - arc_radius - w/2  # 底部圆弧下半部分

        # 上侧边集合 (Top-i-j) - 导线的外边界
        # j=1: 左侧直线段上半部分（外边界）
        top_edge_1 = edges.findAt((tuple(np.array((x_0 + unit_x_offset, y_quarter_top, 0.0)) + np.array(origin)),))
        part.Set(edges=top_edge_1, name=f"Top-{i+1}-1")

        # j=2: 顶部圆弧段（Top边取上半部分）
        top_edge_2 = edges.findAt((tuple(np.array((top_arc_center_x, y_arc_top_upper, 0.0)) + np.array(origin)),))
        part.Set(edges=top_edge_2, name=f"Top-{i+1}-2")

        # j=3: 右侧直线段上半部分（外边界）
        top_edge_3 = edges.findAt((tuple(np.array((x_3 + unit_x_offset, y_quarter_top, 0.0)) + np.array(origin)),))
        part.Set(edges=top_edge_3, name=f"Top-{i+1}-3")

        # j=4: 右侧直线段下半部分（外边界）
        top_edge_4 = edges.findAt((tuple(np.array((x_3 + unit_x_offset, y_quarter_bot, 0.0)) + np.array(origin)),))
        part.Set(edges=top_edge_4, name=f"Top-{i+1}-4")

        # j=5: 底部圆弧段（Top边取上半部分）
        top_edge_5 = edges.findAt((tuple(np.array((bottom_arc_center_x, y_arc_bot_upper, 0.0)) + np.array(origin)),))
        part.Set(edges=top_edge_5, name=f"Top-{i+1}-5")

        # j=6: 左侧直线段下半部分（外边界）
        top_edge_6 = edges.findAt((tuple(np.array((x_0 + l_1 + unit_x_offset, y_quarter_bot, 0.0)) + np.array(origin)),))
        part.Set(edges=top_edge_6, name=f"Top-{i+1}-6")

        # 下侧边集合 (Bottom-i-j) - 导线的内边界
        # j=1: 左侧直线段上半部分（内边界）
        bottom_edge_1 = edges.findAt((tuple(np.array((x_1 + unit_x_offset, y_quarter_top, 0.0)) + np.array(origin)),))
        part.Set(edges=bottom_edge_1, name=f"Bottom-{i+1}-1")

        # j=2: 顶部圆弧段（Bottom边取下半部分）
        bottom_edge_2 = edges.findAt((tuple(np.array((top_arc_center_x, y_arc_top_lower, 0.0)) + np.array(origin)),))
        part.Set(edges=bottom_edge_2, name=f"Bottom-{i+1}-2")

        # j=3: 右侧直线段上半部分（内边界）
        bottom_edge_3 = edges.findAt((tuple(np.array((x_2 + unit_x_offset, y_quarter_top, 0.0)) + np.array(origin)),))
        part.Set(edges=bottom_edge_3, name=f"Bottom-{i+1}-3")

        # j=4: 右侧直线段下半部分（内边界）
        bottom_edge_4 = edges.findAt((tuple(np.array((x_2 + unit_x_offset, y_quarter_bot, 0.0)) + np.array(origin)),))
        part.Set(edges=bottom_edge_4, name=f"Bottom-{i+1}-4")

        # j=5: 底部圆弧段（Bottom边取下半部分）
        bottom_edge_5 = edges.findAt((tuple(np.array((bottom_arc_center_x, y_arc_bot_lower, 0.0)) + np.array(origin)),))
        part.Set(edges=bottom_edge_5, name=f"Bottom-{i+1}-5")

        # j=6: 左侧直线段下半部分（内边界）
        bottom_edge_6 = edges.findAt((tuple(np.array((x_1 + l_1 + unit_x_offset, y_quarter_bot, 0.0)) + np.array(origin)),))
        part.Set(edges=bottom_edge_6, name=f"Bottom-{i+1}-6")

    # --------------- 创建合并的Top和Bottom集合 --------------- #
    # 收集所有Top边集合
    top_sets = tuple(part.sets[f"Top-{i+1}-{j}"] for i in range(m) for j in range(1, 7))
    part.SetByBoolean(name='Top', sets=top_sets)

    # 收集所有Bottom边集合
    bottom_sets = tuple(part.sets[f"Bottom-{i+1}-{j}"] for i in range(m) for j in range(1, 7))
    part.SetByBoolean(name='Bottom', sets=bottom_sets)

    # --------------- 定义材料 --------------- #
    model.Material(name="PI")
    model.materials["PI"].Elastic(table=((2500.0, 0.27),))

    model.Material(name="Cu")
    model.materials["Cu"].Elastic(table=((130000.0, 0.34),))

    # --------------- 创建复合层 --------------- #
    region = part.sets["All"]

    compositeLayup = part.CompositeLayup(
        name="CompositeLayup-1",
        description="PI-Cu-PI Sandwich",
        elementType=SHELL,
        offsetType=BOTTOM_SURFACE,
        symmetric=False,
        thicknessAssignment=FROM_SECTION,
    )

    compositeLayup.Section(
        preIntegrate=OFF,
        integrationRule=SIMPSON,
        thicknessType=UNIFORM,
        poissonDefinition=DEFAULT,
        temperature=GRADIENT,
        useDensity=OFF,
    )

    # 设置参考方向
    compositeLayup.ReferenceOrientation(
        orientationType=DISCRETE,
        localCsys=None,
        additionalRotationType=ROTATION_NONE,
        angle=0.0,
        additionalRotationField='',
        axis=AXIS_3,
        stackDirection=STACK_3,
        normalAxisDefinition=SURFACE,
        normalAxisRegion=part.surfaces['Top'],
        normalAxisDirection=AXIS_3,
        flipNormalDirection=False,
        primaryAxisDefinition=EDGE,
        primaryAxisRegion=part.sets['Bottom'],
        primaryAxisDirection=AXIS_1,
        flipPrimaryDirection=False
    )

    compositeLayup.suppress()

    # 底层聚酰亚胺 (第一层)
    compositeLayup.CompositePly(
        suppressed=False,
        plyName="PI-Bot",
        region=region,
        material="PI",
        thicknessType=SPECIFY_THICKNESS,
        thickness=pi_thickness,
        orientationType=SPECIFY_ORIENT,
        orientationValue=0.0,
        additionalRotationType=ROTATION_NONE,
        additionalRotationField="",
        axis=AXIS_3,
        angle=0.0,
        numIntPoints=3,
    )

    # 中层铜 (第二层)
    compositeLayup.CompositePly(
        suppressed=False,
        plyName="Cu",
        region=region,
        material="Cu",
        thicknessType=SPECIFY_THICKNESS,
        thickness=cu_thickness,
        orientationType=SPECIFY_ORIENT,
        orientationValue=0.0,
        additionalRotationType=ROTATION_NONE,
        additionalRotationField="",
        axis=AXIS_3,
        angle=0.0,
        numIntPoints=3,
    )

    # 顶层聚酰亚胺 (第三层)
    compositeLayup.CompositePly(
        suppressed=False,
        plyName="PI-Top",
        region=region,
        material="PI",
        thicknessType=SPECIFY_THICKNESS,
        thickness=pi_thickness,
        orientationType=SPECIFY_ORIENT,
        orientationValue=0.0,
        additionalRotationType=ROTATION_NONE,
        additionalRotationField="",
        axis=AXIS_3,
        angle=0.0,
        numIntPoints=3,
    )

    compositeLayup.resume()

    # --------------- 布种划分网格 --------------- #
    part.seedPart(size=wire_seed_size, deviationFactor=0.1, minSizeFactor=0.1)
    part.generateMesh()

    return part


def build_serpentine_wire_no_caps(
    modelname: str,
    partname: str,
    w: float = 0.05,
    l_1: float = 0.5,
    l_2: float = 0.5,
    m: int = 4,
    wire_seed_size: float = 0.005,
    pi_thickness: float = 0.003,
    cu_thickness: float = 0.0006,
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0),
):
    """
    创建无端盘的二维蛇形导线壳单元草图并生成 Part。

    Args:
        modelname (str): Abaqus 模型名称（mdb.models 的键）。
        partname (str): 生成的 Part 与草图名称。
        w (float): 蛇形导线带状线宽。
        l_1 (float): 一个完整周期沿 X 方向的宽度。
        l_2 (float): 竖直直线段长度。
        m (int): 周期数（完整周期个数）。
        wire_seed_size (float): 蛇形线布种尺寸。
        pi_thickness (float): PI 单层厚度（上下两层相同）。
        cu_thickness (float): Cu 单层厚度（中间层）。
        origin (tuple[float, float, float]): 草图原点坐标。

    Returns:
        Part: 创建好的 Part 对象。
    """
    try:
        model = mdb.models[modelname]
    except KeyError:
        model = mdb.Model(name=modelname)

    x_0: float = -w / 2
    x_1: float = x_0 + w
    x_2: float = x_0 + l_1 / 2.0
    x_3: float = x_2 + w

    y_mid: float = 0.0
    y_bot: float = y_mid - l_2 / 2.0
    y_top: float = y_mid + l_2 / 2.0

    x_inner_right: float = m * l_1 - w / 2
    x_outer_right: float = x_inner_right + w

    sk = model.ConstrainedSketch(
        name=partname,
        sheetSize=10.0,
        transform=(1, 0, 0, 0, 1, 0, 0, 0, 1) + origin,
    )

    line_0 = sk.Line(point1=(x_0, y_top), point2=(x_0, y_mid))
    line_1 = sk.Line(point1=(x_1, y_top), point2=(x_1, y_mid))
    line_2 = sk.Line(point1=(x_2, y_top), point2=(x_2, y_mid))
    line_3 = sk.Line(point1=(x_3, y_top), point2=(x_3, y_mid))

    arc_0 = sk.ArcByStartEndTangent(point1=(x_0, y_top), point2=(x_3, y_top), entity=line_0)
    arc_1 = sk.ArcByStartEndTangent(point1=(x_1, y_top), point2=(x_2, y_top), entity=line_1)

    half_objs = (line_0, line_1, line_2, line_3, arc_0, arc_1)

    rotate_center = ((x_2 + x_3) * 0.5, y_mid)
    sk.copyRotate(centerPoint=rotate_center, angle=180.0, objectList=half_objs)

    if m > 1:
        sk.linearPattern(
            geomList=sk.geometry.values(),
            number1=m,
            spacing1=l_1,
            angle1=0.0,
            number2=1,
            spacing2=l_1,
            angle2=90.0,
        )

    # 端部直线封闭（无圆盘）：在 origin 同一高度 y_mid 处封口
    # 左端：连接外左与内左
    sk.Line(point1=(x_0, y_mid), point2=(x_1, y_mid))
    # 右端：连接内右与外右
    sk.Line(point1=(x_inner_right, y_mid), point2=(x_outer_right, y_mid))

    part = model.Part(name=partname, dimensionality=THREE_D, type=DEFORMABLE_BODY)
    part.BaseShell(sketch=sk)

    f = part.faces
    part.Set(faces=f, name="All")
    part.Surface(side1Faces=f, name="Top")
    part.Surface(side2Faces=f, name="Bottom")

    v1 = part.vertices.findAt(tuple(np.array((x_0, y_top, 0)) + np.array(origin)))
    v2 = part.vertices.findAt(tuple(np.array((x_3 + (m - 1) * l_1, y_top, 0)) + np.array(origin)))
    part.PartitionFaceByShortestPath(point1=v1, point2=v2, faces=f)

    v3 = part.vertices.findAt(tuple(np.array((x_2, y_bot, 0)) + np.array(origin)))
    v4 = part.vertices.findAt(tuple(np.array((x_outer_right, y_bot, 0)) + np.array(origin)))
    part.PartitionFaceByShortestPath(point1=v3, point2=v4, faces=f)

    edges = part.edges

    for i in range(m):
        unit_x_offset = i * l_1

        arc_radius = l_1 / 4
        top_arc_center_x = l_1 / 4 + unit_x_offset
        bottom_arc_center_x = 3 * l_1 / 4 + unit_x_offset

        y_quarter_top = y_mid + l_2 / 4
        y_quarter_bot = y_mid - l_2 / 4

        y_arc_top_upper = y_top + arc_radius + w / 2
        y_arc_top_lower = y_top + arc_radius - w / 2
        y_arc_bot_upper = y_bot - arc_radius + w / 2
        y_arc_bot_lower = y_bot - arc_radius - w / 2

        top_edge_1 = edges.findAt((tuple(np.array((x_0 + unit_x_offset, y_quarter_top, 0.0)) + np.array(origin)),))
        part.Set(edges=top_edge_1, name=f"Top-{i+1}-1")

        top_edge_2 = edges.findAt((tuple(np.array((top_arc_center_x, y_arc_top_upper, 0.0)) + np.array(origin)),))
        part.Set(edges=top_edge_2, name=f"Top-{i+1}-2")

        top_edge_3 = edges.findAt((tuple(np.array((x_3 + unit_x_offset, y_quarter_top, 0.0)) + np.array(origin)),))
        part.Set(edges=top_edge_3, name=f"Top-{i+1}-3")

        top_edge_4 = edges.findAt((tuple(np.array((x_3 + unit_x_offset, y_quarter_bot, 0.0)) + np.array(origin)),))
        part.Set(edges=top_edge_4, name=f"Top-{i+1}-4")

        top_edge_5 = edges.findAt((tuple(np.array((bottom_arc_center_x, y_arc_bot_upper, 0.0)) + np.array(origin)),))
        part.Set(edges=top_edge_5, name=f"Top-{i+1}-5")

        top_edge_6 = edges.findAt((tuple(np.array((x_0 + l_1 + unit_x_offset, y_quarter_bot, 0.0)) + np.array(origin)),))
        part.Set(edges=top_edge_6, name=f"Top-{i+1}-6")

        bottom_edge_1 = edges.findAt((tuple(np.array((x_1 + unit_x_offset, y_quarter_top, 0.0)) + np.array(origin)),))
        part.Set(edges=bottom_edge_1, name=f"Bottom-{i+1}-1")

        bottom_edge_2 = edges.findAt((tuple(np.array((top_arc_center_x, y_arc_top_lower, 0.0)) + np.array(origin)),))
        part.Set(edges=bottom_edge_2, name=f"Bottom-{i+1}-2")

        bottom_edge_3 = edges.findAt((tuple(np.array((x_2 + unit_x_offset, y_quarter_top, 0.0)) + np.array(origin)),))
        part.Set(edges=bottom_edge_3, name=f"Bottom-{i+1}-3")

        bottom_edge_4 = edges.findAt((tuple(np.array((x_2 + unit_x_offset, y_quarter_bot, 0.0)) + np.array(origin)),))
        part.Set(edges=bottom_edge_4, name=f"Bottom-{i+1}-4")

        bottom_edge_5 = edges.findAt((tuple(np.array((bottom_arc_center_x, y_arc_bot_lower, 0.0)) + np.array(origin)),))
        part.Set(edges=bottom_edge_5, name=f"Bottom-{i+1}-5")

        bottom_edge_6 = edges.findAt((tuple(np.array((x_1 + l_1 + unit_x_offset, y_quarter_bot, 0.0)) + np.array(origin)),))
        part.Set(edges=bottom_edge_6, name=f"Bottom-{i+1}-6")

    top_sets = tuple(part.sets[f"Top-{i+1}-{j}"] for i in range(m) for j in range(1, 7))
    part.SetByBoolean(name="Top", sets=top_sets)

    bottom_sets = tuple(part.sets[f"Bottom-{i+1}-{j}"] for i in range(m) for j in range(1, 7))
    part.SetByBoolean(name="Bottom", sets=bottom_sets)

    model.Material(name="PI")
    model.materials["PI"].Elastic(table=((2500.0, 0.27),))

    model.Material(name="Cu")
    model.materials["Cu"].Elastic(table=((130000.0, 0.34),))

    region = part.sets["All"]

    compositeLayup = part.CompositeLayup(
        name="CompositeLayup-1",
        description="PI-Cu-PI Sandwich",
        elementType=SHELL,
        offsetType=BOTTOM_SURFACE,
        symmetric=False,
        thicknessAssignment=FROM_SECTION,
    )

    compositeLayup.Section(
        preIntegrate=OFF,
        integrationRule=SIMPSON,
        thicknessType=UNIFORM,
        poissonDefinition=DEFAULT,
        temperature=GRADIENT,
        useDensity=OFF,
    )

    compositeLayup.ReferenceOrientation(
        orientationType=DISCRETE,
        localCsys=None,
        additionalRotationType=ROTATION_NONE,
        angle=0.0,
        additionalRotationField="",
        axis=AXIS_3,
        stackDirection=STACK_3,
        normalAxisDefinition=SURFACE,
        normalAxisRegion=part.surfaces["Top"],
        normalAxisDirection=AXIS_3,
        flipNormalDirection=False,
        primaryAxisDefinition=EDGE,
        primaryAxisRegion=part.sets["Bottom"],
        primaryAxisDirection=AXIS_1,
        flipPrimaryDirection=False,
    )

    compositeLayup.suppress()

    compositeLayup.CompositePly(
        suppressed=False,
        plyName="PI-Bot",
        region=region,
        material="PI",
        thicknessType=SPECIFY_THICKNESS,
        thickness=pi_thickness,
        orientationType=SPECIFY_ORIENT,
        orientationValue=0.0,
        additionalRotationType=ROTATION_NONE,
        additionalRotationField="",
        axis=AXIS_3,
        angle=0.0,
        numIntPoints=3,
    )

    compositeLayup.CompositePly(
        suppressed=False,
        plyName="Cu",
        region=region,
        material="Cu",
        thicknessType=SPECIFY_THICKNESS,
        thickness=cu_thickness,
        orientationType=SPECIFY_ORIENT,
        orientationValue=0.0,
        additionalRotationType=ROTATION_NONE,
        additionalRotationField="",
        axis=AXIS_3,
        angle=0.0,
        numIntPoints=3,
    )

    compositeLayup.CompositePly(
        suppressed=False,
        plyName="PI-Top",
        region=region,
        material="PI",
        thicknessType=SPECIFY_THICKNESS,
        thickness=pi_thickness,
        orientationType=SPECIFY_ORIENT,
        orientationValue=0.0,
        additionalRotationType=ROTATION_NONE,
        additionalRotationField="",
        axis=AXIS_3,
        angle=0.0,
        numIntPoints=3,
    )

    compositeLayup.resume()

    part.seedPart(size=wire_seed_size, deviationFactor=0.1, minSizeFactor=0.1)
    part.generateMesh()

    return part



if __name__ == "__main__":
    # 这是一个用于在ABAQUS环境中调试 build_serpentine_wire 函数的测试脚本
    # 运行方式: abaqus python wire.py

    print("=" * 50)
    print("Testing build_serpentine_wire function...")

    # 1. 定义测试参数
    test_model_name = "WireTestModel"
    test_part_name = "TestWirePart"
    test_params = {
        "w": 0.05,
        "l_1": 0.5,
        "l_2": 0.5,
        "m": 4,
        "origin": (1.0, 1.0, 0.25),
    }

    print("\nParameters used for testing:")
    for key, value in test_params.items():
        print(f"  - {key}: {value}")

    # 2. 调用函数创建部件
    wire_part = build_serpentine_wire(
        modelname=test_model_name,
        partname=test_part_name,
        **test_params
    )
    print(f"\nSuccessfully created part '{wire_part.name}' in model '{test_model_name}'.")

    print("=" * 50)
