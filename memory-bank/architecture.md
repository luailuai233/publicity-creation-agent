# 热点驱动宣传创作工作台架构记忆

> 状态：任务 1–40 与免费公开站增量均已完成内部验证，等待用户部署验收
> 记录日期：2026-11-22
> 记录原则：只描述仓库中已经存在的实现；目标能力以 `design-document.md` 和 `implementation.md` 为准

## 权威文档

- 产品行为与范围：`memory-bank/design-document.md`
- 技术选型与约束：`memory-bank/tech-stack.md`
- 实施任务与验证要求：`memory-bank/implementation.md`
- 当前实现事实：`memory-bank/architecture.md`
- 交付状态与最近验证：`memory-bank/progress.md`

出现冲突时，先以产品设计确定行为，再以技术栈确定实现边界，最后按实施计划拆分任务；不得把尚未通过测试的目标能力写成当前架构。

## 当前模块边界

| 区域 | 当前主要位置 | 当前职责 |
| --- | --- | --- |
| 应用装配 | `workbench/main.py`、`workbench/settings.py` | 创建 FastAPI 应用、装配数据库、Provider、Agent Runner、API 与页面路由，并在启动时恢复任务 |
| 服务端页面 | `workbench/web/`、`workbench/templates/`、`workbench/static/` | Jinja2 页面、HTMX 片段、复古工作台样式和少量浏览器交互 |
| JSON API | `workbench/api/` | 项目、素材、事实、案例、策略、稿件、质检、导出、Job 和 Agent Run 接口 |
| Agent 内核 | `workbench/agent/` | 构造项目快照、确定下一动作、调用白名单工具、保存步骤、暂停恢复和启动恢复 |
| 模型抽象 | `workbench/ai/` | `AIProvider` 契约、Pydantic 结构、默认 Mock Provider、故障注入和 Provider 工厂 |
| 领域服务 | `workbench/materials/`、`facts/`、`references/`、`strategies/`、`drafts/`、`quality/`、`exports/` | 各业务阶段的校验、持久化和产物生成；活动事实与参考案例保持分离 |
| 后台任务 | `workbench/jobs/` | 进程内素材解析任务、状态持久化和异常启动恢复 |
| 持久化 | `workbench/db/`、`alembic/` | SQLAlchemy 模型、Session、SQLite 和 Alembic 迁移；当前最新迁移为 `0007_quality_resolution` |
| 本地文件 | `workbench/storage/`、`workbench/runtime_paths.py` | 项目文件边界、上传、导出及运行目录集中计算 |
| 部署入口 | `Dockerfile`、`render.yaml`、`scripts/container-start.sh` | Python 3.12 容器、免费 Render Blueprint、迁移、单 worker 启动和统一临时数据目录 |
| 自动化验证 | `tests/unit/`、`tests/integration/`、`tests/e2e/`、`.github/workflows/ci.yml` | 规则、服务、恢复、API、浏览器主流程与三系统 CI 验证 |

当前部署单位是一个 Python 模块化单体：单个 Uvicorn 进程同时承载页面、API、进程内任务和 Agent；SQLite 与项目文件保存在 `WORKBENCH_ROOT`。本地默认使用仓库目录，免费 Render 使用 `/tmp/workbench`，后者允许在实例重启或重部署后清空。

## 运行命令

正常开发与验证只使用仓库包装脚本：

- 初始化环境与迁移：`.\scripts\setup.ps1`
- 启动本地页面：`.\scripts\dev.ps1`
- 单元与集成测试：`.\scripts\test.ps1`
- 浏览器端到端测试：`.\scripts\e2e.ps1`

脚本通过 `scripts/runtime-env.ps1` 把缓存、临时文件、浏览器文件、SQLite、上传、导出和测试结果定向到 `D:\aipm\demo`。当前开发地址为 `http://127.0.0.1:8000`。

项目解释器范围固定为 Python 3.11 或 Python 3.12；包装脚本只接受项目内 `.venv` 的解释器，并校验解释器版本和路径。`scripts/setup.ps1` 从 `requirements.lock.txt` 安装锁定依赖，必要时先通过 `ensurepip` 初始化包管理器。部署保持单 Uvicorn worker，避免进程内任务和 SQLite 写入被多个 worker 重复执行。

容器使用 `requirements-prod.lock` 的生产依赖和 Python 3.12。`scripts/container-start.sh` 从 `PORT` 读取监听端口，派生与 `WORKBENCH_ROOT/storage/app.db` 一致的 `DATABASE_URL`，先运行 Alembic，再以一个 Uvicorn worker 启动。生产环境给所有响应加入基础安全头，并在进入业务路由前按 `Content-Length` 拒绝超过 `MAX_REQUEST_BODY_BYTES` 的请求；当前默认总请求上限为 25 MiB。

