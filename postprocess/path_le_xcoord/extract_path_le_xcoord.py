from __future__ import annotations

"""路径 LE 提取脚本（横坐标为 X 坐标）。

该脚本面向 Abaqus/CAE 当前视口中正在显示的 ODB，按给定路径端点提取：
- `SUBSTRATE-1` 上的 LE 曲线
- `WIRE-1` 上的 LE 曲线

支持两层函数：
1) 仅提取数据（单帧）
2) 多帧聚合并导出 CSV（宽表）

宽表格式：
- 第一列：`x_coordinate`
- 后续列：`frame_<帧号>`

典型调用：
    start_pt, end_pt = make_horizontal_endpoints(0.0, 8.0, 9.5, 0.6)
    csv_map = extract_multi_frame_le_to_csv(
        start_point=start_pt,
        end_point=end_pt,
        step="Step-1",
        frames=[35, 52],
    )
"""

import csv
import math
from collections.abc import Iterable
from pathlib import Path

import displayGroupOdbToolset as dgo
from abaqus import session
from abaqusConstants import (
    CONTOURS_ON_UNDEF,
    DEFAULT_MODEL,
    INTEGRATION_POINT,
    INVARIANT,
    POINT_LIST,
    UNDEFORMED,
    UNIFORM_SPACING,
    X_COORDINATE,
)

from abq_serp_sub.utils.abaqus_utils import current_display_info

Point3D = tuple[float, float, float]


def _default_output_dir() -> Path:
    """返回默认输出目录：当前脚本同级 `data/`。"""
    file_path = globals().get("__file__")
    if file_path and not str(file_path).startswith("<"):
        return Path(file_path).resolve().parent / "data"
    return Path.cwd() / "data"


def _as_y_list(y_values: float | Iterable[float]) -> list[float]:
    """将单个或多个 y 值规范化为列表。"""
    if isinstance(y_values, (int, float)):
        return [float(y_values)]
    values = [float(y_value) for y_value in y_values]
    if not values:
        raise ValueError("y_values 不能为空。")
    return values


def _float_tag(value: float) -> str:
    """将浮点数转换为适合文件名的字符串。"""
    return f"{value:.6g}".replace("-", "m").replace(".", "p")


def make_horizontal_endpoints(
    x_start: float,
    x_end: float,
    y_value: float,
    z_value: float,
) -> tuple[Point3D, Point3D]:
    """构造位于同一高度的水平路径端点。

    Args:
        x_start (float): 起点 x 坐标。
        x_end (float): 终点 x 坐标。
        y_value (float): 水平线 y 坐标（两端点共用）。
        z_value (float): 水平线 z 坐标（两端点共用，通常为基底上表面）。

    Returns:
        tuple[Point3D, Point3D]: `(start_point, end_point)` 两个三维端点。
    """
    start_point: Point3D = (x_start, y_value, z_value)
    end_point: Point3D = (x_end, y_value, z_value)
    return start_point, end_point


def _resolve_step_and_frame(odb, step: int | str, frame: int | None) -> tuple[int, int]:
    """将 step/frame 参数规范化为索引。"""
    step_names = list(odb.steps.keys())

    if isinstance(step, str):
        if step not in step_names:
            raise ValueError(f"未找到步骤 '{step}'，可用步骤: {step_names}")
        step_index = step_names.index(step)
    else:
        if step < 0 or step >= len(step_names):
            raise ValueError(f"step 索引 {step} 超出范围，当前步骤数: {len(step_names)}")
        step_index = step

    step_name = step_names[step_index]
    frame_count = len(odb.steps[step_name].frames)

    if frame is None:
        frame_index = frame_count - 1
    else:
        if frame < 0 or frame >= frame_count:
            raise ValueError(
                f"frame 索引 {frame} 超出范围，步骤 '{step_name}' 帧数: {frame_count}"
            )
        frame_index = frame

    return step_index, frame_index


