const MATERIAL_JOB_POLL_MS = 1500;

document.querySelectorAll("[data-job-id]").forEach((node) => {
  const poll = async () => {
    const response = await fetch(`/api/jobs/${node.dataset.jobId}`);
    const payload = await response.json();
    if (payload.data && ["QUEUED", "PROCESSING"].includes(payload.data.status)) {
      window.setTimeout(poll, MATERIAL_JOB_POLL_MS);
    }
  };
  window.setTimeout(poll, MATERIAL_JOB_POLL_MS);
});
