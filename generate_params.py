"""
参数生成脚本

使用 Hydra + hydra-list-sweeper 生成参数 JSON 文件。

使用方法:
    uv run python generate_params.py --multirun

运行后会弹出文件选择对话框，选择 YAML 配置文件。

输出:
    params/<NNN>_<modelname>.json
    params/_index.md                  （参数索引表，供人工审阅记录）
"""
import atexit
import json
import sys
from datetime import datetime
from pathlib import Path

import hydra
from omegaconf import DictConfig, OmegaConf
from pydantic import ValidationError

from abq_serp_sub.preprocess.config.resolvers import register_resolvers
from abq_serp_sub.preprocess.config.models import Config
from abq_serp_sub.utils.common_utils import select_files

# 注册自定义 resolver（必须在 @hydra.main 之前）
register_resolvers()

# 输出目录（基于启动命令时的当前工作目录）
# 这样在不同运行目录执行时，参数文件会落在对应目录下的 params/。
PARAMS_DIR = Path.cwd() / "params"

# ---------------------------------------------------------------------------
# 运行计数器 & 索引收集
# Hydra multirun 在同一进程内多次调用 main()，因此模块级变量可跨调用共享
# ---------------------------------------------------------------------------
_run_counter: int = 0
_run_registry: list[dict] = []


def _next_run_number() -> int:
    """返回下一个递增编号（从 1 开始）。"""
    global _run_counter
    _run_counter += 1
    return _run_counter


def _extract_key_params(config: Config) -> dict[str, str]:
    """从 Config 中提取关键参数，用于索引表展示。"""
    params: dict[str, str] = {}

    # 基底参数
    params["elem_code"] = config.substrate.elem_code
    params["seed_size"] = str(config.substrate.seed_size)

    # Cohesive 参数
    if config.interaction.cohesive:
        coh = config.interaction.cohesive
        params["Knn"] = str(coh.stiffness_normal)
        params["σ_max"] = str(coh.max_stress_normal)
        params["Gc"] = str(coh.fracture_energy)

    # 分析步类型
    if config.steps:
        params["step_type"] = config.steps[0].step_type.value

    return params


def _generate_index_md() -> None:
    """生成 Markdown 索引文件。在所有 Hydra 多次运行结束后调用。"""
    if not _run_registry:
        return

    index_path = PARAMS_DIR / "_index.md"

    # 收集所有出现过的参数列名（保持插入顺序）
    all_param_keys: list[str] = []
    for entry in _run_registry:
        for k in entry["params"]:
            if k not in all_param_keys:
                all_param_keys.append(k)

    # 构建 Markdown
    lines: list[str] = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines.append(f"# 参数索引表")
    lines.append(f"")
    lines.append(f"> 生成时间: {timestamp}  ")
    lines.append(f"> 共 {len(_run_registry)} 组参数")
    lines.append(f"")

    # 表头
    header_cols = ["编号", "模型名称"] + all_param_keys + ["审阅备注"]
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("| " + " | ".join(["---"] * len(header_cols)) + " |")

    # 表体
    for entry in _run_registry:
        num = entry["number"]
        name = entry["modelname"]
        param_cells = [entry["params"].get(k, "-") for k in all_param_keys]
        row = [f"{num:03d}", f"`{name}`"] + param_cells + [""]
        lines.append("| " + " | ".join(row) + " |")

    lines.append("")

    index_path.parent.mkdir(parents=True, exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n📋 索引文件已生成: {index_path}")


# 注册退出钩子，确保在所有 main() 调用结束后生成索引
atexit.register(_generate_index_md)


def _has_hydra_config_override(args: list[str]) -> bool:
    """检测是否已显式传入 Hydra 配置路径参数。"""
    return (
        "--config-path" in args
        or "--config-name" in args
        or any(arg.startswith("--config-path=") for arg in args)
        or any(arg.startswith("--config-name=") for arg in args)
    )


def _inject_selected_config(args: list[str], selected_config: str) -> list[str]:
    """将选中的配置文件路径转换为 Hydra CLI 参数。"""
    config_path = Path(selected_config).resolve()
    return args + [
        "--config-path",
        str(config_path.parent),
        "--config-name",
        config_path.stem,
    ]


def _prepare_cli_args(argv: list[str]) -> list[str]:
    """
    处理 CLI 参数。

    如果用户没有通过 --config-path/--config-name 指定配置文件，
    则弹出文件选择对话框让用户选择 YAML 配置文件。
    """
    args = argv[1:]

    # 如果用户已经手动指定了配置路径，直接使用
    if _has_hydra_config_override(args):
        return argv

    # 弹出文件选择对话框
    default_conf_dir = Path(__file__).parent / "conf"
    initialdir = str(default_conf_dir if default_conf_dir.exists() else Path.cwd())
    selected = select_files(
        title="选择参数配置文件",
        filetypes=[("YAML 文件", "*.yaml *.yml"), ("所有文件", "*.*")],
        multiple=False,
        initialdir=initialdir,
    )

    if not selected:
        raise SystemExit("未选择配置文件，已取消参数生成")

    return [argv[0]] + _inject_selected_config(args, selected)


@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(cfg: DictConfig) -> None:
    """
    Hydra 入口函数。
    """
    # 1. 解析所有 resolver + Pydantic 类型验证（modelname 自动生成）
    cfg_dict = OmegaConf.to_container(cfg, resolve=True)

    # Pydantic 模型已配置 extra="ignore"，自动忽略 hydra 内部配置
    try:
        config = Config(**cfg_dict)
    except ValidationError as e:
        print(f"配置验证失败:\n{e}")
        return

    # 2. 添加编号前缀
    run_num = _next_run_number()
    numbered_name = f"{run_num:03d}_{config.modelname}"
    config.modelname = numbered_name

    # 3. 序列化为 JSON
    output_file = PARAMS_DIR / f"{numbered_name}.json"

    # 确保输出目录存在
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(config.model_dump(), f, indent=2, ensure_ascii=False)

    # 4. 收集到索引注册表
    _run_registry.append({
        "number": run_num,
        "modelname": numbered_name,
        "params": _extract_key_params(config),
    })

    print(f"✓ [{run_num:03d}] 生成参数文件: {output_file.name}")


if __name__ == "__main__":
    try:
        sys.argv = _prepare_cli_args(sys.argv)
    except ValueError as e:
        raise SystemExit(f"参数错误: {e}")
    main()

