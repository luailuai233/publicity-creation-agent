# 公开站与 Agent 最终验收记录

验收日期：2026-11-22。环境：Windows、项目内 Python 3.12、项目内 Playwright Chromium。开发与测试产物均位于 `D:\aipm\demo`。

## 已执行的自动验证

```powershell
cd D:\aipm\demo
.\scripts\test.ps1 -q
.\scripts\e2e.ps1 -q
.\.venv\Scripts\ruff.exe check workbench tests
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m alembic current
git diff --check
```

结果：

- 单元与集成回归：`219 passed`，零失败；
- Playwright 浏览器验收：`7 passed`，零失败；
- Ruff：`All checks passed!`；
- 依赖检查：`No broken requirements found.`；
- 数据库迁移：`0007_quality_resolution (head)`；
- Git 差异完整性：修正本轮唯一尾随空格后通过；Windows 仅提示预期的 LF/CRLF 转换；
- 生产配置冒烟：Alembic 从空库升级到 head，单 worker Uvicorn 启动成功，`GET /health` 返回 200，并包含 `nosniff`、`DENY` 和 `no-referrer` 安全头；
- Docker Desktop 守护进程当前未运行，因此没有声称本机镜像构建成功；容器、Render 与启动脚本契约由专项测试覆盖。

## 用户本地验收命令

第一次运行或依赖变化后：

```powershell
cd D:\aipm\demo
.\scripts\setup.ps1
```

完整自动验收：

```powershell
cd D:\aipm\demo
.\scripts\test.ps1 -q
.\scripts\e2e.ps1 -q
.\.venv\Scripts\ruff.exe check workbench tests
```

手工页面验收：

```powershell
cd D:\aipm\demo
.\scripts\dev.ps1
```

浏览器打开 `http://127.0.0.1:8000`，按 [`docs/demo-script.md`](demo-script.md) 操作。重点确认：

1. 项目页顶部始终能看到七个工作区入口，Agent 等待策略选择时能直接进入“编辑提案”；
2. 页面不再显示 `LOCAL · MOCK AI`、“本地优先 · 自动保存”、“Demo 模拟结果”或“结构化模拟模式”；
3. “灵感收藏”可以粘贴正文、输入公开链接或上传截图，保存后可以执行案例分析；
4. Agent 只集中询问异常事实，到策略选择必须暂停，用户选择后才恢复；
5. 最终质量门通过后才能导出，导出不包含参考原文、内部 block 标记或提示词。

## Render 公开站验收

1. 将仓库推送到 GitHub；
2. 在 Render 选择 **New → Blueprint** 并连接仓库；
3. 确认识别到根目录 `render.yaml`，计划为 Free，健康检查为 `/health`；
4. 部署完成后打开公开地址，新建项目并走通上面的手工流程；
5. 若要调用真实模型，在 Render Environment 配置 `AI_PROVIDER=openai_compatible`、`AI_BASE_URL`、`AI_API_KEY`、`AI_MODEL`，可选配置 `AI_VISION_MODEL`，然后重新部署。

## 已知限制

- 公开链接无登录，所有访客共享同一个 SQLite、文件目录和模型额度；不适合敏感数据。
- 免费 Render 连续 15 分钟无访问会休眠，休眠、重新部署或实例重启都会清空临时文件系统；下一次唤醒可能需要约一分钟。
- 单实例、单 Uvicorn worker 不能横向扩容；SQLite 和进程内 Runner 不支持多实例竞争。
- 截图理解依赖可选视觉模型；未配置或失败时需要人工填写截图说明。
- 小于 1100 像素只提示使用桌面宽度，不承诺完整移动端布局。
- 测试仍显示第三方依赖与 `datetime.utcnow()` 弃用警告，但本轮测试零失败。
