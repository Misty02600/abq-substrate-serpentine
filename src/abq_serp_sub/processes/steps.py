"""分析步创建模块"""

from typing import TYPE_CHECKING

from abaqusConstants import (
    ON, OFF, DEFAULT, RAMP, STEP,
    DISSIPATED_ENERGY_FRACTION,
    QUASI_STATIC, MODERATE_DISSIPATION, TRANSIENT_FIDELITY,
    AUTOMATIC_GLOBAL, AUTOMATIC_EBE, FIXED_USER_DEFINED_INC, FIXED_EBE,
)

if TYPE_CHECKING:
    from abaqus.Model.Model import Model

from abq_serp_sub.core.context import (
    # 分析步配置 - 枚举
    StepType,
    ImplicitApplication,
    AmplitudeType,
    TimeIncrementationMethod,
    # 分析步配置 - 配置类
    StepIncrementConfig,
    ImplicitDynamicsStepConfig,
    ExplicitDynamicsStepConfig,
    # 分析步配置 - 序列配置
    AnalysisStepConfig,
    # 分析步配置 - 默认配置
    get_default_static_config,
    get_default_implicit_dynamics_config,
    get_default_explicit_dynamics_config,
)



# region 创建静态分析步
def create_step(
    model: "Model",
    config: StepIncrementConfig | None = None,
    name: str | None = None,
    previous: str | None = None,
    enable_restart: bool = False,
    restart_intervals: int = 1,
    set_time_incrementation: bool = False,
):
    """
    创建分析步（通用函数）。

    自动跟踪调用次数，自动设置分析步名称和前序步骤。
    第 1 次调用：name="Step-1", previous="Initial"
    第 n 次调用：name="Step-{n}", previous="Step-{n-1}"

    Args:
        model: Abaqus 模型对象
        config (StepIncrementConfig | None): 增量控制配置，None 时使用默认值
        name (str | None): 分析步名称，None 时自动生成
        previous (str | None): 前一个分析步名称，None 时自动生成
        enable_restart (bool): 是否启用重启动功能，默认 False
        restart_intervals (int): 重启动间隔数，默认 1
        set_time_incrementation (bool): 是否设置时间增量控制参数，默认 False

    Returns:
        Step: 创建的分析步对象
    """
    # 获取并递增调用计数器
    call_count = getattr(create_step, '_call_count', 0) + 1
    create_step._call_count = call_count

    # 自动设置 name 和 previous
    if name is None:
        name = f"Step-{call_count}"
    if previous is None:
        previous = "Initial" if call_count == 1 else f"Step-{call_count - 1}"

    if config is None:
        config = get_default_static_config()

    step = model.StaticStep(
        name=name,
        previous=previous,
        nlgeom=ON,
        maxNumInc=config.max_num_inc,
        initialInc=config.initial_inc,
        minInc=config.min_inc,
        maxInc=config.max_inc,
        stabilizationMagnitude=0.002,
        stabilizationMethod=DISSIPATED_ENERGY_FRACTION,
        continueDampingFactors=False,
        adaptiveDampingRatio=0.2,
    )

    if enable_restart:
        step.Restart(frequency=0, numberIntervals=restart_intervals, overlay=OFF, timeMarks=OFF)

    if set_time_incrementation:
        step.control.setValues(
            allowPropagation=OFF,
            resetDefaultValues=OFF,
            timeIncrementation=(4.0, 8.0, 9.0, 16.0, 10.0, 4.0, 12.0, 8.0, 6.0, 3.0, 50.0),
        )

    return step
# endregion


