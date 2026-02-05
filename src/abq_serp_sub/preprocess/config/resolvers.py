"""
OmegaConf 自定义 Resolver

用于配置文件中的派生值计算。

使用示例:
    n_cols: ${imul:${substrate.n_rows},2}    # = n_rows * 2
    square_size: ${div:2,${substrate.n_rows}}  # = 2 / n_rows

注意: 必须在 Hydra 初始化之前调用 register_resolvers()
"""
from omegaconf import OmegaConf


def register_resolvers() -> None:
    """注册所有自定义 OmegaConf resolver"""

    # region 乘法

    # 整数乘法: ${imul:${a},2} -> int(a * 2)
    OmegaConf.register_new_resolver(
        "imul",
        lambda x, y: int(float(x) * float(y)),
        replace=True,
    )

    # 浮点乘法: ${mul:${a},2} -> a * 2
    OmegaConf.register_new_resolver(
        "mul",
        lambda x, y: float(x) * float(y),
        replace=True,
    )

    # endregion

    # region 除法

    # 除法: ${div:${a},2} -> a / 2
    OmegaConf.register_new_resolver(
        "div",
        lambda x, y: float(x) / float(y),
        replace=True,
    )

    # 整除: ${idiv:${a},2} -> int(a // 2)
    OmegaConf.register_new_resolver(
        "idiv",
        lambda x, y: int(float(x) // float(y)),
        replace=True,
    )

    # endregion

    # region 加减法

    # 加法: ${add:${a},1} -> a + 1
    OmegaConf.register_new_resolver(
        "add",
        lambda x, y: float(x) + float(y),
        replace=True,
    )

    # 减法: ${sub:${a},1} -> a - 1
    OmegaConf.register_new_resolver(
        "sub",
        lambda x, y: float(x) - float(y),
        replace=True,
    )

    # endregion
