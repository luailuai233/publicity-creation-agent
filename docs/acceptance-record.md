# Agent Demo 验收记录

验收日期：2026-11-15。环境：Windows、Python 3.9、系统 Edge；项目缓存、浏览器 profile、SQLite、临时目录、测试与导出均重定向到 `D:\aipm\demo`。

## 自动化结果

- `scripts/test.ps1`：`120 passed`，22.86 秒；
- `scripts/e2e.ps1` 连续三轮：每轮 `5 passed`，分别为 13.82 秒、14.06 秒、13.80 秒；
- Alembic：`0003_agent_runtime (head)`；
- 视口：1440×900、1280×800；Agent 主 CTA 可见、页面无横向溢出、灵感页保持三栏；
- 浏览器主链路：准备事实 → 一次启动 Agent → 案例分析 → 三策略与自动推荐 → 标题/大纲/正文 → 质量检查 → 最终审核 → Markdown 导出；
- 完整 Agent 时间线与数据库 `AgentStep` 一致，页面刷新后仍能读取终态与步骤。

## P0 验收

- Agent 每轮读取真实 `ProjectSnapshot`，不是播放固定流程文案；
- 六个工具通过白名单 Registry 调用，未知工具被拒绝；
- 单 Run 最多 12 次调用，结构错误最多重试一次，正文最多自动修订一次；
- 同项目只允许一个活动 Run；暂停、取消、等待用户、失败、部分完成和完成均持久化；
- 服务重启只恢复 `RUNNING`，不会擅自恢复 `PAUSED/WAITING_USER`；
- 活动事实与参考案例保持表、Service、Provider 输入三层隔离；
- 三个差异策略自动生成，Provider 推荐项默认采用，用户可覆盖；
- 推荐标题、大纲、正文与事实引用自动生成；
- 事实来源/冲突类问题阻止完成和导出；普通表达问题最多修订一轮；
- Mock 结果始终标记为 Demo，默认运行不访问网络；
- Provider Factory、`.env.example` 与 README 已提供真实 API 接入契约，未实现分支会明确拒绝启动且不泄露密钥。

## D 盘边界

`scripts/runtime-env.ps1` 将 pip cache、Python pycache/user base、TEMP/TMP、Playwright 浏览器目录、Edge 磁盘缓存、SQLite、上传、导出和测试结果全部定向到项目目录。路径扫描只发现系统 Edge 可执行文件位于 C 盘；该文件只读，浏览器写入 profile/cache 仍在 `.runtime/`。

## 已知限制

- 当前内置 Provider 仅为确定性 Mock，不发起真实模型请求；
- 进程内 Runner 与 SQLite 面向单实例 Demo，不支持多进程任务竞争；
- OCR/图片理解仍为明确标识的 Demo 模拟结果；
- 人工策略覆盖后需要从 Agent 工作台重新启动一次 Run，系统不会在后台擅自重写人工稿件。