## 数据流

1. Web 页面或 JSON API 创建项目并接收活动素材。
2. 素材服务将文件保存到项目目录；DOCX 按非空段落和表格行、PDF 按页和文本块写入可定位 `SourceChunk`，Job Runner 与 Agent 工具共用同一解析器。
3. 图片优先交给可选视觉模型；未配置、失败、低置信度或涉及身份推断时进入 `NEEDS_REVIEW` 并要求人工场景说明，视觉推断不能直接成为默认确认的关键事实。
4. 事实服务从活动素材生成事实卡和来源关系；参考案例支持文本、公开链接和截图，链接读取器拒绝内网/保留地址并限制重定向、类型、大小和超时，随后用标准库 HTML Parser 删除脚本、样式和导航并提取可读正文；截图由 API 保存到服务端生成的项目边界路径，浏览器不能提交服务器路径。案例始终不进入事实表。
5. 删除案例时同步删除项目内保存的原文或截图并通过级联使分析失效；读取失败会保留原 URL 供人工补充。
6. 策略服务读取可用事实与案例方法摘要，生成三个候选方案；推荐不等于选择，用户必须主动选择后 Planner 才继续。策略在叙事主角、开头方式、结构组织三个维度中至少两个维度不同。
7. 稿件服务根据选定策略生成标题、大纲、正文和事实引用；段落级改写只发送目标段落、改写要求与允许事实，应用前检查段落锁定和事实锁定，并只保存最近一次 Agent 改写的撤销快照。人工编辑会立即使该快照失效。
8. 质检服务结合事实、案例文本和规则生成问题；隐私、事实冲突、无来源身份或引语属于不能仅确认的硬问题，相似表达和一般语气属于可记录说明后接受的软问题。导出会重新查询当前质检状态：任何 OPEN 硬问题不可绕过，软问题必须已解决或以非空说明标记 ACCEPTED。Markdown 默认附创作说明和待确认清单，纯文本默认仅含正文。
9. 页面以 1.5 秒间隔轮询数据库中的 Agent Run 状态，显示阶段、下一动作、工具耗时和错误码；在终态或 `WAITING_USER` 停止，刷新后仍以数据库状态恢复界面。
10. 发布页与导出服务共享同一导出门禁判断，因此按钮可用状态不会早于后端实际放行状态。
11. 灵感页的案例分析成功后由浏览器刷新服务端页面；页面选择最近一个已有分析的案例，将数据库中的标题钩子、情绪、结构、图片作用、可迁移方法和禁用表达渲染到中央及右侧窗口。没有分析时只显示等待提示，不使用固定示例冒充真实结果。
12. 灵感页与策略空状态共用策略生成入口。服务端同时检查最小活动事实集合与至少一个可用案例方法：条件满足时允许调用既有策略生成 API 并在成功后进入编辑提案；条件不足时只提供返回 Agent 的恢复动作，避免发起注定失败的模型请求。
13. 事实冲突不再只以内部组 ID 呈现。冲突读取投影会为每个候选事实装配可读值、文件名、页码或段落与原文片段；Planner 将这些信息写入有类型的单选问题，事实页和素材页复用同一投影并允许直接选择候选值。对已经持久化的旧版等待问题，Agent 页面在读取时动态补全候选项，因此刷新即可恢复可读交互，无需重跑 Agent。
14. 在事实页或素材页独立解决冲突时，接口会同步消费活动中 `WAITING_USER` 运行里的对应冲突问题并更新检查点 revision；仍有问题时继续等待剩余问题，已无问题时转为 `QUEUED` 并重新调度 Runner，避免用户返回 Agent 后遇到过期回答错误。
15. 素材解析完成后会按原始文件名推断流程、采访、发言稿、图片和笔记分类，弥补 DOCX/PDF 解析器只能返回通用类别的限制；旧数据在事实确认时也会按原文件名计算有效类别。引语抽取只接受发言稿或带明确归属提示的采访片段，避免把加引号的活动标题误当人物原话。
16. 黄色待确认事实提供“采用”和“忽略”两个显式动作，批量继续不会擅自确认引语候选。Agent 的 `MISSING_FACTS` 回答会生成一份 `用户补充事实.txt` 逻辑素材、来源片段和已确认 EVENT 事实，确保人工回答真正改变业务快照而不是只写入决策备注。

