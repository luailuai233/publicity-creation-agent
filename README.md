<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/c5096076-db7a-47d8-afb9-7519e8c810b1" />

一个面向高校社团宣传场景的 LLM-driven Agent。用户只需创建项目、上传活动资料、提供参考案例并明确创作目标，Agent 即可根据当前项目状态自主选择工具，完成素材解析、事实核验、案例分析、创意策划、推文生成与质量检查，实现从活动资料到宣传稿件的完整创作闭环。

与传统固定流程的 AI 写作工具不同，本项目采用 **LLM Tool Calling + Python Runtime** 架构：由大模型判断当前应该调用什么工具、下一步做什么；由 Python 负责工具执行、参数校验和业务安全控制。当遇到事实冲突或需要用户选择创作策略时，Agent 会主动暂停并等待用户操作。

## 核心功能

- **活动素材解析：** 支持上传活动文档及图片，提取可用于宣传创作的原始信息。
- **事实核验：** 将活动素材转化为可追溯事实卡，识别信息缺失、来源不足及事实冲突。
- **参考案例分析：** 支持粘贴文章、输入公开网页链接或上传截图，提炼案例的开头、叙事结构、情绪表达和创作方法。
- **自主创意策划：** 根据活动事实和参考案例，生成多个差异化宣传策略，由用户选择最终方向。
- **智能推文生成：** 根据已确认事实和选定策略生成宣传稿件，保留事实引用关系。
- **质量检查与导出：** 检查事实引用、内容完整性、相似表达及潜在风险，支持 Markdown 导出。

## Agent 架构设计
项目采用模型驱动的自主工具调用架构，不再依赖 Python 预先写死完整执行顺序。

用户创作目标
     │
     ▼
AgentRunner
     │
     ▼
读取 ProjectSnapshot
     │
     ├── 当前项目状态
     ├── 用户创作目标
     ├── 历史执行记录
     └── 当前可用工具
     │
     ▼
LLM Agent（Function Calling）
     │
     ▼
模型自主选择工具及参数
     │
     ▼
Python Tool Runtime
     │
     ├── 工具白名单校验
     ├── 参数 Schema 校验
     ├── 业务执行条件检查
     ├── 幂等与调用预算控制
     └── 工具执行与结果持久化
     │
     ▼
Tool Result 返回模型
     │
     ▼
模型重新判断下一步
     │
     ├── 继续调用业务工具
     ├── 请求用户确认
     └── 完成任务


### 模型自主决策与工具调用

基于 OpenAI-compatible Function Calling 实现模型与 Python 工具之间的交互。

Agent 提供六类业务工具：

| 工具 | 功能 |
|---|---|
| `parse_materials` | 活动素材解析 |
| `validate_facts` | 活动事实提取与核验 |
| `analyze_references` | 参考案例分析 |
| `plan_strategies` | 宣传创意策略生成 |
| `generate_content` | 宣传稿件生成 |
| `check_quality` | 稿件质量检查 |

另外提供两个控制工具：

- `ask_user`：遇到事实冲突、关键资料缺失或需要用户选择时，主动发起人工确认。
- `finish_run`：模型判断任务完成后申请结束，由 Python 执行最终完成条件检查。

每轮执行后重新读取项目状态，将工具执行结果反馈给模型，由模型决定下一步。Python 不负责规定固定工具顺序，但通过工具白名单、参数校验、执行条件及任务预算保证运行安全。

### 人机协作机制

- 高置信度且有来源的普通事实可以自动确认，异常事实集中交由用户处理。
- 生成的推荐策略不会自动选中，必须由用户主动选择。
- 关键事实冲突未解决时，不允许进入依赖这些事实的稿件生成环节。
- 支持任务暂停、用户补充信息及恢复执行。

## Prompt Engineering 与 Badcase 迭代

针对 Agent 决策、工具调用和专业内容生成等不同任务，建立三层 Prompt 体系：

1. **Agent System Prompt：** 约束整体任务目标、决策原则、工具使用方式及完成条件。
2. **Tool Description：** 描述工具用途、适用场景、前置条件和执行限制，辅助模型准确选择工具。
3. **Task Prompt：** 分别优化事实提取、案例分析、策略生成、正文创作和质量检查等专业任务。

针对工具路由错误、参数格式异常、事实边界混淆、人机协作缺失等问题，构建23条 Badcase 测试用例（21条正式计分、2条诊断），经过3轮问题定位、Prompt 优化和回归验证，持续改善模型决策与工具调用表现。

测试集位置：`tests/evals/`

## 技术栈

| 模块 | 技术 |
|---|---|
| 后端框架 | FastAPI |
| 前端 | Jinja2 + HTMX |
| ORM | SQLAlchemy |
| 数据库 | SQLite |
| AI 接入 | OpenAI-compatible Chat Completions / Function Calling |
| 数据校验 | Pydantic |
| 数据迁移 | Alembic |
| 测试 | Pytest |
| 部署 | Docker / Render |

## 本地运行

**环境要求：** Python 3.11 或 3.12。

