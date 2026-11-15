# 热点驱动宣传创作工作台（Python Demo）

这是一个本地优先、结构化模拟 AI 的单 Agent Demo。用户准备活动资料、参考资料和创作目标后，只需点击一次“开始自主创作”；Agent 会读取项目状态，自主选择六个白名单工具，生成三个策略并自动推荐，继续完成标题、大纲、正文和质量检查。关键事实冲突才会暂停询问，刷新或重启后可从已完成步骤继续。

默认 `MockAIProvider` 不调用任何外部 API。Mock 只替代模型推理；Agent 的 Planner、工具注册表、执行状态、调用上限、暂停恢复、项目记忆和数据隔离均为真实实现。

## Windows 本地运行

只使用以下包装脚本，不要直接运行 `pip`、`pytest` 或 `uvicorn`：

```powershell
cd D:\aipm\demo
.\scripts\setup.ps1
.\scripts\dev.ps1
```

打开 `http://127.0.0.1:8000`，载入 Demo、处理示例事实冲突，然后进入 Agent 工作台点击“开始自主创作”。测试命令：

```powershell
.\scripts\test.ps1
.\scripts\e2e.ps1
```

## D 盘写入保证

包装脚本把虚拟环境、pip 缓存、Python 字节码、临时目录、Playwright 浏览器目录、Edge 磁盘缓存、SQLite、上传文件、导出和测试结果全部定向到 `D:\aipm\demo`。程序不创建 C 盘运行时文件。唯一读取的 C 盘资源是系统已安装的 Edge 可执行文件和 Codex 工具自身；浏览器 profile/cache 仍在本项目 `.runtime` 下。

运行数据位于 `storage/`，Markdown 位于 `exports/`，测试产物位于 `test-results/`。删除这些目录中的内容即可清理运行数据；保留 `.gitkeep` 即可。Demo 重置只删除数据库中 `is_demo=True` 的项目及经路径校验的项目上传子目录，不触碰普通项目。

## Agent 架构与故障注入

开发环境可向 `POST /api/demo/faults` 发送结构化故障队列，例如 `{"faults":{"reference":["schema_error","schema_error"]}}`。生产环境禁用该接口。

架构为 FastAPI + Jinja/HTMX + SQLAlchemy/SQLite + 本地文件存储。`AgentRunner` 每轮重新读取 `ProjectSnapshot`，由状态 Planner 决定下一个工具；六个工具分别负责资料解析、事实校验、案例分析、策略规划、内容生成和质量检查。单次 Run 最多调用 12 次工具，模型结构错误最多重试一次，正文最多自动修订一次。

## 如何接入真实模型 API

本版本只交付 Provider 工厂和接口契约，不内置会联网的 Provider。把 `.env.example` 复制为项目内 `.env` 时保持 `AI_PROVIDER=mock` 即可离线运行。不要把密钥写入源码、数据库、日志或浏览器。

要接 OpenAI 或其他兼容服务，请新增 `workbench/ai/openai_compatible_provider.py`，实现 `AIProvider` 的五个方法：

- `analyze_reference(raw_text, source_id)`；
- `generate_strategies(facts, method_summaries, project_name)`；
- `generate_outline(strategy, facts)`；
- `generate_draft(title, outline, strategy, facts)`；
- `check_quality(content, facts, method_summaries)`。

每个方法必须返回现有 `AIEnvelope[T]`，要求模型按对应 Pydantic/JSON Schema 输出；把来源 ID 或事实 ID 原样带回，超时和结构错误只重试一次。模型不得获得数据库 Session、文件系统对象、Shell 或 Tool Registry。正文生成只传已确认 FactCard，不传参考案例原文。

实现完成后，在 `workbench/ai/factory.py` 的 `openai_compatible` 分支构造该 Provider，再配置：

```text
AI_PROVIDER=openai_compatible
AI_BASE_URL=https://你的兼容服务/v1
AI_API_KEY=服务端密钥
AI_MODEL=模型名称
```

建议先写一个使用本地假 HTTP 服务的契约测试，验证 JSON Schema、超时、一次重试、错误码和密钥脱敏，再进行最小连通性测试。当前版本若设置 `AI_PROVIDER=openai_compatible` 会明确拒绝启动，不会静默回退或伪装成真实调用。

P1 暂不包含多人协作、云存储、真实图片理解、真实热榜抓取和多实例任务队列。

## 可选 Docker（单实例）

```powershell
docker build -t publicity-workbench .
docker run --rm -p 8000:8000 -v D:\aipm\demo\storage:/app/storage -v D:\aipm\demo\exports:/app/exports publicity-workbench
```

SQLite 方案仅支持单实例。Docker 路径不承诺宿主机 C 盘零写入（Docker Desktop 自身由宿主配置决定），严格 D 盘约束请使用上述 Windows 包装脚本。
