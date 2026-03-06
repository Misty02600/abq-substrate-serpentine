# [TASK014] - ABAQUS Python 环境配置与项目组织优化

**Status:** Pending
**Added:** 2026-03-02
**Updated:** 2026-03-02

## Original Request
优化 ABAQUS 脚本的运行方式和项目组织：
1. 解决 ABAQUS Python 中 import 路径和依赖管理问题
2. 清理入口脚本中的 sys.path hack
3. 整理项目特定脚本与可复用库的关系
4. 改进 justfile 硬编码路径

## Thought Process

### 依赖分析结论
- ABAQUS 建模流程只需 numpy（内置），后处理需要 pandas
- pydantic、hydra、omegaconf、scipy 只在本地 Python 运行
- abqpy 提供同名模块（abaqus/abaqusConstants），不能暴露给 ABAQUS Python

### 方案选择
- 讨论了 abaqus_v6.env（cwd 依赖，不可行）、.pth 文件、PYTHONPATH、--target 隔离目录等方案
- 最终决定：直接安装到 ABAQUS Python（`pip install -e .`）
- 重构 pyproject.toml：`dependencies` 只放 ABAQUS 需要的（pandas），其他放 `dependency-groups`

### 项目组织
- 根级后处理脚本是项目特定的（旧项目已结束）
- 迁移到 `experiments/` 目录按项目组织
- 通用的后处理工具保留在 `src/abq_serp_sub/` 包内

## Implementation Plan

### Phase 1: pyproject.toml 重构
重构依赖分组，使 `abaqus python -m pip install -e .` 只安装 pandas：
```toml
[project]
dependencies = ["pandas==2.3.3"]

[dependency-groups]
local = ["hydra-core==1.3.2", "omegaconf==2.3.0", ...]
dev = [{ include-group = "local" }, "abqpy", "pytest"]
```

### Phase 2: ABAQUS Python 安装
```powershell
abaqus python -m pip install -e .
```

### Phase 3: 清理入口脚本
- 删除所有 `SCRIPT_DIR` / `sys.path.append` 逻辑
- 统一 `from src.*` 导入为 `from abq_serp_sub.*`

### Phase 4: justfile 改进
- `root` 改为 `justfile_directory()`
- 添加 `setup-abaqus` recipe

### Phase 5: 项目组织
- 创建 `experiments/` 目录
- 迁移根级后处理脚本到 `experiments/porosity_stretchability/`
- 清理/标记弃用 `build_solid_serpentine.py`

## Progress Tracking

**Overall Status:** Not Started - 0%

### Subtasks
| ID   | Description                                  | Status      | Updated    | Notes                    |
| ---- | -------------------------------------------- | ----------- | ---------- | ------------------------ |
| 14.1 | 重构 pyproject.toml 依赖分组                 | Not Started | 2026-03-02 | dependencies 只放 pandas |
| 14.2 | 执行 abaqus python -m pip install -e .       | Not Started | 2026-03-02 |                          |
| 14.3 | 清理入口脚本 sys.path hack                   | Not Started | 2026-03-02 | 6+ 个文件                |
| 14.4 | 统一旧式导入路径 (from src.* → abq_serp_sub) | Not Started | 2026-03-02 | extract_*.py             |
| 14.5 | justfile 改为 justfile_directory()           | Not Started | 2026-03-02 |                          |
| 14.6 | 添加 setup-abaqus recipe 到 justfile         | Not Started | 2026-03-02 |                          |
| 14.7 | 创建 experiments/ 目录结构                   | Not Started | 2026-03-02 |                          |
| 14.8 | 迁移根级后处理脚本到 experiments/            | Not Started | 2026-03-02 | 4 个文件                 |
| 14.9 | 清理 build_solid_serpentine.py               | Not Started | 2026-03-02 | 归档或删除               |

## Progress Log
### 2026-03-02
- 创建任务
- 完成依赖全景分析（见 dependency_analysis.md artifact）
- 讨论多种方案，确定最终方案：重构 pyproject.toml + pip install -e .
- 确定项目组织方案：experiments/ 目录分离项目特定脚本