# region 创建隐式动力学步
def create_implicit_dynamics_step(
    model: "Model",
    config: ImplicitDynamicsStepConfig | None = None,
    name: str | None = None,
    previous: str | None = None,
    enable_restart: bool = False,
    restart_intervals: int = 1,
):
    """
    创建隐式动力学分析步。

    自动跟踪调用次数，自动设置分析步名称和前序步骤。

    Args:
        model: Abaqus 模型对象
        config (ImplicitDynamicsStepConfig | None): 隐式动力学配置，None 时使用默认值
        name (str | None): 分析步名称，None 时自动生成
        previous (str | None): 前一个分析步名称，None 时自动生成
        enable_restart (bool): 是否启用重启动功能，默认 False
        restart_intervals (int): 重启动间隔数，默认 1

    Returns:
        Step: 创建的隐式动力学分析步对象
    """
    # 获取并递增调用计数器
    call_count = getattr(create_implicit_dynamics_step, '_call_count', 0) + 1
    create_implicit_dynamics_step._call_count = call_count

    # 自动设置 name 和 previous
    if name is None:
        name = f"Step-{call_count}"
    if previous is None:
        previous = "Initial" if call_count == 1 else f"Step-{call_count - 1}"

    if config is None:
        config = get_default_implicit_dynamics_config()

    # 构建参数字典
    step_kwargs = dict(
        name=name,
        previous=previous,
        timePeriod=config.time_period,
        maxNumInc=config.max_num_inc,
        initialInc=config.initial_inc,
        minInc=config.min_inc,
        nohaf=ON if config.nohaf else OFF,
        initialConditions=ON if config.initial_conditions else OFF,
        nlgeom=ON if config.nlgeom else OFF,
    )

    # application 参数（需要转换为 ABAQUS 常量）
    app_map = {
        ImplicitApplication.QUASI_STATIC: QUASI_STATIC,
        ImplicitApplication.MODERATE_DISSIPATION: MODERATE_DISSIPATION,
        ImplicitApplication.TRANSIENT_FIDELITY: TRANSIENT_FIDELITY,
    }
    step_kwargs['application'] = app_map.get(config.application, QUASI_STATIC)

    # amplitude 参数
    amp_map = {
        AmplitudeType.RAMP: RAMP,
        AmplitudeType.STEP: STEP,
    }
    step_kwargs['amplitude'] = amp_map.get(config.amplitude, RAMP)

    # alpha 参数
    if config.alpha is None:
        step_kwargs['alpha'] = DEFAULT
    else:
        step_kwargs['alpha'] = config.alpha

    step = model.ImplicitDynamicsStep(**step_kwargs)

    if enable_restart:
        step.Restart(frequency=0, numberIntervals=restart_intervals, overlay=OFF, timeMarks=OFF)

    return step
# endregion


# region 创建显式动力学步
def create_explicit_dynamics_step(
    model: "Model",
    config: ExplicitDynamicsStepConfig | None = None,
    name: str | None = None,
    previous: str | None = None,
):
    """
    创建显式动力学分析步。

    自动跟踪调用次数，自动设置分析步名称和前序步骤。

    Args:
        model: Abaqus 模型对象
        config (ExplicitDynamicsStepConfig | None): 显式动力学配置，None 时使用默认值
        name (str | None): 分析步名称，None 时自动生成
        previous (str | None): 前一个分析步名称，None 时自动生成

    Returns:
        Step: 创建的显式动力学分析步对象
    """
    # 获取并递增调用计数器
    call_count = getattr(create_explicit_dynamics_step, '_call_count', 0) + 1
    create_explicit_dynamics_step._call_count = call_count

    # 自动设置 name 和 previous
    if name is None:
        name = f"Step-{call_count}"
    if previous is None:
        previous = "Initial" if call_count == 1 else f"Step-{call_count - 1}"

    if config is None:
        config = get_default_explicit_dynamics_config()

    # 构建参数字典
    step_kwargs = dict(
        name=name,
        previous=previous,
        timePeriod=config.time_period,
        improvedDtMethod=ON if config.improved_dt_method else OFF,
        scaleFactor=config.scale_factor,
        linearBulkViscosity=config.linear_bulk_viscosity,
        quadBulkViscosity=config.quad_bulk_viscosity,
        nlgeom=ON if config.nlgeom else OFF,
        adiabatic=ON if config.adiabatic else OFF,
    )

    # timeIncrementationMethod 参数（需要转换为 ABAQUS 常量）
    method_map = {
        TimeIncrementationMethod.AUTOMATIC_GLOBAL: AUTOMATIC_GLOBAL,
        TimeIncrementationMethod.AUTOMATIC_EBE: AUTOMATIC_EBE,
        TimeIncrementationMethod.FIXED_USER_DEFINED_INC: FIXED_USER_DEFINED_INC,
        TimeIncrementationMethod.FIXED_EBE: FIXED_EBE,
    }
    step_kwargs['timeIncrementationMethod'] = method_map.get(
        config.time_incrementation_method, AUTOMATIC_GLOBAL
    )

    # 用户定义的时间增量（仅当使用 FIXED_USER_DEFINED_INC 时）
    if (config.time_incrementation_method == TimeIncrementationMethod.FIXED_USER_DEFINED_INC
        and config.user_defined_inc is not None):
        step_kwargs['userDefinedInc'] = config.user_defined_inc

    step = model.ExplicitDynamicsStep(**step_kwargs)

    return step