def _extract_part_curve(
    viewport,
    path,
    part_instance_name: str,
    xy_name: str,
    step_index: int,
    frame_index: int,
    num_intervals: int,
) -> list[tuple[float, float]]:
    """提取指定部件实例沿路径的 LE 数据。"""
    leaf = dgo.LeafFromPartInstance(partInstanceName=(part_instance_name,))
    viewport.odbDisplay.displayGroup.replace(leaf=leaf)

    xy_data = session.XYDataFromPath(
        name=xy_name,
        path=path,
        includeIntersections=True,
        projectOntoMesh=False,
        pathStyle=UNIFORM_SPACING,
        numIntervals=num_intervals,
        projectionTolerance=0,
        shape=UNDEFORMED,
        labelType=X_COORDINATE,
        removeDuplicateXYPairs=True,
        includeAllElements=False,
        step=step_index,
        frame=frame_index,
    )

    return [(float(x_value), float(le_value)) for x_value, le_value in xy_data.data]


def extract_path_le_xcoord_data(
    start_point: Point3D,
    end_point: Point3D,
    *,
    step: int | str = 0,
    frame: int | None = 0,
    num_intervals: int = 100,
    viewport_name: str | None = None,
    path_name: str = "Path-LE-XCoord",
    wire_instance_name: str = "WIRE-1",
    substrate_instance_name: str = "SUBSTRATE-1",
) -> dict[str, object]:
    """提取当前展示模型中指定帧的路径 LE 数据（不写文件）。

    Args:
        start_point (Point3D): 路径起点 `(x, y, z)`。
        end_point (Point3D): 路径终点 `(x, y, z)`。
        step (int | str): 分析步索引或步骤名，默认 `0`。
        frame (int | None): 帧索引；为 `None` 时自动取该分析步最后一帧。
        num_intervals (int): 路径等分间隔数量，默认 `100`。
        viewport_name (str | None): 视口名；为 `None` 时取当前激活视口。
        path_name (str): Abaqus Path 对象名称。
        wire_instance_name (str): 导线实例名，默认 `WIRE-1`。
        substrate_instance_name (str): 基底实例名，默认 `SUBSTRATE-1`。

    Returns:
        dict[str, object]: 包含模型名、步/帧索引以及 `sub`/`wire` 曲线数据。
    """
    info = current_display_info(viewport_name=viewport_name)
    if info["kind"] != "ODB":
        raise RuntimeError("当前视口未显示 ODB，请先在视口中显示目标 ODB。")

    target_viewport_name = info["viewport"]
    model_name = info["model_name"]
    if not model_name:
        raise RuntimeError("无法从当前显示 ODB 解析模型名。")

    viewport = session.viewports[target_viewport_name]
    odb = viewport.displayedObject

    step_index, frame_index = _resolve_step_and_frame(odb=odb, step=step, frame=frame)

    viewport.odbDisplay.display.setValues(plotState=(CONTOURS_ON_UNDEF,))
    viewport.odbDisplay.setPrimaryVariable(
        variableLabel="LE",
        outputPosition=INTEGRATION_POINT,
        refinement=(INVARIANT, "Max. Principal"),
    )

    path = session.Path(
        name=path_name,
        type=POINT_LIST,
        expression=(start_point, end_point),
    )

    y_coord = start_point[1]
    y_tag = _float_tag(y_coord)

    substrate_curve = _extract_part_curve(
        viewport=viewport,
        path=path,
        part_instance_name=substrate_instance_name,
        xy_name=f"{model_name}_sub_y{y_tag}_s{step_index}_f{frame_index}",
        step_index=step_index,
        frame_index=frame_index,
        num_intervals=num_intervals,
    )

    leaf_default = dgo.Leaf(leafType=DEFAULT_MODEL)
    viewport.odbDisplay.displayGroup.either(leaf=leaf_default)

    wire_curve = _extract_part_curve(
        viewport=viewport,
        path=path,
        part_instance_name=wire_instance_name,
        xy_name=f"{model_name}_wire_y{y_tag}_s{step_index}_f{frame_index}",
        step_index=step_index,
        frame_index=frame_index,
        num_intervals=num_intervals,
    )

    viewport.odbDisplay.displayGroup.either(leaf=leaf_default)

    return {
        "model_name": model_name,
        "step_index": step_index,
        "frame_index": frame_index,
        "sub": substrate_curve,
        "wire": wire_curve,
    }


