from __future__ import annotations

"""按分析步最后一帧提取路径 LE 数据并导出 CSV。

该脚本提供两个函数：
1) `extract_multi_step_last_frame_le_to_csv`：按指定分析步提取每步最后一帧
2) `extract_all_steps_last_frame_le_to_csv`：自动提取当前 ODB 全部分析步的最后一帧

宽表格式：
- 第一列：`x_coordinate`
- 后续列：`step_<步骤索引>`
"""

import csv
import math
from collections.abc import Iterable
from pathlib import Path

from abaqus import session

from abq_serp_sub.utils.abaqus_utils import current_display_info
from extract_path_le_xcoord import extract_path_le_xcoord_data

Point3D = tuple[float, float, float]


def _default_output_dir() -> Path:
    """返回默认输出目录：当前脚本同级 `data/`。"""
    file_path = globals().get("__file__")
    if file_path and not str(file_path).startswith("<"):
        return Path(file_path).resolve().parent / "data"
    return Path.cwd() / "data"


def _build_wide_table(
    step_curves: dict[int, list[tuple[float, float]]],
) -> tuple[list[float], dict[int, list[float]]]:
    """将多分析步曲线转换为宽表列结构。

    Args:
        step_curves (dict[int, list[tuple[float, float]]]): 键为步骤索引，值为 `(x, le)` 曲线。

    Returns:
        tuple[list[float], dict[int, list[float]]]: x 列与各步骤 LE 列映射。
    """
    sorted_steps = sorted(step_curves.keys())
    if not sorted_steps:
        raise ValueError("steps 不能为空。")

    first_curve = step_curves[sorted_steps[0]]
    x_values = [x_value for x_value, _ in first_curve]
    y_columns: dict[int, list[float]] = {
        sorted_steps[0]: [y_value for _, y_value in first_curve]
    }

    for step_index in sorted_steps[1:]:
        curve = step_curves[step_index]
        if len(curve) != len(x_values):
            raise ValueError(
                f"步骤 {step_index} 的数据点数量与参考步骤不一致："
                f"{len(curve)} != {len(x_values)}"
            )

        current_x = [x_value for x_value, _ in curve]
        if any(
            not math.isclose(x_ref, x_cur, rel_tol=1e-9, abs_tol=1e-9)
            for x_ref, x_cur in zip(x_values, current_x)
        ):
            raise ValueError(f"步骤 {step_index} 的 x 坐标与参考步骤不一致，无法直接拼成宽表。")

        y_columns[step_index] = [y_value for _, y_value in curve]

    return x_values, y_columns


