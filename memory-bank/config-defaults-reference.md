# 配置默认值参考（代码对齐版）

## 目的

本文档作为当前仓库的配置默认值“单一参考源”，回答三个问题：

1. 字段默认值是多少
2. 默认值在哪一层生效
3. 配置从输入到 Abaqus 执行的实际流转路径

基线日期：2026-03-02（按当前仓库代码审计）

---

## 一、端到端数据流

### 1) 本地参数生成侧（Hydra/OmegaConf/Pydantic）

入口：`generate_params.py`

流程：

1. Hydra 读取配置
2. `register_resolvers()` 注册 OmegaConf resolver
   文件：`src/abq_serp_sub/preprocess/config/resolvers.py`
3. `OmegaConf.to_container(..., resolve=True)` 解析 `${...}`
4. `Config(**cfg_dict)` 做 Pydantic 校验和默认值填充
   文件：`src/abq_serp_sub/preprocess/config/models.py`
5. `model_dump()` 序列化成 JSON

### 2) Abaqus 建模侧（JSON -> dataclass -> create_model）

入口：`generate_from_json.py` -> `create_model_from_dict()`

流程：

1. JSON 读入 `dict`
2. `build_model_config(cfg)` 将 dict 转为 dataclass
   文件：`src/abq_serp_sub/preprocess/builders.py`
3. `create_model(config)` 执行建模
   文件：`src/abq_serp_sub/processes/assembly.py`

---

## 二、默认值优先级（高 -> 低）

1. 输入 JSON/YAML 显式值
2. Pydantic `Field(default=...)` / `default_factory=...`
3. Builder 层 `dict.get(key, fallback)`
4. dataclass 字段默认值（`core/context/*.py`）
5. 运行时函数兜底（主要在 `processes/steps.py`，当 `config is None`）

注意：后层映射若遗漏，前层值可能“提供了但没生效”。

---

## 三、Pydantic 层默认值（`preprocess/config/models.py`）

## 3.1 顶层 `Config`

- `loading = LoadingConfig()`（保留兼容，已弃用）
- `computing = ComputingConfig()`
- `analysis = AnalysisConfig()`
- `interaction = InteractionConfig()`
- `naming = NamingConfig()`
- `steps = []`
- `modelname = ""`（随后在 `model_validator` 中自动生成）

## 3.2 substrate

- `type = porous`
- `elem_code = "C3D8R"`
- `material = None`（后续 Builder 回退到 `PDMS`）
- `length/width/n_rows/n_cols/porosity/square_size` 默认 `None`，由类型校验器约束

## 3.3 wire

- `rotation_angle = 0`
- `rotation_center = "center"`
- `has_end_caps = True`
- `flip_vertical = False`
- `pi_thickness = 0.004`
- `pi_E = None`
- `pi_nu = None`
- `pi_density = 1.42e-9`
- `cu_thickness = 0.0003`
- `cu_E = None`
- `cu_nu = None`
- `cu_density = 8.96e-9`

## 3.4 pores

- `use_standard_circles = False`

## 3.5 computing

- `num_cpus = 1`
- `enable_restart = False`

## 3.6 analysis / step 相关

- `AnalysisConfig`
  - `stabilization_magnitude = 0.002`
  - `adaptive_damping_ratio = 0.2`
- `ImplicitDynamicsConfig`
  - `max_num_inc=10000`
  - `initial_inc=0.001`
  - `min_inc=1e-09`
  - `time_period=1.0`
  - `application=QUASI_STATIC`
  - `amplitude=RAMP`
  - `alpha=None`
  - `nohaf=False`
  - `nlgeom=True`
- `ExplicitDynamicsConfig`
  - `time_period=1.0`
  - `time_incrementation_method=AUTOMATIC_GLOBAL`
  - `improved_dt_method=True`
  - `scale_factor=1.0`
  - `linear_bulk_viscosity=0.06`
  - `quad_bulk_viscosity=1.2`
  - `nlgeom=True`
  - `adiabatic=False`
  - `user_defined_inc=None`
- `StepConfig`
  - `step_type=static`
  - `displacement=None`
  - `max_num_inc=100`
  - `initial_inc=0.1`
  - `min_inc=1e-08`
  - `max_inc=1.0`
  - `enable_restart=False`
  - `restart_intervals=1`
  - `set_time_incrementation=True`
  - `implicit=None`
  - `explicit=None`
  - `field_output=None`
- `FieldOutputConfig`
  - `variables=["S","E","U","RF"]`
  - `frequency=1`
  - `position="INTEGRATION_POINTS"`

## 3.7 interaction / output / naming

- `InteractionConfig`
  - `use_cohesive=False`
  - `master_surface=substrate_top`
  - `sliding=small`
  - `cohesive=None`
