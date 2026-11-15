document.documentElement.classList.add("js-enabled");

const jsonRequest = async (url, options = {}) => {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok || payload.error) throw new Error(payload.error?.message || `请求失败 (${response.status})`);
  return payload.data;
};

const setWorkflowStatus = (message) => {
  const target = document.querySelector("[data-workflow-status]");
  if (target) target.textContent = message;
};

document.addEventListener("click", async (event) => {
  const button = event.target.closest("button, a");
  if (!button) return;
  try {
    if (button.dataset.confirmFacts) {
      button.disabled = true; setWorkflowStatus("正在确认来源与冲突…");
      const facts = await jsonRequest(`/api/projects/${button.dataset.confirmFacts}/facts`);
      const groups = new Map();
      facts.filter((fact) => fact.conflict_group).forEach((fact) => { if (!groups.has(fact.conflict_group)) groups.set(fact.conflict_group, fact); });
      for (const [group, fact] of groups) await jsonRequest(`/api/facts/conflicts/${group}/resolve`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({fact_id: fact.id})});
      for (const fact of facts.filter((item) => item.status === "PENDING" && !item.conflict_group)) await jsonRequest(`/api/facts/${fact.id}`, {method: "PATCH", headers: {"Content-Type": "application/json"}, body: JSON.stringify({status: "CONFIRMED"})});
      location.href = `/project/${button.dataset.confirmFacts}/inspiration`; return;
    }
    if (button.dataset.analyzeReference) {
      button.disabled = true; setWorkflowStatus("正在分析参考案例…");
      await jsonRequest(`/api/references/${button.dataset.analyzeReference}/analyze`, {method: "POST"});
      button.textContent = "分析完成"; return;
    }
    if (button.dataset.generateStrategies) {
      button.disabled = true; setWorkflowStatus("正在结构化分析并生成策略…");
      for (const item of document.querySelectorAll("[data-analyze-reference]")) await jsonRequest(`/api/references/${item.dataset.analyzeReference}/analyze`, {method: "POST"});
      await jsonRequest(`/api/projects/${button.dataset.generateStrategies}/strategies/generate`, {method: "POST"});
      location.href = `/project/${button.dataset.generateStrategies}/strategy`; return;
    }
    if (button.dataset.selectStrategy) {
      await jsonRequest(`/api/strategies/${button.dataset.selectStrategy}/select`, {method: "PATCH", headers: {"Content-Type": "application/json"}, body: "{}"});
      document.querySelectorAll("[data-select-strategy]").forEach((item) => item.textContent = "选择这个提案");
      button.textContent = "已选择"; document.querySelector("[data-open-editor]").disabled = false; return;
    }
    if (button.dataset.openEditor) { location.href = `/project/${button.dataset.openEditor}/editor`; return; }
    if (button.dataset.generateDraft) {
      button.disabled = true; setWorkflowStatus("正在生成标题、大纲与正文…");
      const outline = await jsonRequest(`/api/projects/${button.dataset.generateDraft}/drafts/outline`, {method: "POST"});
      await jsonRequest(`/api/projects/${button.dataset.generateDraft}/drafts/generate`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({title: outline.titles[0], outline: outline.outline})});
      location.reload(); return;
    }
    if (button.dataset.runCheck) {
      button.disabled = true; setWorkflowStatus("正在检查事实、表达与隐私风险…");
      await jsonRequest(`/api/drafts/${button.dataset.runCheck}/check`, {method: "POST"}); location.reload(); return;
    }
  } catch (error) { setWorkflowStatus(error.message); button.disabled = false; }
});