def _write_wide_csv(
    csv_path: Path,
    x_values: list[float],
    step_columns: dict[int, list[float]],
) -> None:
    """将宽表写入 CSV。

    Args:
        csv_path (Path): 目标 CSV 文件路径。
        x_values (list[float]): x 坐标列。
        step_columns (dict[int, list[float]]): 各步骤对应的 LE 列。

    Returns:
        None: 仅执行文件写入。
    """
    sorted_steps = sorted(step_columns.keys())
    header = ["x_coordinate"] + [f"step_{step_index}" for step_index in sorted_steps]

    with csv_path.open("w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(header)

        for row_index, x_value in enumerate(x_values):
            row = [x_value] + [step_columns[step_index][row_index] for step_index in sorted_steps]
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
    column_prefix: str = "step",
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


def extract_multi_step_last_frame_le_to_csv(
    start_point: Point3D,
    end_point: Point3D,
    *,
    steps: Iterable[int | str],
    num_intervals: int = 100,
    viewport_name: str | None = None,
    output_dir: Path | str | None = None,
    path_name: str = "Path-LE-XCoord",
    wire_instance_name: str = "WIRE-1",
    substrate_instance_name: str = "SUBSTRATE-1",
    combine_parts: bool = True,
) -> dict[str, Path]:
    """按多个分析步提取“最后一帧”的路径 LE，并导出宽表 CSV。

    Args:
        start_point (Point3D): 路径起点 `(x, y, z)`。
        end_point (Point3D): 路径终点 `(x, y, z)`。
        steps (Iterable[int | str]): 要提取的分析步迭代器（索引或步骤名）。
        num_intervals (int): 路径等分间隔数量，默认 `100`。
        viewport_name (str | None): 视口名；为 `None` 时取当前激活视口。
        output_dir (Path | str | None): 输出目录；默认为当前脚本同级 `data/`。
        path_name (str): Abaqus Path 对象名称前缀。
        wire_instance_name (str): 导线实例名，默认 `WIRE-1`。
        substrate_instance_name (str): 基底实例名，默认 `SUBSTRATE-1`。
        combine_parts (bool): 为 `True` 时将 substrate 与 wire 合并导出到同一 CSV。

    Returns:
        dict[str, Path]: 默认返回 `{"sub": sub_csv_path, "wire": wire_csv_path}`；
            合并模式返回 `{"combined": combined_csv_path}`。
    """
    steps_list = list(steps)
    if not steps_list:
        raise ValueError("steps 不能为空。")

    sub_curves: dict[int, list[tuple[float, float]]] = {}
    wire_curves: dict[int, list[tuple[float, float]]] = {}
    model_name: str | None = None

    for step_item in steps_list:
        data = extract_path_le_xcoord_data(
            start_point=start_point,
            end_point=end_point,
            step=step_item,
            frame=None,
            num_intervals=num_intervals,
            viewport_name=viewport_name,
            path_name=path_name,
            wire_instance_name=wire_instance_name,
            substrate_instance_name=substrate_instance_name,
        )

        model_name = data["model_name"]
        step_index = data["step_index"]
        sub_curves[step_index] = data["sub"]
        wire_curves[step_index] = data["wire"]

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
            column_prefix="step",
        )
        return {"combined": combined_csv}

    sub_csv = output_path / f"{model_name}_sub_step_last.csv"
    wire_csv = output_path / f"{model_name}_wire_step_last.csv"

    _write_wide_csv(sub_csv, sub_x, sub_columns)
    _write_wide_csv(wire_csv, wire_x, wire_columns)

    return {"sub": sub_csv, "wire": wire_csv}


def extract_all_steps_last_frame_le_to_csv(
    start_point: Point3D,
    end_point: Point3D,
    *,
    num_intervals: int = 100,
    viewport_name: str | None = None,
    output_dir: Path | str | None = None,
    path_name: str = "Path-LE-XCoord",
    wire_instance_name: str = "WIRE-1",
    substrate_instance_name: str = "SUBSTRATE-1",
    combine_parts: bool = True,
) -> dict[str, Path]:
    """自动提取当前 ODB 全部分析步最后一帧的路径 LE，并导出宽表 CSV。

    Args:
        start_point (Point3D): 路径起点 `(x, y, z)`。
        end_point (Point3D): 路径终点 `(x, y, z)`。
        num_intervals (int): 路径等分间隔数量，默认 `100`。
        viewport_name (str | None): 视口名；为 `None` 时取当前激活视口。
        output_dir (Path | str | None): 输出目录；默认为当前脚本同级 `data/`。
        path_name (str): Abaqus Path 对象名称前缀。
        wire_instance_name (str): 导线实例名，默认 `WIRE-1`。
        substrate_instance_name (str): 基底实例名，默认 `SUBSTRATE-1`。
        combine_parts (bool): 为 `True` 时将 substrate 与 wire 合并导出到同一 CSV。

    Returns:
        dict[str, Path]: 默认返回 `{"sub": sub_csv_path, "wire": wire_csv_path}`；
            合并模式返回 `{"combined": combined_csv_path}`。
    """
    info = current_display_info(viewport_name=viewport_name)
    if info["kind"] != "ODB":
        raise RuntimeError("当前视口未显示 ODB，请先在视口中显示目标 ODB。")

    target_viewport_name = info["viewport"]
    viewport = session.viewports[target_viewport_name]
    odb = viewport.displayedObject

    step_names = list(odb.steps.keys())
    if not step_names:
        raise RuntimeError("当前 ODB 不包含分析步。")

    return extract_multi_step_last_frame_le_to_csv(
        start_point=start_point,
        end_point=end_point,
        steps=step_names,
        num_intervals=num_intervals,
        viewport_name=viewport_name,
        output_dir=output_dir,
        path_name=path_name,
        wire_instance_name=wire_instance_name,
        substrate_instance_name=substrate_instance_name,
        combine_parts=combine_parts,
    )
