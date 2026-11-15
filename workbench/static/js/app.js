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
    if (button.dataset.selectStrategy) {
      await jsonRequest(`/api/strategies/${button.dataset.selectStrategy}/select`, {method: "PATCH", headers: {"Content-Type": "application/json"}, body: "{}"});
      document.querySelectorAll("[data-select-strategy]").forEach((item) => item.textContent = "选择这个提案");
      button.textContent = "已选择"; document.querySelector("[data-open-editor]").disabled = false; return;
    }
    if (button.dataset.runCheck) {
      button.disabled = true; setWorkflowStatus("正在检查事实、表达与隐私风险…");
      await jsonRequest(`/api/drafts/${button.dataset.runCheck}/check`, {method: "POST"}); location.reload(); return;
    }
  } catch (error) { setWorkflowStatus(error.message); button.disabled = false; }
});