所有模型能力通过 `AIProvider` 调用。默认 `MockAIProvider` 可离线运行；选择 `openai_compatible` 时必须同时提供服务地址、API Key 和文本模型，缺项会在启动装配前失败，真实 Provider 失败不会静默回退为 Mock。HTTP transport 分别限制 connect、read、write 和 pool timeout，并只对网络错误、429 与 5xx 重试一次。模型输出经 Pydantic 严格校验，结构错误最多修复一次；认证、限流、网络、请求、内容和结构错误使用稳定错误码。案例分析与策略实体会保存 `AIEnvelope.is_demo`，真实 Provider 结果不会再被硬编码为模拟来源。案例拆解不得接收活动事实，策略不得接收参考原文，所有返回的事实 ID 必须属于当前输入集合。

OpenAI-compatible 请求的系统消息会明确要求仅返回 JSON 对象，并设置 4096 token 的结构化输出预算；适配器优先使用 `response_format=json_object`，如果兼容端点以 4xx 拒绝该可选参数，则仅移除该参数重试一次并继续用 Pydantic 校验结果。案例拆解额外提供与本地 Schema 一致的完整 JSON 示例；首次校验失败时，第二次请求携带模型的无效输出和具体校验错误，让模型定向修复而不是盲目重跑。案例分析 API 会把 Provider 异常转换为稳定的中文 JSON 错误与 502 状态，浏览器不会再把服务器错误页误当 JSON 解析。

策略生成同样提供与本地 Schema 一致的完整 JSON 示例，并明确要求一次返回恰好三个方案。策略 API 捕获统一的 Provider 异常并返回稳定中文 JSON 与 502 状态；浏览器只在成功持久化三个策略后跳转，失败时保留当前页面并把错误显示在底部任务栏。

## Agent 决策流

1. API 创建 `AgentRun`，Runner 将状态从 `QUEUED` 推进到 `RUNNING`。
2. `build_project_snapshot` 从数据库构造最小项目快照。
3. `Planner` 返回 `CALL_TOOL`、`ASK_USER`、`COMPLETE` 或 `FAIL`。
4. `CALL_TOOL` 只能从 `ToolRegistry` 取得白名单工具；执行前写入 `PROCESSING` 的 `AgentStep` 和输入指纹。
5. 工具完成后，Runner 比较项目 revision；输入已变化时丢弃旧结果并重新规划，否则保存结果摘要。
6. `ASK_USER` 将运行置为 `WAITING_USER` 并持久化问题组及项目 revision；用户必须一次回答全部异常项。接口校验问题 ID、完整性和 revision，先持久化业务变更再恢复 Agent，任何失败都保持等待状态。
7. 工具异常、调用上限、规划循环上限、暂停或取消都会形成明确终态或可恢复状态。
8. 应用启动时扫描可恢复的 Job 和 Agent Run，并重新调度需要继续的运行。
9. 同一人工中断中的全部回答在一个数据库事务内应用；事实冲突、事实修订和案例补充均先 flush，只有消息记录和运行恢复状态也准备完成后才统一 commit。任一回答失败会回滚本批全部变更，避免部分落库后仍停留在旧问题组。

事实使用规范化值和稳定 fingerprint 去重；高置信且来源完整的非敏感事实可自动确认。Planner 以互补的最小事实集合为门禁，只对 Agent 标出的异常项提问，并将本轮问题一次问完。

## 持久化与恢复

- SQLite 保存项目、素材、来源、事实、案例、策略、稿件、质检、Job、Agent Run、Agent Step 和消息。
- 每个 SQLite 连接统一启用 `foreign_keys=ON`、`journal_mode=WAL` 和 `busy_timeout=5000`；服务层继续使用短 Session，不允许在模型网络调用期间持有写事务。
- 长操作前先保存运行或步骤状态；应用启动时把可恢复记录重新加入进程内执行。
- 项目 revision 用于识别执行期间发生的用户修改并丢弃过期 Agent 结果。
- 当前最新数据库迁移是 `0007_quality_resolution`；`0005_fact_identity` 保存事实规范化值与稳定指纹，`0006_authoring_controls` 保存策略主角、稿件锁定与单次撤销快照，`0007_quality_resolution` 保存质检处置策略、说明、风险片段和建议。

## 已知缺口