def _build_wide_table(
    frame_curves: dict[int, list[tuple[float, float]]],
) -> tuple[list[float], dict[int, list[float]]]:
    """将多帧曲线转换为宽表列结构。"""
    sorted_frames = sorted(frame_curves.keys())
    if not sorted_frames:
        raise ValueError("frames 不能为空。")

    first_curve = frame_curves[sorted_frames[0]]
    x_values = [x_value for x_value, _ in first_curve]
    y_columns: dict[int, list[float]] = {
        sorted_frames[0]: [y_value for _, y_value in first_curve]
    }

    for frame_index in sorted_frames[1:]:
        curve = frame_curves[frame_index]
        if len(curve) != len(x_values):
            raise ValueError(
                f"帧 {frame_index} 的数据点数量与参考帧不一致："
                f"{len(curve)} != {len(x_values)}"
            )

        current_x = [x_value for x_value, _ in curve]
        if any(not math.isclose(x_ref, x_cur, rel_tol=1e-9, abs_tol=1e-9)
               for x_ref, x_cur in zip(x_values, current_x)):
            raise ValueError(f"帧 {frame_index} 的 x 坐标与参考帧不一致，无法直接拼成宽表。")

        y_columns[frame_index] = [y_value for _, y_value in curve]

    return x_values, y_columns


