# [TASK015] - 基于 RPY 的路径 LE 后处理导出

**Status:** In Progress
**Added:** 2026-03-07
**Updated:** 2026-03-07

## Original Request
用户希望基于当前 Abaqus/CAE 录制操作（`abaqus.rpy`）实现后处理脚本，目标是：
1. 按路径提取 `LE` 场变量；
2. 分别提取 `wire` 与 `sub` 两个部件沿路径的数据；
3. 横坐标使用 `x coordinate`；
4. 将后处理加入 `postprocess/` 下的新项目目录；
5. 导出为 CSV，文件名使用模型名；
6. 脚本只提取“当前展示的模型”（当前 viewport 显示的 ODB/model）。

## Thought Process
根据用户当前编辑的 `g:/zyt/serp-sub-inface/tests4/abaqus.rpy`，可识别到以下关键操作模式：

1. **变量设置**
   - 主变量设置为 `LE`，输出位置为积分点，包含 `Max. Principal`。

2. **路径设置**
   - 使用 `Path-1`，最终路径为点列表形式，典型端点：
     - `(0.0, 9.5, 0.600000023841858)`
     - `(8.0, 9.5, 0.600000023841858)`
   - 采用 `UNIFORM_SPACING` 与 `numIntervals=100`。

3. **分别提取 wire / sub**
   - 通过 display group 切换（`SUBSTRATE-1` / 默认模型）分别生成 XYData。
   - `XYDataFromPath` 里逐步确认横坐标为 `labelType=X_COORDINATE`。
   - 命名上已出现 `sub`, `wire`, `sub2`, `wire2` 等曲线对象。

4. **当前展示模型语义**
   - 脚本交互中多次 `session.viewports['Viewport: 1'].setValues(displayedObject=odb)`，说明目标应从当前 viewport 的 displayed object 动态获取，不应硬编码 ODB 路径。

## Implementation Plan
- [x] 1. 在 `postprocess/` 下创建新的后处理项目目录（用于路径 LE 导出）。
- [x] 2. 编写脚本：从当前 viewport 获取当前显示 ODB 与模型标识。
- [x] 3. 复现路径提取流程：统一 Path 创建参数与 `LE` 变量设置。
- [x] 4. 分别提取 `wire` 与 `sub` 曲线，横坐标固定为 `X_COORDINATE`。
- [x] 5. 规范化导出 CSV（模型名命名，包含数据来源标记）。
- [x] 6. 在 README 或脚本头部补充使用方式（CAE 交互运行/noGUI 入口）。
- [ ] 7. 在 Abaqus/CAE 中进行实跑验证。

## Progress Tracking

**Overall Status:** In Progress - 90%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 15.1 | 创建后处理项目目录 | Complete | 2026-03-07 | 新增 `postprocess/path_le_xcoord/` |
| 15.2 | 读取当前 viewport 模型 | Complete | 2026-03-07 | 复用 `current_display_info()` |
| 15.3 | 实现 Path + LE 提取 | Complete | 2026-03-07 | `POINT_LIST` + `LE` + `INTEGRATION_POINT` |
| 15.4 | 分离 wire/sub 输出 | Complete | 2026-03-07 | display group 切换提取 |
| 15.5 | 按模型名导出 CSV | Complete | 2026-03-07 | 输出 `<model_name>.csv` |
| 15.6 | 补充文档与示例 | Complete | 2026-03-07 | 模块头部增加调用示例 |
| 15.7 | Abaqus/CAE 实跑验证 | Not Started | 2026-03-07 | 待用户环境执行 |
| 15.8 | 多帧宽表CSV导出重构 | Complete | 2026-03-07 | 首列x，后续列为frame数据 |

## Progress Log
### 2026-03-07
- 创建任务并记录需求。
- 解析用户当前 `abaqus.rpy` 的关键后处理操作：`Path-1`、`LE`、`X_COORDINATE`、wire/sub 分别提取。
- 明确本任务先登记，不立即修改业务代码，待用户确认后实施。

### 2026-03-07（实现）
- 新建脚本：`postprocess/path_le_xcoord/extract_path_le_xcoord.py`。
- 新增端点构造函数 `make_horizontal_endpoints(x_start, x_end, y_value, z_value)`，支持“基底上表面水平线”端点输入。
- 主函数 `extract_path_le_xcoord_to_csv(...)` 新增参数：`start_point`、`end_point`、`step`、`frame` 等。
- 通过 `abq_serp_sub.utils.abaqus_utils.current_display_info()` 获取当前视口正在显示的 ODB 与模型名。
- 按 `X_COORDINATE` 横坐标分别提取 `SUBSTRATE-1` 与 `WIRE-1` 的 LE，并合并导出为 `<model_name>.csv`。
- 完成语法与静态错误检查（无报错），待 Abaqus/CAE 实跑验证。

### 2026-03-07（重构）
- 根据用户反馈，将脚本重构为“两层函数”：
   - `extract_path_le_xcoord_data(...)`：仅提取单帧数据，不写文件。
   - `extract_multi_frame_le_to_csv(...)`：对多个帧提取并导出 CSV。
- CSV 改为宽表格式：第一列 `x_coordinate`，后续列 `frame_<帧号>`。
- 为避免 wire 与 sub 混排，分别输出：`<model_name>_sub.csv` 与 `<model_name>_wire.csv`。
- 增加多帧对齐校验：若不同帧 x 坐标或点数不一致，直接报错提示。