- 公开站无登录且采用单用户语义：所有访客共享项目、文件和模型额度，不提供隐私隔离、多人协作、多 worker 调度或云端高可用。
- 免费 Render 文件系统不持久，连续 15 分钟无访问会休眠；休眠、实例重启或重新部署后 SQLite、上传与导出清空，冷启动可能约一分钟。
- 图片理解依赖可选视觉模型；未配置或低置信度时只进入人工说明流程，不提供本地 OCR 生产级保证。
- 相似表达检查采用稳定规则和模型建议，属于发布风险提示，不替代人工版权或法律判断。
- 当前页面以桌面端为目标；低于 1100 像素会提示使用桌面宽度，不提供完整移动端重排。
- 测试仍会输出第三方 `pytest-asyncio`、Starlette 以及项目 `datetime.utcnow()` 的弃用警告，但不影响本轮功能和验收结果。

## 验证基线

- 已完成：对仓库结构、应用装配、Agent Runner、运行脚本和迁移文件进行只读检查。
- 2026-11-20：用户在 `D:\aipm\demo` 执行 `.\scripts\test.ps1 tests/unit/test_memory_bank_contract.py -q`，结果为 `4 passed in 0.04s`。
- 本次验证确认五个 memory-bank 文件存在、三份权威文档非空、架构与进度文档已初始化，并确认 `CLAUDE.md` 与 `AGENTS.md` 的三条结尾规则。
- 2026-11-21：项目 `.venv` 已切换为 Python 3.12.14；Alembic 从 Agent 基线 `0003_agent_runtime` 继续升级到当前迁移 `0005_fact_identity`。
- 任务 2–4 的运行路径、依赖锁定和 SQLite 专项测试已在 `.\scripts\test.ps1` 测试入口下通过；完整回归结果记录在 `progress.md`。
- 2026-11-21：用户确认任务 2–11 批次测试通过；真实 Provider 的配置、错误映射、一次重试、结构修复与本地假 transport 契约已验收。
- 2026-11-22：表单导航与缓存修复后的 `.\scripts\test.ps1 -q` 完整通过，结果为 `219 passed`；`.\scripts\e2e.ps1 -q` 完整通过，结果为 `7 passed`。
- 2026-11-22：Ruff 检查为 `All checks passed!`，Alembic 当前为 `0007_quality_resolution (head)`，浏览器证据保存到 `test-results/acceptance/`。
- 2026-11-22：真实模型案例拆解兼容性修复的 Provider、隔离与 API 专项回归为 `34 passed`，Ruff 为 `All checks passed!`；完整套件在 Codex 沙箱的 Windows `TestClient` 事件循环启动阶段阻塞，未将该环境中断记录为全量通过。
- 2026-11-22：按 DeepSeek JSON Output 契约补充示例、输出预算和带校验详情的修复轮次后，AI、案例隔离与 API 专项回归为 `36 passed`，Ruff 为 `All checks passed!`。
- 2026-11-22：灵感页真实分析结果渲染的模板回归为 `1 passed`；浏览器回归已更新，但 Codex 沙箱因 Uvicorn 测试服务器 socket 权限无法启动而未在该环境完成浏览器执行。
- 2026-11-22：策略生成入口、DeepSeek 三策略结构示例、策略 API 错误映射和既有策略领域服务专项回归为 `10 passed`；`node --check workbench/static/js/app.js` 与相关 Ruff 检查均通过。浏览器主流程已改为从灵感页显式生成策略，但本轮未把 Codex 沙箱中的 Uvicorn socket 限制记为浏览器通过。
- 2026-11-22：冲突候选值与来源展示的 Planner、快照和事实状态机专项回归为 `28 passed`；冲突选择控件、批量回答原子性与等待运行同步回归为 `3 passed`；应用装配确认 58 条路由，JavaScript 语法检查与 Ruff 均通过。通过本机正在运行的真实项目页面验证 Agent、事实和素材页均返回 200，Agent 输出 2 个单选项，事实页与素材页各输出 2 个选择按钮，并包含“36人”“12人”、可读提示和来源信息；沙箱内 `TestClient` 生命周期仍会阻塞，未把该环境问题记为页面测试通过。
- 2026-11-22：素材分类、引语抽取、待确认事实动作和人工补充事实专项回归并入相关事实/Agent/Job 套件，共 `38 passed`；JavaScript 语法与 Ruff 通过。真实本地事实页返回 200，输出 2 组“采用/忽略”按钮、“引语候选”文案和静态版本 `20261122-7`。
- 2026-11-22：生产配置从空库执行全部迁移并以单 worker Uvicorn 启动，`GET /health` 返回 200 与预期安全头；Docker Desktop 守护进程未运行，因此没有执行本机镜像构建。
- 2026-11-22：GitHub 发布体检确认 Docker 镜像显式包含 `data/samples`，三系统 CI 在迁移前创建运行目录并让 `DATABASE_URL` 与 `WORKBENCH_ROOT` 指向同一 SQLite；对应部署契约测试 `2 passed`，Ruff 为 `All checks passed!`。