def _write_wide_csv(
    csv_path: Path,
    x_values: list[float],
    frame_columns: dict[int, list[float]],
    *,
    column_prefix: str = "frame",
) -> None:
    """将宽表写入 CSV。"""
    sorted_frames = sorted(frame_columns.keys())
    header = ["x_coordinate"] + [f"{column_prefix}_{frame_index}" for frame_index in sorted_frames]

    with csv_path.open("w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(header)

        for row_index, x_value in enumerate(x_values):
            row = [x_value] + [frame_columns[frame_index][row_index] for frame_index in sorted_frames]
            writer.writerow(row)


def _merge_x_axis(sub_x: list[float], wire_x: list[float]) -> list[float]:
    """合并 sub/wire 的 x 轴（按并集，近似相等点去重）。"""
    merged: list[float] = []
    all_x = sorted(sub_x + wire_x)
    for x_value in all_x:
        if not merged or not math.isclose(merged[-1], x_value, rel_tol=1e-9, abs_tol=1e-9):
            merged.append(x_value)
    return merged


def _project_values_to_axis(
    source_x: list[float],
    source_values: list[float],
    target_x: list[float],
) -> list[float]:
    """将源曲线值投影到目标 x 轴，未命中位置留 NaN。"""
    projected: list[float] = []
    for target in target_x:
        found = float('nan')
        for x_value, y_value in zip(source_x, source_values):
            if math.isclose(x_value, target, rel_tol=1e-9, abs_tol=1e-9):
                found = y_value
                break
        projected.append(found)
    return projected


def _write_combined_parts_wide_csv(
    csv_path: Path,
    sub_x: list[float],
    wire_x: list[float],
    sub_columns: dict[int, list[float]],
    wire_columns: dict[int, list[float]],
    *,
    column_prefix: str = "frame",
) -> None:
    """将 substrate 与 wire 合并写入一个宽表 CSV。"""
    sub_keys = sorted(sub_columns.keys())
    wire_keys = sorted(wire_columns.keys())
    if sub_keys != wire_keys:
        raise ValueError("sub 与 wire 的列键不一致，无法合并到同一个宽表文件。")

    merged_x = _merge_x_axis(sub_x, wire_x)

    header = ["x_coordinate"]
    header += [f"sub_{column_prefix}_{key}" for key in sub_keys]
    header += [f"wire_{column_prefix}_{key}" for key in wire_keys]

    with csv_path.open("w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(header)

        sub_projected = {
            key: _project_values_to_axis(sub_x, sub_columns[key], merged_x)
            for key in sub_keys
        }
        wire_projected = {
            key: _project_values_to_axis(wire_x, wire_columns[key], merged_x)
            for key in wire_keys
        }

        for row_index, x_value in enumerate(merged_x):
            row = [x_value]
            row += [sub_projected[key][row_index] for key in sub_keys]
            row += [wire_projected[key][row_index] for key in wire_keys]
            writer.writerow(row)


def extract_multi_frame_le_to_csv(
    start_point: Point3D,
    end_point: Point3D,
    *,
    frames: Iterable[int],
    step: int | str = 0,
    num_intervals: int = 100,
    viewport_name: str | None = None,
    output_dir: Path | str | None = None,
    path_name: str = "Path-LE-XCoord",
    wire_instance_name: str = "WIRE-1",
    substrate_instance_name: str = "SUBSTRATE-1",
    combine_parts: bool = True,
) -> dict[str, Path]:
    """提取多个帧并保存为宽表 CSV（首列 x，后续列为各帧 LE）。

    Args:
        start_point (Point3D): 路径起点 `(x, y, z)`。
        end_point (Point3D): 路径终点 `(x, y, z)`。
        frames (Iterable[int]): 要提取的帧索引迭代器（列表、生成器、range等）。
        step (int | str): 分析步索引或步骤名，默认 `0`。
        num_intervals (int): 路径等分间隔数量，默认 `100`。
        viewport_name (str | None): 视口名；为 `None` 时取当前激活视口。
        output_dir (Path | str | None): 输出目录；默认为当前脚本同级 `data/`。
        path_name (str): Abaqus Path 对象名称。
        wire_instance_name (str): 导线实例名，默认 `WIRE-1`。
        substrate_instance_name (str): 基底实例名，默认 `SUBSTRATE-1`。
        combine_parts (bool): 为 `True` 时将 substrate 与 wire 合并导出到同一 CSV。

    Returns:
        dict[str, Path]: 默认返回 `{"sub": sub_csv_path, "wire": wire_csv_path}`；
            合并模式返回 `{"combined": combined_csv_path}`。
    """
    frames_list = list(frames)
    if not frames_list:
        raise ValueError("frames 不能为空。")

    sub_curves: dict[int, list[tuple[float, float]]] = {}
    wire_curves: dict[int, list[tuple[float, float]]] = {}
    model_name: str | None = None

    for frame_index in frames_list:
        data = extract_path_le_xcoord_data(
            start_point=start_point,
            end_point=end_point,
            step=step,
            frame=frame_index,
            num_intervals=num_intervals,
            viewport_name=viewport_name,
            path_name=path_name,
            wire_instance_name=wire_instance_name,
            substrate_instance_name=substrate_instance_name,
        )

        model_name = data["model_name"]
        sub_curves[frame_index] = data["sub"]
        wire_curves[frame_index] = data["wire"]

    assert model_name is not None

    sub_x, sub_columns = _build_wide_table(sub_curves)
    wire_x, wire_columns = _build_wide_table(wire_curves)

    output_path = Path(output_dir) if output_dir else _default_output_dir()
    output_path.mkdir(parents=True, exist_ok=True)

    if combine_parts:
        combined_csv = output_path / f"{model_name}.csv"
        _write_combined_parts_wide_csv(
            combined_csv,
            sub_x,
            wire_x,
            sub_columns,
            wire_columns,
            column_prefix="frame",
        )
        return {"combined": combined_csv}

    sub_csv = output_path / f"{model_name}_sub.csv"
    wire_csv = output_path / f"{model_name}_wire.csv"

    _write_wide_csv(sub_csv, sub_x, sub_columns, column_prefix="frame")
    _write_wide_csv(wire_csv, wire_x, wire_columns, column_prefix="frame")

    return {"sub": sub_csv, "wire": wire_csv}


def extract_multi_y_multi_frame_le_to_csv(
    x_start: float,
    x_end: float,
    y_values: float | Iterable[float],
    z_value: float,
    *,
    frames: Iterable[int],
    step: int | str = 0,
    num_intervals: int = 100,
    viewport_name: str | None = None,
    output_dir: Path | str | None = None,
    path_name: str = "Path-LE-XCoord",
    wire_instance_name: str = "WIRE-1",
    substrate_instance_name: str = "SUBSTRATE-1",
    combine_parts: bool = True,
) -> dict[str, Path]:
    """按单个或多个 y 值提取多帧 LE，并汇总到一个 CSV。

    Args:
        x_start (float): 路径起点 x 坐标。
        x_end (float): 路径终点 x 坐标。
        y_values (float | Iterable[float]): 单个 y 或多个 y 值。
        z_value (float): 路径 z 坐标。
        frames (Iterable[int]): 要提取的帧索引迭代器。
        step (int | str): 分析步索引或步骤名，默认 `0`。
        num_intervals (int): 路径等分间隔数量，默认 `100`。
        viewport_name (str | None): 视口名；为 `None` 时取当前激活视口。
        output_dir (Path | str | None): 输出目录；默认为当前脚本同级 `data/`。
        path_name (str): Abaqus Path 对象名称。
        wire_instance_name (str): 导线实例名，默认 `WIRE-1`。
        substrate_instance_name (str): 基底实例名，默认 `SUBSTRATE-1`。
        combine_parts (bool): 为 `True` 时在单个 CSV 中同时包含 sub 与 wire 列。

    Returns:
        dict[str, Path]: `{"combined": csv_path}` 或 `{"single": csv_path}`。
    """
    frames_list = list(frames)
    if not frames_list:
        raise ValueError("frames 不能为空。")

    y_list = _as_y_list(y_values)
    sorted_frames = sorted(frames_list)
    output_path = Path(output_dir) if output_dir else _default_output_dir()
    output_path.mkdir(parents=True, exist_ok=True)

    rows: list[list[float]] = []
    model_name: str | None = None

    for y_value in y_list:
        start_point, end_point = make_horizontal_endpoints(
            x_start=x_start,
            x_end=x_end,
            y_value=y_value,
            z_value=z_value,
        )

        sub_curves: dict[int, list[tuple[float, float]]] = {}
        wire_curves: dict[int, list[tuple[float, float]]] = {}

        for frame_index in frames_list:
            data = extract_path_le_xcoord_data(
                start_point=start_point,
                end_point=end_point,
                step=step,
                frame=frame_index,
                num_intervals=num_intervals,
                viewport_name=viewport_name,
                path_name=path_name,
                wire_instance_name=wire_instance_name,
                substrate_instance_name=substrate_instance_name,
            )
            model_name = data["model_name"]
            sub_curves[frame_index] = data["sub"]
            wire_curves[frame_index] = data["wire"]

        sub_x, sub_columns = _build_wide_table(sub_curves)
        wire_x, wire_columns = _build_wide_table(wire_curves)
        merged_x = _merge_x_axis(sub_x, wire_x)

        sub_projected = {
            frame_index: _project_values_to_axis(sub_x, sub_columns[frame_index], merged_x)
            for frame_index in sorted_frames
        }
        wire_projected = {
            frame_index: _project_values_to_axis(wire_x, wire_columns[frame_index], merged_x)
            for frame_index in sorted_frames
        }

        for row_index, x_value in enumerate(merged_x):
            row: list[float | str] = [y_value, x_value]
            row += [sub_projected[frame_index][row_index] for frame_index in sorted_frames]
            if combine_parts:
                row += [wire_projected[frame_index][row_index] for frame_index in sorted_frames]
            rows.append(row)

    assert model_name is not None

    if len(y_list) == 1:
        y_tag = _float_tag(y_list[0])
    else:
        y_tag = f"multi_{len(y_list)}"

    if combine_parts:
        csv_path = output_path / f"{model_name}.csv"
        header = ["y_coordinate", "x_coordinate"]
        header += [f"sub_frame_{frame_index}" for frame_index in sorted_frames]
        header += [f"wire_frame_{frame_index}" for frame_index in sorted_frames]
        key = "combined"
    else:
        csv_path = output_path / f"{model_name}_sub.csv"
        header = ["y_coordinate", "x_coordinate"]
        header += [f"sub_frame_{frame_index}" for frame_index in sorted_frames]
        key = "single"

    with csv_path.open("w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(header)
        writer.writerows(rows)

    return {key: csv_path}


if __name__ == "__main__":
    # default_start, default_end = make_horizontal_endpoints(
    #     x_start=0.0,
    #     x_end=8.0,
    #     y_value=9.5,
    #     z_value=0.6,
    # )

    # csv_files = extract_multi_frame_le_to_csv(
    #     start_point=default_start,
    #     end_point=default_end,
    #     step="Step-1",
    #     frames=range(10, 350, 35),
    #     combine_parts=True,
    # )

    # print("导出完成:", csv_files)

    csv_multi_y = extract_multi_y_multi_frame_le_to_csv(
        x_start=0.0,
        x_end=8.0,
        y_values=[5, 9.5],
        z_value=0.6,
        step="Step-1",
        frames=range(10, 350, 35),
        combine_parts=True,
    )
    print("多y导出完成:", csv_multi_y)
