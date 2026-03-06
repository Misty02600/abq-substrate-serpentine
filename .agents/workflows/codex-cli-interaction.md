---
description: How to interact with OpenAI Codex CLI from another AI agent for code review, bug finding, and discussion
---

# AI Agent ↔ Codex CLI 交互工作流

## 概述

本工作流描述 AI Agent（如 Gemini/Claude）如何通过终端调用 OpenAI Codex CLI 进行代码审查、bug 查找、以及多轮讨论直至达成共识。

## Prompt 传递方式

> ⚠️ 以下参数均经 `codex exec --help` 及实机运行验证（v0.106.0）

### 方式 1: 直接传字符串（默认首选）

最简单，大多数场景足够：

```powershell
codex exec --full-auto -o C:\tmp\output.txt "Review src/ for bugs. List file, line number, severity for each issue."
```

### 方式 2: 从文件读取（长/复杂 prompt）

当 prompt 太长、含特殊字符或中文时，先写文件再展开：

```powershell
codex exec --full-auto -o C:\tmp\output.txt (Get-Content C:\tmp\prompt.txt -Raw)
```

或用管道模式：

```powershell
Get-Content C:\tmp\prompt.txt | codex exec --full-auto -o C:\tmp\output.txt -
```

### 何时需要文件？

| 场景                         |     直接传字符串      | 用文件 |
| ---------------------------- | :-------------------: | :----: |
| 英文短指令（< 200 字）       |           ✅           |        |
| 英文长指令（多段详细描述）   |                       |   ✅    |
| 包含中文                     | ❌ PowerShell 可能崩溃 |   ✅    |
| 包含引号/特殊字符            |      ❌ 转义困难       |   ✅    |
| `codex exec review` 附加说明 |      ✅ 通常很短       |        |

### 方式 3: 专用代码审查命令

Codex 有内置的 `review` 子命令，专为代码审查设计：

```powershell
# 审查所有未提交的改动
codex exec review --full-auto --uncommitted -o C:\tmp\review_output.txt

# 审查与某个分支的差异
codex exec review --full-auto --base main -o C:\tmp\review_output.txt

# 审查某个特定 commit
codex exec review --full-auto --commit abc123 -o C:\tmp\review_output.txt

# 附加自定义审查指令
codex exec review --full-auto --uncommitted -o C:\tmp\review_output.txt "Focus on type safety and error handling"
```

### ❌ 避免

- **`--file` 参数不存在**：网上有些文章提到 `--file PROMPT.md` 但实际 CLI 不支持，用管道替代
- **不要在 PowerShell 中内联长文本或中文 prompt**：会导致控制台缓冲区崩溃（`System.ArgumentOutOfRangeException`）
- **不要用 `--approval-mode` 参数**：正确的参数是 `--full-auto`

## 经过实机验证的参数

| 参数                               | 说明                                           |
| ---------------------------------- | ---------------------------------------------- |
| `--full-auto`                      | 自动批准所有文件读取和命令执行（代码审查必须） |
| `-o, --output-last-message <file>` | 将最终回答保存到文件（终端输出很混乱）         |
| `-` (作为 PROMPT 参数)             | 从 stdin 读取 prompt                           |
| `-m, --model <model>`              | 指定模型（如 `-m o3`）                         |
| `-i, --image <file>`               | 附加图片到 prompt                              |
| `-C, --cd <dir>`                   | 指定工作目录                                   |
| `--json`                           | 以 JSONL 格式输出事件（适合程序化解析）        |
| `--ephemeral`                      | 不持久化会话文件                               |

## 标准工作流

### Step 1: 确认 Codex CLI 可用

```powershell
// turbo
codex --version
```

### Step 2: 写 prompt 文件（英文）

**代码审查 prompt 模板：**

```text
Review all Python source code under src/ directory of this project.
Find all bugs, logic errors, config inconsistencies, type mismatches.

Focus on:
1) [specific area] - any missing fields or type errors
2) [specific area] - schema consistency between modules
3) [specific area] - dead code or stale references
4) [specific area] - runtime errors that would crash

For each issue found, provide:
- Severity: High/Medium/Low
- File and line number
- Description of the problem
- Suggested fix

Output format: structured list grouped by severity.
```

### Step 3: 执行 Codex

```powershell
Get-Content C:\tmp\codex_prompt.txt | codex exec --full-auto -o C:\tmp\codex_output.txt -
```

### Step 4: 等待完成

使用 `command_status` 工具轮询（`WaitDurationSeconds=120`）。

终端输出中的工作状态标识：
- `thinking` — Codex 正在推理
- `🌐 Searching the web...` — 搜索文档
- `exec` — 执行命令（读文件、跑测试等）

### Step 5: 读取结果

使用 `view_file` 读取 `-o` 指定的输出文件。**不要解析终端输出**，太混乱。

### Step 6: 交叉验证

对 Codex 的每条发现：
1. **检查实际代码**：确认引用的行号和代码片段是否准确
2. **独立判断**：评估是否为真正的 bug
3. **标记分歧**：记录同意和不同意的点

### Step 7: 多轮讨论（可选）

如有争议，发起第二轮对话。Codex 可能会：
- 搜索官方文档验证
- **编写并运行测试脚本**来验证行为
- 修正自己之前的判断

**第二轮 prompt 模板：**

```text
I found these items in a code review. I need you to verify specific findings:

1. Finding #X: [describe the specific claim and your doubt]
2. Finding #Y: [describe another specific claim]

Please answer based on [framework/API] behavior, with evidence.
```

### Step 8: 生成统一报告

整合双方共识，标注发现者、共识状态、是否经过实机验证。

## AGENTS.md 上下文

Codex 会自动读取项目根目录下的 `AGENTS.md` 文件作为编码规范和项目上下文。如果项目有特殊约定（命名规范、技术栈、测试要求），写在 `AGENTS.md` 中可以提升 Codex 的审查质量。

## Codex 的能力

- 读取项目中的所有文件（需要 `--full-auto`）
- 运行命令（pytest、编译、甚至 ABAQUS 仿真引擎）
- 搜索互联网查找文档
- 编写临时脚本并执行来验证假设

## 时间预估

| 任务复杂度           | 预计时间  |
| -------------------- | --------- |
| 验证 2-3 个具体发现  | 1-3 分钟  |
| 审查 20+ 文件项目    | 3-8 分钟  |
| 含实机测试和文档搜索 | 5-15 分钟 |

## 完整示例

```python
# 1. 写 prompt 到临时文件
write_to_file("/tmp/codex_prompt.txt", "Review all Python source code ...")

# 2. 执行 Codex（后台运行）
run_command('codex exec --full-auto -o C:/tmp/codex_output.txt (Get-Content C:/tmp/codex_prompt.txt -Raw)')

# 3. 轮询等待
command_status(CommandId=..., WaitDurationSeconds=120)

# 4. 读取结果
view_file("C:/tmp/codex_output.txt")

# 5. 交叉验证 Codex 引用的代码
view_file("src/module.py", StartLine=100, EndLine=120)

# 6. 如有分歧，发起第二轮
write_to_file("/tmp/codex_prompt2.txt", "Verify finding #X: ...")
run_command('codex exec --full-auto -o C:/tmp/codex_output2.txt (Get-Content C:/tmp/codex_prompt2.txt -Raw)')
```
