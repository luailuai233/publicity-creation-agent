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

const syncReferenceFields = (form) => {
  const selected = form.querySelector("[data-reference-type]")?.value;
  form.querySelectorAll("[data-reference-field]").forEach((field) => { field.hidden = field.dataset.referenceField !== selected; });
};

document.addEventListener("change", (event) => {
  if (event.target.matches("[data-reference-type]")) syncReferenceFields(event.target.form);
});

document.addEventListener("submit", async (event) => {
  const form = event.target.closest("[data-reference-create]");
  if (!form) return;
  event.preventDefault();
  const error = form.querySelector("[data-reference-error]");
  const button = form.querySelector("button[type=submit]");
  error.textContent = ""; button.disabled = true;
  const data = new FormData(form);
  const inputType = data.get("input_type");
  try {
    if (inputType === "SCREENSHOT") {
      if (!data.get("file")?.size) throw new Error("请选择一张截图");
      data.delete("input_type"); data.delete("raw_text"); data.delete("source_url");
      await jsonRequest(`/api/projects/${form.dataset.referenceCreate}/references/upload`, {method: "POST", body: data});
    } else {
      const payload = {input_type: inputType, source_label: data.get("source_label") || ""};
      if (inputType === "TEXT") payload.raw_text = data.get("raw_text") || "";
      if (inputType === "LINK") payload.source_url = data.get("source_url") || "";
      await jsonRequest(`/api/projects/${form.dataset.referenceCreate}/references`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload)});
    }
    location.reload();
  } catch (caught) { error.textContent = caught.message; button.disabled = false; }
});

document.addEventListener("click", async (event) => {
  const button = event.target.closest("button, a");
  if (!button) return;
  try {
    if (button.dataset.confirmFacts) {
      button.disabled = true; setWorkflowStatus("正在确认来源与冲突…");
      const facts = await jsonRequest(`/api/projects/${button.dataset.confirmFacts}/facts`);
      const groups = new Map();
      facts.filter((fact) => fact.conflict_group).forEach((fact) => { if (!groups.has(fact.conflict_group)) groups.set(fact.conflict_group, fact); });
      if (groups.size) throw new Error("请先在“解决冲突”中查看来源并选择正确事实");
      if (facts.some((fact) => fact.status === "PENDING" && fact.type === "QUOTE")) throw new Error("请先逐条采用或忽略黄色的引语候选");
      for (const fact of facts.filter((item) => item.status === "PENDING" && !item.conflict_group)) await jsonRequest(`/api/facts/${fact.id}`, {method: "PATCH", headers: {"Content-Type": "application/json"}, body: JSON.stringify({status: "CONFIRMED"})});
      location.href = `/project/${button.dataset.confirmFacts}/inspiration`; return;
    }
    if (button.dataset.updateFact) {
      button.disabled = true; setWorkflowStatus(button.dataset.factStatus === "CONFIRMED" ? "正在采用事实…" : "正在忽略候选事实…");
      await jsonRequest(`/api/facts/${button.dataset.updateFact}`, {method: "PATCH", headers: {"Content-Type": "application/json"}, body: JSON.stringify({status: button.dataset.factStatus})});
      location.reload(); return;
    }
    if (button.dataset.resolveConflict) {
      button.disabled = true; setWorkflowStatus("正在保存冲突选择…");
      await jsonRequest(`/api/facts/conflicts/${button.dataset.resolveConflict}/resolve`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({fact_id: button.dataset.factId})});
      location.reload(); return;
    }
    if (button.dataset.analyzeReference) {
      button.disabled = true; setWorkflowStatus("正在分析参考案例…");
      await jsonRequest(`/api/references/${button.dataset.analyzeReference}/analyze`, {method: "POST"});
      location.reload(); return;
    }
    if (button.dataset.deleteReference) {
      if (!confirm("删除后案例原文与分析结果将一并清除，确定继续吗？")) return;
      await jsonRequest(`/api/references/${button.dataset.deleteReference}`, {method: "DELETE"});
      location.reload(); return;
    }
    if (button.dataset.generateStrategies) {
      button.disabled = true; setWorkflowStatus("正在生成 3 个创作策略…");
      await jsonRequest(`/api/projects/${button.dataset.generateStrategies}/strategies/generate`, {method: "POST"});
      location.href = `/project/${button.dataset.generateStrategies}/strategy`; return;
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