- `CohesiveConfig`
  - `stiffness_* = 1.0e6`
  - `max_stress_* = 1.0`
  - `fracture_energy = 0.1`
- `NamingConfig.custom_params = None`

---

## 四、Builder 层默认值（`preprocess/builders.py`）

## 4.1 substrate 构建

- `substrate.type` 缺省回退 `"porous"`
- 材料默认回退 `PDMS`（`processes/parts/material_instances.py`）
- 自定义材料子字段缺省回退：
  - `name -> "PDMS"`
  - `c1/c2/d -> PDMS.c1/c2/d`
- `elem_code` 缺省回退 `"C3D8R"`

## 4.2 wire 构建

- `rotation_center` 缺省回退 `"center"`
- PI 参数回退：
  - `pi_E` 缺省/None -> `PI.youngs_modulus`
  - `pi_nu` 缺省/None -> `PI.poissons_ratio`
- Cu 参数回退：
  - `cu_E` 缺省/None -> `CU.youngs_modulus`
  - `cu_nu` 缺省/None -> `CU.poissons_ratio`

## 4.3 steps 构建（`build_steps_config`）

- `steps` 为空：返回 `()`
- 每步默认回退：
  - `step_type` 默认 `"static"`
  - static：`100 / 0.1 / 1e-08 / 1.0`
  - implicit：`10000 / 0.001 / 1e-09 / 1.0`，`amplitude=RAMP`，`alpha=None`，`nohaf=False`，`initial_conditions=False`，`nlgeom=True`
  - explicit：`time_period=1.0`，`method=AUTOMATIC_GLOBAL`，`improved_dt_method=True`，`scale_factor=1.0`，`linear=0.06`，`quad=1.2`，`nlgeom=True`，`adiabatic=False`，`user_defined_inc=None`
  - `displacement=None`
  - `enable_restart=False`
  - `restart_intervals=1`
  - `set_time_incrementation=True`
- `field_output` 默认回退：
  - `variables=["S","E","U","RF"]`
  - `frequency=1`
  - `position="INTEGRATION_POINTS"`

## 4.4 interaction 构建

- `use_cohesive=False`
- `master_surface` 缺省 `"substrate_top"`
- cohesive 参数数值默认与 Pydantic 一致（1e6 / 1.0 / 0.1）

---

## 五、dataclass 层默认值（`core/context`）

## 5.1 `core/context/substrate.py`

- `SubstrateMeshConfig.elem_code = "C3D8R"`

## 5.2 `core/context/model.py`

- `CohesiveConfig`
  - `stiffness_* = 1.0e6`
  - `max_stress_* = 1.0`
  - `fracture_energy = 0.1`
  - `viscosity_coef = 5e-6`
- `InteractionConfig`
  - `master_surface = SUBSTRATE_TOP`
  - `sliding = SMALL`
  - `cohesive = None`
- `ModelConfig.steps = ()`
- `ModelConfig.fix_substrate_bottom_z = False`

## 5.3 `core/context/step.py`

- `ImplicitDynamicsStepConfig`：time/application/amplitude 等默认
- `ExplicitDynamicsStepConfig`：time/method/viscosity 等默认
- `FieldOutputConfig`：`('S','E','U','RF') / 1 / INTEGRATION_POINTS`
- `AnalysisStepConfig`
  - `step_type=STATIC`
  - `config=None`
  - `displacement=None`
  - `enable_restart=False`
  - `restart_intervals=1`
  - `set_time_incrementation=False`
  - `field_output=None`
- 工厂函数默认：
  - `get_default_static_config() -> (150, 0.1, 1e-08, 0.5)`
  - `get_default_implicit_dynamics_config() -> (10000, 0.001, 1e-09, 1.0, QUASI_STATIC, RAMP, nlgeom=True)`
  - `get_default_explicit_dynamics_config() -> (1.0, AUTOMATIC_GLOBAL, improved_dt_method=True, nlgeom=True)`

---

## 六、运行时兜底（`processes/steps.py`）

- `create_step(config=None)` -> `get_default_static_config()`
- `create_implicit_dynamics_step(config=None)` -> `get_default_implicit_dynamics_config()`
- `create_explicit_dynamics_step(config=None)` -> `get_default_explicit_dynamics_config()`

此外静态步里还有硬编码参数：

- `stabilizationMagnitude = 0.002`
- `adaptiveDampingRatio = 0.2`
- `stabilizationMethod = DISSIPATED_ENERGY_FRACTION`

---

## 七、当前代码里的关键注意点（易踩坑）

1. `steps=[]` 不会自动生成两步分析
虽然 Pydantic 顶层注释写了“空列表时使用默认两步配置”，但当前实际流程是：
`build_steps_config([]) -> ()`，`create_model()` 不会自动补步。

