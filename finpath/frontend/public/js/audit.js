function confidenceClass(value) {
  const normalized = String(value || "medium").toLowerCase();
  if (normalized.includes("high")) return "green";
  if (normalized.includes("low")) return "red";
  return "amber";
}

export function renderAudit(container, auditObject = {}) {
  if (!container) return;
  const confidence = auditObject.confidence || auditObject.confidence_score || "medium";
  const guard = auditObject.hallucination_guard || auditObject.guard_status || "passed";
  const reasons = auditObject.reasoning_chain || auditObject.reasoning || [];
  const sources = auditObject.rag_sources || auditObject.sources || [];

  const wrapper = document.createElement("div");
  wrapper.innerHTML = `
    <div class="audit-toggle">View Reasoning -></div>
    <div class="audit-content hidden">
      <div style="display:flex;gap:var(--space-2);flex-wrap:wrap; margin-bottom: var(--space-3);">
        <span class="badge ${confidenceClass(confidence)}">Confidence: ${confidence}</span>
        <span class="badge ${String(guard).toLowerCase().includes("pass") ? "green" : "amber"}">
          Guard: ${String(guard).toUpperCase()}
        </span>
      </div>
      <div>
        <strong>Reasoning Chain</strong>
        <ol id="audit-reasons"></ol>
      </div>
      <div>
        <strong>RAG Sources</strong>
        <div id="audit-sources"></div>
      </div>
    </div>
  `;

  const reasonList = wrapper.querySelector("#audit-reasons");
  reasons.forEach((line) => {
    const li = document.createElement("li");
    li.textContent = line;
    reasonList.appendChild(li);
  });

  if (!reasons.length) {
    const li = document.createElement("li");
    li.textContent = "Reasoning trace unavailable for this response.";
    reasonList.appendChild(li);
  }

  const sourceWrap = wrapper.querySelector("#audit-sources");
  sources.forEach((source) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "source-pill";
    chip.title = `RAG source: ${source}`;
    chip.textContent = source;
    sourceWrap.appendChild(chip);
  });

  if (!sources.length) {
    const none = document.createElement("span");
    none.className = "source-pill";
    none.textContent = "No explicit source cited";
    sourceWrap.appendChild(none);
  }

  const toggle = wrapper.querySelector(".audit-toggle");
  const content = wrapper.querySelector(".audit-content");
  toggle.addEventListener("click", () => {
    content.classList.toggle("hidden");
    toggle.textContent = content.classList.contains("hidden") ? "View Reasoning ->" : "View Reasoning <-";
  });

  container.innerHTML = "";
  container.appendChild(wrapper);
}
