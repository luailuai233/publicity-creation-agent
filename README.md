# 热点驱动宣传创作工作台（Python Demo）

这是一个本地优先、结构化模拟 AI 的可运行 Demo。它把材料导入、来源化事实、参考案例方法提炼、差异化策略、带引用草稿、质量检查和安全导出串成完整产品链路；不调用真实外部 AI API，也不需要部署即可本机体验。

## Windows 本地运行

只使用以下包装脚本，不要直接运行 `pip`、`pytest` 或 `uvicorn`：

```powershell
cd D:\aipm\demo
.\scripts\setup.ps1
.\scripts\dev.ps1
```

打开 `http://127.0.0.1:8000`，点击“重置并打开完整 Demo”。测试命令：

```powershell
.\scripts\test.ps1
.\scripts\e2e.ps1
```

## D 盘写入保证

包装脚本把虚拟环境、pip 缓存、Python 字节码、临时目录、Playwright 浏览器目录、Edge 磁盘缓存、SQLite、上传文件、导出和测试结果全部定向到 `D:\aipm\demo`。程序不创建 C 盘运行时文件。唯一读取的 C 盘资源是系统已安装的 Edge 可执行文件和 Codex 工具自身；浏览器 profile/cache 仍在本项目 `.runtime` 下。

运行数据位于 `storage/`，Markdown 位于 `exports/`，测试产物位于 `test-results/`。删除这些目录中的内容即可清理运行数据；保留 `.gitkeep` 即可。Demo 重置只删除数据库中 `is_demo=True` 的项目及经路径校验的项目上传子目录，不触碰普通项目。

## 故障注入与架构

开发环境可向 `POST /api/demo/faults` 发送结构化故障队列，例如 `{"faults":{"reference":["schema_error","schema_error"]}}`。生产环境禁用该接口。

架构为 FastAPI + Jinja/HTMX + SQLAlchemy/SQLite + 本地文件存储。`AIProvider` 是边界接口，当前 `MockAIProvider` 返回经过 Pydantic 校验的确定性结构；将来接真实模型时只需新增 Provider，继续满足相同 envelope、重试、来源 ID 和失败状态约定。P1 暂不包含多人协作、云存储、真实图片理解、真实热榜抓取和多实例任务队列。

## 可选 Docker（单实例）

```powershell
docker build -t publicity-workbench .
docker run --rm -p 8000:8000 -v D:\aipm\demo\storage:/app/storage -v D:\aipm\demo\exports:/app/exports publicity-workbench
```

SQLite 方案仅支持单实例。Docker 路径不承诺宿主机 C 盘零写入（Docker Desktop 自身由宿主配置决定），严格 D 盘约束请使用上述 Windows 包装脚本。