2. `interaction.sliding` 当前未在 Builder 层透传
`build_interaction_config()` 没有把输入 `sliding` 传给 dataclass，运行时将使用 dataclass 默认 `SMALL`。

3. `implicit.application` 当前被 Builder 固定为 `QUASI_STATIC`
`build_steps_config()` 对隐式步硬编码 `application=ImplicitApplication.QUASI_STATIC`。

4. 部分 density 字段未完全贯通
- `wire.pi_density / wire.cu_density` 目前未用于 builder 组装线弹材料
- `substrate.material.density` 在 builder 自定义材料分支里未传递

5. ~~`output.global_output`~~ 已清理（2026-03-03），`setup_field_outputs()` 已删除

---

## 八、配置含义（字段语义与单位）

本节解释“字段是干什么的”，用于和默认值章节配套阅读。

### 8.1 顶层字段（`Config`）

| 字段          | 含义                         |
| ------------- | ---------------------------- |
| `substrate`   | 基底几何/网格/材料配置       |
| `wire`        | 蛇形导线几何/截面/材料配置   |
| `pores`       | 多孔基底圆孔扰动与随机性配置 |
| `computing`   | 作业计算资源与重启动开关     |
| `analysis`    | 静态步稳定化参数（遗留）     |
| `steps`       | 分析步序列（推荐主入口）     |
| `interaction` | 基底-导线界面约束/接触配置   |
| `naming`      | 模型命名拼接策略             |
| `fix_substrate_bottom_z` | 是否约束基底底面 z 方向位移 |
| `modelname`   | 最终模型名；空时自动生成     |

### 8.2 substrate（基底）

| 字段             | 含义                     | 常用单位/取值      |
| ---------------- | ------------------------ | ------------------ |
| `type`           | 基底类型                 | `solid` / `porous` |
| `length`         | 实心基底 X 向长度        | mm                 |
| `width`          | 实心基底 Y 向宽度        | mm                 |
| `n_rows`         | 多孔阵列行数             | 正整数             |
| `n_cols`         | 多孔阵列列数             | 正整数             |
| `porosity`       | 孔隙率                   | 0~0.7854           |
| `square_size`    | 多孔单元边长             | mm                 |
| `depth`          | 基底厚度（拉伸方向）     | mm                 |
| `seed_size`      | 基底全局布种尺寸         | mm                 |
| `edge_seed_size` | 导线邻域边缘细化布种尺寸 | mm                 |
| `elem_code`      | Abaqus 单元代码          | 例如 `C3D8R`       |
| `material`       | 基底材料参数对象         | 见下表             |

`substrate.material` 子字段：

| 字段      | 含义                  | 常用单位        |
| --------- | --------------------- | --------------- |
| `name`    | 材料名                | 字符串          |
| `density` | 密度                  | tonne/mm³       |
| `c1`      | Mooney-Rivlin 参数 C1 | MPa（工程习惯） |
| `c2`      | Mooney-Rivlin 参数 C2 | MPa（工程习惯） |
| `d`       | 体积压缩相关参数      | 材料模型参数    |

### 8.3 wire（蛇形导线）

| 字段              | 含义                       | 常用单位/取值                   |
| ----------------- | -------------------------- | ------------------------------- |
| `w`               | 线宽                       | mm                              |
| `l_1`             | 一个蛇形周期的水平节距     | mm                              |
| `l_2`             | 竖直直线段长度             | mm                              |
| `m`               | 周期数                     | 正整数                          |
| `seed_size`       | 导线网格布种尺寸           | mm                              |
| `rotation_angle`  | 组装后绕 Z 轴旋转角        | 度                              |
| `rotation_center` | 旋转中心                   | `origin` / `center` / `[x,y,z]` |
| `has_end_caps`    | 是否包含端部圆帽几何       | bool                            |
| `flip_vertical`   | 是否做上下翻转（草图阶段） | bool                            |
| `pi_thickness`    | PI 单层厚度                | mm                              |
| `cu_thickness`    | Cu 层厚度                  | mm                              |
| `pi_E`            | PI 弹性模量（可选）        | MPa                             |
| `pi_nu`           | PI 泊松比（可选）          | 无量纲                          |
| `pi_density`      | PI 密度（可选）            | tonne/mm³                       |
| `cu_E`            | Cu 弹性模量（可选）        | MPa                             |
| `cu_nu`           | Cu 泊松比（可选）          | 无量纲                          |
| `cu_density`      | Cu 密度（可选）            | tonne/mm³                       |

### 8.4 pores（孔隙扰动）

| 字段                   | 含义                           | 常用单位/取值 |
| ---------------------- | ------------------------------ | ------------- |
| `use_standard_circles` | 是否使用标准圆孔阵列（无扰动） | bool          |
| `T_xi`                 | 圆心位置扰动截断幅值           | 无量纲        |
| `T_delta`              | 直径扰动截断幅值               | 无量纲        |
| `random_seed`          | 随机种子（控制可复现）         | 非负整数      |

