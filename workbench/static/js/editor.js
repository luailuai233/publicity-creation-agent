(() => {
  const editor = document.querySelector("[data-editor][data-draft-id]");
  if (!editor) return;
  const wordCount = document.querySelector("[data-word-count]");
  const citationCount = document.querySelector("[data-citation-count]");
  const saveTime = document.querySelector("[data-save-time]");
  let timer;

  editor.addEventListener("input", () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(async () => {
      const response = await fetch(`/api/drafts/${editor.dataset.draftId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: editor.value }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.data) {
        saveTime.textContent = "保存失败";
        return;
      }
      wordCount.textContent = String(payload.data.word_count);
      citationCount.textContent = String(payload.data.citation_count);
      saveTime.textContent = payload.data.updated_at;
    }, 2000);
  });
})();
