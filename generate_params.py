"""
参数生成脚本

使用 Hydra + hydra-list-sweeper 生成参数 JSON 文件。

使用方法:
    uv run python generate_params.py --multirun

输出:
    params/<modelname>.json
"""
import json
from pathlib import Path

import hydra
from omegaconf import DictConfig, OmegaConf
from pydantic import ValidationError

from abq_serp_sub.config.resolvers import register_resolvers
from abq_serp_sub.config.models import Config

# 注册自定义 resolver（必须在 @hydra.main 之前）
register_resolvers()

# 输出目录
PARAMS_DIR = Path(__file__).parent / "params"


@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(cfg: DictConfig) -> None:
    """
    Hydra 入口函数。

    在 multirun 模式下，每个参数组合会调用一次此函数。
    """
    # 1. 解析所有 resolver + Pydantic 类型验证（modelname 自动生成）
    cfg_dict = OmegaConf.to_container(cfg, resolve=True)

    # Pydantic 模型已配置 extra="ignore"，自动忽略 hydra 内部配置
    try:
        config = Config(**cfg_dict)
    except ValidationError as e:
        print(f"配置验证失败:\n{e}")
        return

    # 2. 序列化为 JSON
    output_file = PARAMS_DIR / f"{config.modelname}.json"

    # 确保输出目录存在
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(config.model_dump(), f, indent=2, ensure_ascii=False)

    print(f"✓ 生成参数文件: {output_file.name}")


if __name__ == "__main__":
    main()