### 8.5 computing（计算资源）

| 字段             | 含义               | 常用单位/取值 |
| ---------------- | ------------------ | ------------- |
| `num_cpus`       | 作业 CPU 核心数    | 正整数        |
| `enable_restart` | 是否启用重启动输出 | bool          |

### 8.6 steps（分析步）

`steps` 是分析控制主入口，每个元素对应一个 `Step-N`。

通用字段：

| 字段                      | 含义                       | 常用单位/取值                      |
| ------------------------- | -------------------------- | ---------------------------------- |
| `step_type`               | 步类型                     | `static` / `implicit` / `explicit` |
| `displacement`            | 该步施加的单侧位移         | mm                                 |
| `enable_restart`          | 该步是否开启 restart       | bool                               |
| `restart_intervals`       | restart 间隔               | 正整数                             |
| `set_time_incrementation` | 静态步是否写入时间增量控制 | bool                               |

静态步增量字段（直接挂在 step）：

| 字段          | 含义         |
| ------------- | ------------ |
| `max_num_inc` | 最大增量步数 |
| `initial_inc` | 初始增量     |
| `min_inc`     | 最小增量     |
| `max_inc`     | 最大增量     |

隐式动力学子字段（`implicit`）：

| 字段          | 含义                                |
| ------------- | ----------------------------------- |
| `time_period` | 分析时间周期                        |
| `application` | 隐式应用类型                        |
| `amplitude`   | 幅值类型（RAMP/STEP）               |
| `alpha`       | 数值阻尼参数（`None` 表示 DEFAULT） |
| `nohaf`       | 是否禁用 half-increment residual    |
| `nlgeom`      | 是否开启几何非线性                  |

显式动力学子字段（`explicit`）：

| 字段                         | 含义                           |
| ---------------------------- | ------------------------------ |
| `time_period`                | 分析时间周期                   |
| `time_incrementation_method` | 时间增量方法                   |
| `improved_dt_method`         | 是否启用改进步长算法           |
| `scale_factor`               | 时间增量缩放因子               |
| `linear_bulk_viscosity`      | 线性体积粘性                   |
| `quad_bulk_viscosity`        | 二次体积粘性                   |
| `nlgeom`                     | 是否开启几何非线性             |
| `adiabatic`                  | 是否绝热分析                   |
| `user_defined_inc`           | 用户指定增量（特定方法下生效） |

场输出子字段（`field_output`）：

| 字段        | 含义                                |
| ----------- | ----------------------------------- |
| `variables` | 输出变量列表（如 `S/E/U/RF`）       |
| `frequency` | 输出频率（每 N 个增量）             |
| `position`  | 输出位置（如 `INTEGRATION_POINTS`） |

### 8.7 interaction（界面作用）

| 字段             | 含义                             | 常用取值                               |
| ---------------- | -------------------------------- | -------------------------------------- |
| `use_cohesive`   | 是否使用 Cohesive 接触；否则 Tie | bool                                   |
| `master_surface` | 主面选择                         | `substrate_top` / `wire_bottom`        |
| `sliding`        | 接触滑移类型                     | `small` / `finite`（当前代码见注意点） |
| `cohesive`       | Cohesive 参数对象                | 见下表                                 |

`interaction.cohesive` 子字段：

| 字段                 | 含义                 | 常用单位                 |
| -------------------- | -------------------- | ------------------------ |
| `stiffness_normal`   | 法向刚度 Knn         | 力/长度³（接触刚度量纲） |
| `stiffness_shear_1`  | 切向刚度 Kss         | 同上                     |
| `stiffness_shear_2`  | 切向刚度 Ktt         | 同上                     |
| `max_stress_normal`  | 法向损伤起始应力阈值 | 应力                     |
| `max_stress_shear_1` | 切向损伤起始应力阈值 | 应力                     |
| `max_stress_shear_2` | 切向损伤起始应力阈值 | 应力                     |
| `fracture_energy`    | 断裂能               | N/mm                     |

### 8.8 naming

| 字段                   | 含义                             |
| ---------------------- | -------------------------------- |
| `naming.custom_params` | 指定参与模型名拼接的参数路径列表 |

---

## 九、快速定位

- Pydantic 默认值：`src/abq_serp_sub/preprocess/config/models.py`
- Builder 回退逻辑：`src/abq_serp_sub/preprocess/builders.py`
- dataclass 默认值：`src/abq_serp_sub/core/context/*.py`
- 分析步运行时兜底：`src/abq_serp_sub/processes/steps.py`
- 预置材料常量：`src/abq_serp_sub/processes/parts/material_instances.py`

---

## 十、更新记录

- 2026-03-02：首次建立（按当前源码逐层核对）
