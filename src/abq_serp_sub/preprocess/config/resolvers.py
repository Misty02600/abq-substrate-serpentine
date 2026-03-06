"""
OmegaConf 自定义 Resolver

用于配置文件中的派生值计算。

使用示例:
    n_cols: ${imul:${substrate.n_rows},2}    # = n_rows * 2
    square_size: ${div:2,${substrate.n_rows}}  # = 2 / n_rows
    values: ${range:1,10,2}                    # = [1, 3, 5, 7, 9] (自动识别整数)
    sweeper_str: ${sweep:0.1,1.0,0.2}          # = "0.1,0.3,0.5,0.7,0.9" (逗号分隔)

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

    # region 列表生成
    # endregion

    # region 列表生成 (自动识别整数/浮点)

    def _generate_sequence(start, stop, step):
        """生成数值序列，自动处理整数格式"""
        current = float(start)
        stop_val = float(stop)
        step_val = float(step)
        result = []

        # 简单的浮点误差处理
        epsilon = 1e-10

        while (step_val > 0 and current < stop_val - epsilon) or \
              (step_val < 0 and current > stop_val + epsilon):

            val = round(current, 10)
            # 如果是整数（如 1.0），转为 int（1）；否则保留 float
            if val.is_integer():
                result.append(int(val))
            else:
                result.append(val)
            current += step_val

        return result

    # 通用范围: ${range:1,10,2} -> [1, 3, 5...] / ${range:0.1,1.0,0.2} -> [0.1, 0.3...]
    def range_resolver(start, stop, step=1):
        return _generate_sequence(start, stop, step)

    OmegaConf.register_new_resolver("range", range_resolver, replace=True)

    # 通用 Sweeper: ${sweep:1,4,1} -> "1,2,3" / ${sweep:0.1,0.3,0.1} -> "0.1,0.2"
    def sweep_resolver(start, stop, step=1):
        values = _generate_sequence(start, stop, step)
        return ",".join(str(v) for v in values)

    OmegaConf.register_new_resolver("sweep", sweep_resolver, replace=True)

    # 逗号分隔列表: ${list:1,2,3} -> "1,2,3"
    def list_resolver(*args):
        return ",".join(str(x) for x in args)

    OmegaConf.register_new_resolver("list", list_resolver, replace=True)

    # 兼容旧名称（可选，防止现有配置报错，或直接移除）
    OmegaConf.register_new_resolver("irange", range_resolver, replace=True)
    OmegaConf.register_new_resolver("frange", range_resolver, replace=True)
    OmegaConf.register_new_resolver("isweep", sweep_resolver, replace=True)

    # endregion
