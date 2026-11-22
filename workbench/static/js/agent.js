(() => {
  const root = document.querySelector("[data-agent-workspace]");
  if (!root) return;
  const projectId = root.dataset.projectId;
  let runId = root.dataset.runId;
  const terminal = new Set(["COMPLETED", "FAILED", "PARTIAL", "CANCELLED", "WAITING_USER"]);
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
    const previousStatus = root.querySelector("[data-agent-status]").textContent.trim();
    root.querySelector("[data-agent-status]").textContent = run.status;
    root.querySelector("[data-agent-footer]").textContent = `${run.status} · ${run.current_stage || "等待下一步"}`;
    root.querySelector("[data-agent-stage]").textContent = run.current_stage || "等待下一步";
    root.querySelector("[data-agent-next]").textContent = run.next_action;
    root.querySelector("[data-agent-duration]").textContent = `${run.elapsed_ms} ms`;
    if (run.status === "WAITING_USER" && previousStatus !== "WAITING_USER") return location.reload();
    if (!terminal.has(run.status) && run.status !== "PAUSED") setTimeout(refresh, 1500);
  };
  root.querySelector("[data-agent-start]")?.addEventListener("submit", async (event) => {
    event.preventDefault(); error.textContent = "";
    try {
      const goal = new FormData(event.currentTarget).get("goal");
      const run = await call(`/api/projects/${projectId}/agent-runs`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({goal})});
      runId = run.id; root.dataset.runId = run.id; refresh();
    } catch (caught) { error.textContent = caught.message; }
  });
  root.querySelector("[data-agent-answer]")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const answers = [...form.querySelectorAll("[data-question-id]")].map((field) => ({
      question_id: field.dataset.questionId,
      selected_option_id: field.querySelector("input[type=radio]:checked")?.value || null,
      free_text: field.querySelector("textarea")?.value || null,
    }));
    const revision = form.dataset.projectRevision;
    const values = {project_revision: revision === "" ? null : Number(revision), answers};
    try { await call(`/api/agent-runs/${runId}/answers`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(values)}); location.reload(); }
    catch (caught) { error.textContent = caught.message; }
  });
  for (const [selector, action] of [["[data-agent-pause]", "pause"], ["[data-agent-resume]", "resume"], ["[data-agent-cancel]", "cancel"]]) {
    root.querySelector(selector)?.addEventListener("click", async () => { try { await call(`/api/agent-runs/${runId}/${action}`, {method: "POST"}); location.reload(); } catch (caught) { error.textContent = caught.message; } });
  }
  const initialStatus = root.querySelector("[data-agent-status]")?.textContent.trim();
  if (runId && !terminal.has(initialStatus) && initialStatus !== "PAUSED") setTimeout(refresh, 1500);
})();