# endregion


# region 创建分析步（统一入口）
def create_dynamics_step(
    model: "Model",
    step_type: StepType = StepType.STATIC,
    config: StepIncrementConfig | ImplicitDynamicsStepConfig | ExplicitDynamicsStepConfig | None = None,
    name: str | None = None,
    previous: str | None = None,
    enable_restart: bool = False,
    restart_intervals: int = 1,
    set_time_incrementation: bool = False,
):
    """
    创建分析步（统一入口，支持静态/隐式动力学/显式动力学）。

    Args:
        model: Abaqus 模型对象
        step_type (StepType): 分析步类型，默认 STATIC
        config: 分析步配置，类型需与 step_type 匹配，None 时使用对应的默认配置
        name (str | None): 分析步名称，None 时自动生成
        previous (str | None): 前一个分析步名称，None 时自动生成
        enable_restart (bool): 是否启用重启动功能（仅适用于静态和隐式动力学）
        restart_intervals (int): 重启动间隔数
        set_time_incrementation (bool): 是否设置时间增量控制（仅适用于静态步）

    Returns:
        Step: 创建的分析步对象

    Raises:
        ValueError: 当 step_type 不是有效的 StepType 时
    """
    if step_type == StepType.STATIC:
        return create_step(
            model=model,
            config=config,
            name=name,
            previous=previous,
            enable_restart=enable_restart,
            restart_intervals=restart_intervals,
            set_time_incrementation=set_time_incrementation,
        )
    elif step_type == StepType.IMPLICIT_DYNAMICS:
        return create_implicit_dynamics_step(
            model=model,
            config=config,
            name=name,
            previous=previous,
            enable_restart=enable_restart,
            restart_intervals=restart_intervals,
        )
    elif step_type == StepType.EXPLICIT_DYNAMICS:
        return create_explicit_dynamics_step(
            model=model,
            config=config,
            name=name,
            previous=previous,
        )
    else:
        raise ValueError(f"不支持的分析步类型: {step_type}")
# endregion


# region 重置计数器
def reset_all_step_counters():
    """
    重置所有分析步创建函数的调用计数器。

    在创建新模型时调用，确保步骤编号从 1 开始。
    """
    create_step._call_count = 0
    create_implicit_dynamics_step._call_count = 0
    create_explicit_dynamics_step._call_count = 0
# endregion


# region 拉伸步配置
def create_stretch_config(u1: float, u2: float, min_inc: float = 1e-08) -> StepIncrementConfig:
    """
    根据位移差计算拉伸步的增量配置。

    每步拉伸约 0.008。

    Args:
        u1 (float): 第一步施加的位移
        u2 (float): 第二步施加的位移
        min_inc (float): 最小增量，默认 1e-08

    Returns:
        StepIncrementConfig: 计算好的增量配置
    """
    step_increment = 0.008 / (u2 - u1) if (u2 - u1) > 0.01 else 0.5
    max_num_inc = int(1 / step_increment) * 6

    return StepIncrementConfig(
        max_num_inc=max_num_inc,
        initial_inc=step_increment,
        min_inc=min_inc,
        max_inc=step_increment,
    )
# endregion


# region 创建分析步（便捷）
def create_analysis_steps(
    model: "Model",
    u1: float,
    u2: float,
    step_type: StepType = StepType.STATIC,
    preload_config: StepIncrementConfig | ImplicitDynamicsStepConfig | ExplicitDynamicsStepConfig | None = None,
    stretch_config: StepIncrementConfig | ImplicitDynamicsStepConfig | ExplicitDynamicsStepConfig | None = None,
    enable_restart: bool = False,
):
    """
    创建分析步 Step-1 和 Step-2（便捷函数）。

    会自动重置步骤计数器，确保从 Step-1 开始。

    Args:
        model: Abaqus 模型对象
        u1 (float): 第一步施加的位移
        u2 (float): 第二步施加的位移
        step_type (StepType): 分析步类型，默认 STATIC
        preload_config: Step-1 增量控制配置，类型需与 step_type 匹配
        stretch_config: Step-2 增量控制配置，None 时自动计算（仅支持 STATIC 类型）
        enable_restart (bool): 是否启用重启动功能，默认 False（仅适用于静态和隐式动力学）

    Returns:
        tuple: (step1, step2) 创建的分析步对象
    """
    # 重置所有计数器，确保从 Step-1 开始
    reset_all_step_counters()

    if step_type == StepType.STATIC:
        # Step-1: 预加载步
        step1 = create_step(
            model=model,
            config=preload_config,
            enable_restart=enable_restart,
            restart_intervals=1,
            set_time_incrementation=True,
        )

        # Step-2: 拉伸步（自动计算增量配置）
        if stretch_config is None:
            stretch_config = create_stretch_config(u1, u2)

        step2 = create_step(
            model=model,
            config=stretch_config,
            enable_restart=enable_restart,
            restart_intervals=2,
            set_time_incrementation=False,
        )

    elif step_type == StepType.IMPLICIT_DYNAMICS:
        # 隐式动力学分析步
        step1 = create_implicit_dynamics_step(
            model=model,
            config=preload_config,
            enable_restart=enable_restart,
            restart_intervals=1,
        )

        step2 = create_implicit_dynamics_step(
            model=model,
            config=stretch_config,
            enable_restart=enable_restart,
            restart_intervals=2,
        )

    elif step_type == StepType.EXPLICIT_DYNAMICS:
        # 显式动力学分析步
        step1 = create_explicit_dynamics_step(
            model=model,
            config=preload_config,
        )

        step2 = create_explicit_dynamics_step(
            model=model,
            config=stretch_config,
        )

    else:
        raise ValueError(f"不支持的分析步类型: {step_type}")

    return step1, step2
