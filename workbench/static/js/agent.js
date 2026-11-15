(() => {
  const root = document.querySelector("[data-agent-workspace]");
  if (!root) return;
  const projectId = root.dataset.projectId;
  let runId = root.dataset.runId;
  const error = root.querySelector("[data-agent-error]");

  const call = async (url, options = {}) => {
    const response = await fetch(url, options);
    const payload = await response.json();
    if (!response.ok || payload.error) throw new Error(payload.error?.message || "请求失败");
    return payload.data;
  };
  const refresh = async () => {
    if (!runId) return;
    const run = await call(`/api/agent-runs/${runId}`);
    root.querySelector("[data-agent-status]").textContent = run.status;
    root.querySelector("[data-agent-footer]").textContent = `${run.status} · ${run.current_stage || "等待下一步"}`;
    if (["RUNNING", "QUEUED"].includes(run.status)) setTimeout(refresh, 1500);
    else location.reload();
  };
  root.querySelector("[data-agent-start]")?.addEventListener("submit", async (event) => {
    event.preventDefault(); error.textContent = "";
    try {
      const goal = new FormData(event.currentTarget).get("goal");
      const run = await call(`/api/projects/${projectId}/agent-runs`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({goal})});
      runId = run.id; refresh();
    } catch (caught) { error.textContent = caught.message; }
  });
  root.querySelector("[data-agent-answer]")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try { await call(`/api/agent-runs/${runId}/answers`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(values)}); refresh(); }
    catch (caught) { error.textContent = caught.message; }
  });
  for (const [selector, action] of [["[data-agent-pause]", "pause"], ["[data-agent-resume]", "resume"], ["[data-agent-cancel]", "cancel"]]) {
    root.querySelector(selector)?.addEventListener("click", async () => { try { await call(`/api/agent-runs/${runId}/${action}`, {method: "POST"}); location.reload(); } catch (caught) { error.textContent = caught.message; } });
  }
  if (runId && ["RUNNING", "QUEUED"].includes(root.querySelector("[data-agent-status]")?.textContent)) setTimeout(refresh, 1500);
})();