### Windows

推荐使用仓库提供的包装脚本：

```powershell

.\scripts\setup.ps1

.\scripts\dev.ps1
```

打开浏览器访问：

`http://127.0.0.1:8000`

首页支持创建新项目，也可以载入示例项目体验完整创作流程。

测试：

```powershell
.\scripts\test.ps1 -q

.\scripts\e2e.ps1 -q
```

### macOS / Linux

```bash
export WORKBENCH_ROOT="$PWD/.runtime"

mkdir -p "$WORKBENCH_ROOT/storage"

export DATABASE_URL="sqlite:///$WORKBENCH_ROOT/storage/app.db"

pip install -r requirements.lock.txt

python -m alembic upgrade head

python -m uvicorn workbench.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --workers 1
```

运行数据保存在 `WORKBENCH_ROOT` 指定的目录中：

- `storage/`：SQLite 数据库及运行数据。
- `exports/`：Markdown 导出文件。
- `test-results/`：测试产物。

## 模型配置

### 默认 Mock 模式

项目默认使用确定性 `MockAIProvider`，无需 API Key 或付费模型即可体验产品流程。

Mock 模式通过预设逻辑模拟工具选择和执行过程，适合本地开发、界面演示及工作流验证，但不能代替真实模型的工具选择能力评估。

### 接入真实模型

项目内置 `OpenAICompatibleProvider`，支持接入 DeepSeek 或其他兼容 Chat Completions 和 Function Calling 的模型服务。

在启动环境变量或 Render 的 Environment 中配置：

```env
AI_PROVIDER=openai_compatible

AI_BASE_URL=https://你的兼容服务/v1

AI_API_KEY=你的服务端密钥

AI_MODEL=文本模型名称

AI_VISION_MODEL=可选的视觉模型名称
```

配置完成后重新启动或部署服务。

真实模型模式下：

- Agent 决策通过 Function Calling 完成。
- 模型根据项目状态自主选择工具。
- 案例分析、策略生成、正文创作及质量检查调用真实模型服务。
- API Key 仅在服务端读取，不暴露给前端。

**注意：** 模型服务必须支持 `tools`、`tool_choice` 和 `tool_calls` 等 Function Calling 协议。仅支持普通文本对话的 API 或中转站无法实现真正的模型自主工具调用。

认证错误不会自动重试；网络错误、429 和 5xx 最多重试一次；结构错误最多进行一次修复。模型调用失败不会静默退回 Mock 模式。

## Badcase 测试与评估

项目提供独立的 Agent 工具选择测试集，用于验证模型是否能够根据不同项目状态正确决定下一步行动。

测试覆盖：

- 工具选择：是否根据素材、事实和稿件状态选择合适工具。
- 参数与结构：工具调用参数是否符合 Schema。
- 人机协作：是否正确识别事实冲突及用户确认需求。
- 流程控制：是否出现过早结束、重复调用或跳过必要步骤。
- 安全门禁：是否遵守工具执行条件和业务约束。

运行离线数据校验：

```bash
python tests/evals/validate_tool_selection_dataset.py
```

测试指定场景：

```bash
python tests/evals/evaluate_tool_selection.py \
  --case-ids ROUTE-001 ROUTE-015
```

运行完整正式计分集：

```bash
python tests/evals/evaluate_tool_selection.py
```

评估结果保存至：

`tests/evals/results/`

可用于对比不同模型及 Prompt 版本的工具选择表现，并将新发现的问题持续补充到 Badcase 集合中。

## 数据与安全设计

- 活动事实与参考案例分表、分服务、分模型上下文保存，避免参考案例中的信息被误用为真实活动事实。
- 图片理解不推断人物身份，低置信度结果交由用户确认。
- 硬性风险不能仅靠用户确认绕过；软性风险需要解决或记录说明。
- 模型只能调用白名单工具，不能直接执行任意 Python 代码。
- 工具参数经过 Schema 和业务条件校验，项目及运行标识由后端控制。
- 支持工具执行记录、消息历史持久化、异常中断及任务恢复。
- 公开部署版本不提供账号隔离，禁止上传个人隐私、未公开敏感材料及其他不适合公开的数据。


## Docker 部署

```bash
docker build -t publicity-workbench .

docker run --rm \
  -p 8000:8000 \
  -e WORKBENCH_ROOT=/data \
  -v ./container-data:/data \
  publicity-workbench
```

容器启动时自动执行 Alembic 数据库迁移，再启动单 Worker Uvicorn 服务。

当前 SQLite 架构面向单实例部署，不支持直接横向扩展为多个应用实例。

## 项目文档

- [完整 Demo 演示流程](docs/demo-script.md)
- [自动化验收记录](docs/acceptance-record.md)
- [Badcase 测试集说明](tests/evals/README.md)

---

**项目定位：** 面向高校社团宣传场景的自主式 AI 创作 Agent，重点探索大模型自主工具调用、动态任务决策、Prompt 迭代及人机协作在实际内容生产流程中的应用。
