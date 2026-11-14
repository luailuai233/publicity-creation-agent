(() => {
  const button = document.querySelector("[data-export-draft]");
  if (!button || !button.dataset.exportDraft) return;
  button.addEventListener("click", async () => {
    const response = await fetch(`/api/drafts/${button.dataset.exportDraft}/export`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ confirm_high: true }),
    });
    const payload = await response.json();
    document.querySelector("[data-export-path]").textContent = payload.data ? `已保存：${payload.data.path}` : payload.error.message;
  });
})();