# endregion


# region 场输出设置
def setup_field_outputs(
    model: "Model",
    modelname: str,
    global_output: bool = False,
):
    """
    设置场输出请求。

    Args:
        model: Abaqus 模型对象
        modelname (str): 模型名称
        global_output (bool): 是否使用全局输出，默认 False
    """
    if global_output:
        # 使用全局输出
        model.fieldOutputRequests["F-Output-1"].setValues(
            variables=("U", "RF", "LE", "CSTRESS", "CFORCE"),
            sectionPoints=(1, 2, 3, 4, 5, 6, 7, 8, 9),
        )
    else:
        # 使用分别的场输出
        _regionDef = model.rootAssembly.allInstances["Substrate-1"].sets["TPC_A"]
        model.FieldOutputRequest(
            name="F-Output-1",
            createStepName="Step-2",
            variables=("U",),
            frequency=1,
            region=_regionDef,
        )

        _regionDef = model.rootAssembly.allInstances["Wire-1"].sets["All"]
        model.FieldOutputRequest(
            name="F-Output-2",
            createStepName="Step-2",
            variables=("LE", "U", "CSTRESS", "CFORCE"),
            frequency=1,
            region=_regionDef,
            sectionPoints=(1, 2, 3, 4, 5, 6, 7, 8, 9),
        )
# endregion


# region 根据配置列表创建分析步
def create_steps_from_configs(
    model: "Model",
    step_configs: tuple[AnalysisStepConfig, ...],
) -> list:
    """
    根据分析步配置列表创建分析步。

    遍历配置列表，按顺序创建每个分析步。会自动重置步骤计数器，
    确保从 Step-1 开始。

    Args:
        model: Abaqus 模型对象
        step_configs: 分析步配置元组，每个元素是一个 AnalysisStepConfig

    Returns:
        list: 创建的分析步对象列表

    Example:
        >>> steps = create_steps_from_configs(model, (
        ...     AnalysisStepConfig(step_type=StepType.STATIC, config=...),
        ...     AnalysisStepConfig(step_type=StepType.STATIC, config=...),
        ... ))
    """
    # 重置所有计数器，确保从 Step-1 开始
    reset_all_step_counters()

    created_steps = []

    for step_config in step_configs:
        step_type = step_config.step_type
        config = step_config.config
        enable_restart = step_config.enable_restart
        restart_intervals = step_config.restart_intervals
        set_time_incrementation = step_config.set_time_incrementation

        if step_type == StepType.STATIC:
            step = create_step(
                model=model,
                config=config,
                enable_restart=enable_restart,
                restart_intervals=restart_intervals,
                set_time_incrementation=set_time_incrementation,
            )
        elif step_type == StepType.IMPLICIT_DYNAMICS:
            step = create_implicit_dynamics_step(
                model=model,
                config=config,
                enable_restart=enable_restart,
                restart_intervals=restart_intervals,
            )
        elif step_type == StepType.EXPLICIT_DYNAMICS:
            step = create_explicit_dynamics_step(
                model=model,
                config=config,
            )
        else:
            raise ValueError(f"不支持的分析步类型: {step_type}")

        created_steps.append(step)

    return created_steps
# endregion