## 新增架构洞察

- memory-bank 是项目治理层，不是运行时代码：设计文档规定产品行为，技术栈文档规定工程边界，实施计划规定交付顺序，本文件只记录已存在并得到验证的实现事实。
- 数据库是页面刷新与 Agent 恢复的状态事实来源；进程内任务负责执行，但不能成为唯一状态存储。
- 当前 Agent 的核心反馈循环是“数据库快照 → Planner 决策 → 白名单工具 → 持久化步骤 → 重建快照”，而不是不可变的模型调用流水线。
- Agent 工作流的阶段目标固定，但执行路径由当前数据库状态决定；人工中断不是旁路，回答必须先转化为可恢复的业务状态，再重新规划。
- 策略推荐只帮助排序，不能替代用户选择；局部改写和单步撤销都通过稿件 revision 防止覆盖并发人工修改。
- 质检的关键边界是“硬问题必须修改或补来源、软问题可附说明接受”，不能用统一的风险确认开关代替分类处置。
- UI 的可用状态必须复用领域门禁，而不是在模板中维护一套较弱的近似条件；发布页和导出服务现共用 `export_block_reason`。
- 结构化日志只承担运维关联与错误定位，用户可见执行轨迹必须继续读取数据库中的 Agent Step，不能把服务器日志当成产品状态。
- 开源交付边界由忽略清单、项目内运行目录、三系统 CI 和脱敏样例共同保证；真实密钥和用户运行数据不进入仓库。
- 免费公开站复用同一个单体和 Provider 边界，不新增云数据库或付费服务；代价是临时存储、共享状态和无法横向扩容，这些限制必须在 README 与面试中主动说明。
- 浏览器表单与 JSON API 共享端点时必须按 `Accept` 区分响应：浏览器原生素材上传返回 303 回工作台，API/JavaScript 客户端继续获得结构化 JSON。所有自有 CSS/JavaScript URL 带统一版本参数，避免模板更新后浏览器继续执行旧表单逻辑或旧布局。
- OpenAI-compatible 只保证 Chat Completions 基本契约，不保证支持 `response_format`；适配层必须把结构化输出参数视为可降级能力，同时仍以明确 JSON 指令和本地 Pydantic 校验守住业务结构。Provider 错误必须在 API 边界转成结构化响应，不能把框架 500 文本泄漏给前端解析。
- DeepSeek 的 JSON Output 除 `response_format` 和提示词中的 JSON 字样外，还依赖明确的输出示例与合理的 token 预算；结构修复轮次必须携带上一次无效输出和校验详情，否则相同提示可能重复生成同类错误。
- API 返回 200 只证明分析已持久化，不代表页面已经展示结果；长操作成功路径必须完成“写库—刷新/局部更新—从数据库渲染—结束进行中状态”的闭环，不能只修改按钮文案，更不能让固定占位文案冒充模型结果。
- 人工门禁的持久化负载必须保存用户作答所需的候选值和证据，而不能只保存内部关联键；同时，服务端页面应能根据数据库事实为旧负载补全展示数据，避免发布展示修复后要求用户丢弃已有检查点。
- “一次提交全部确认”是事务语义而不只是按钮文案：领域服务在 Agent 回答路径中必须支持延迟提交，任何一道回答无效都要回滚同批已应用的冲突选择、事实修订与案例补充。
- 同一冲突可能从 Agent 表单或事实页被处理；所有写入口都必须同步人工中断检查点，不能只更新事实表，否则数据库虽然已解决冲突，运行状态仍会持有不可再次回答的旧问题。
- 文件格式不能代表业务类别：DOCX/PDF 解析负责文本和定位，文件名分类负责流程/采访/发言稿语义，两者共同决定引语是否具备可确认来源。人工补问的回答必须落成带来源的领域对象，否则 Planner 会在恢复后重复提出同一缺口。
- 容器中的模块级示例数据属于应用启动依赖，必须与 Python 包一起复制；CI 和非 Windows 启动必须同时设置运行根目录与 Alembic 数据库 URL，避免应用和迁移连接不同 SQLite。
- 目标设计与当前实现必须分开记录；尚未完成的能力只能列为缺口，不能提前写成已实现架构。
