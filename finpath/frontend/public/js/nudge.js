import { postNudge } from "./api.js";
import { typewrite } from "./typewriter.js";
import { renderAudit } from "./audit.js";

const NUDGE_HISTORY_KEY = "finpath-nudge-history";

function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(NUDGE_HISTORY_KEY) || "[]");
  } catch {
    return [];
  }
}

function saveHistory(history) {
  localStorage.setItem(NUDGE_HISTORY_KEY, JSON.stringify(history.slice(0, 50)));
}

function renderHistory() {
  const container = document.getElementById("nudge-history");
  if (!container) return;
  const history = loadHistory();
  if (!history.length) {
    container.innerHTML = "<div class='card'>No nudge decisions yet in this session.</div>";
    return;
  }
  container.innerHTML = history
    .map(
      (entry) => `
      <div class="card" style="margin-bottom: var(--space-2);">
        <div><strong>${entry.time}</strong> - ${entry.purchase}</div>
        <div>Amount: Rs ${Number(entry.amount).toLocaleString()} | Impact: ${entry.delay} | Decision: ${entry.decision}</div>
      </div>
    `
    )
    .join("");
}

export function initNudgePage() {
  renderHistory();

  const amountInput = document.getElementById("nudge-amount");
  const descInput = document.getElementById("nudge-description");
  const triggerBtn = document.getElementById("nudge-submit");
  const overlay = document.getElementById("nudge-overlay");
  const loading = document.getElementById("nudge-loading");
  const panel = document.getElementById("nudge-modal");
  const impact = document.getElementById("nudge-impact");
  const insight = document.getElementById("nudge-insight");
  const reconsider = document.getElementById("nudge-reconsider");
  const proceed = document.getElementById("nudge-proceed");

  if (!triggerBtn) return;

  const hideModal = () => {
    overlay.classList.add("hidden");
    loading.classList.remove("hidden");
    panel.classList.add("hidden");
  };

  triggerBtn.addEventListener("click", async () => {
    const amount = Number(amountInput.value || 0);
    const description = descInput.value || "Purchase";
    const sessionId = window.APP_SESSION_ID || localStorage.getItem("finpath-session-id") || localStorage.getItem("finpath_session_id") || "demo-session-001";

    if (!amount || amount <= 0) {
      alert("Please enter a valid amount");
      return;
    }

    if (!String(description).trim()) {
      alert("Please enter what you are buying");
      return;
    }

    overlay.classList.remove("hidden");
    loading.classList.remove("hidden");
    loading.textContent = "Consulting Financial Agents...";
    panel.classList.add("hidden");

    try {
      const response = await postNudge(amount, description, sessionId);
      const delayDays = response.delay_days || response.delayDays || 1;
      const summary = response.summary || response.nudge || "This purchase impacts your goal velocity.";

      loading.classList.add("hidden");
      panel.classList.remove("hidden");
      impact.textContent = `⚠️ Goal Delayed by ${delayDays} Day${delayDays > 1 ? "s" : ""}`;

      // Dynamic spending context
      const spendCtx = document.getElementById("nudge-spend-context");
      const decisionText = response.decision === "reconsider" ? "We strongly recommend reconsidering." :
                           response.decision === "proceed_with_caution" ? "Proceed with caution." : "This is within safe limits.";
      if (spendCtx) spendCtx.textContent = `This Rs ${Number(amount).toLocaleString()} purchase on ${description} consumes ${delayDays} day(s) of savings capacity. ${decisionText}`;

      await typewrite(insight, summary, 15);

      const auditContainer = document.getElementById("nudge-audit");
      renderAudit(auditContainer, response?.audit || response);

      const updateHistory = (decision) => {
        const current = loadHistory();
        current.unshift({
          time: new Date().toLocaleTimeString(),
          purchase: description,
          amount,
          delay: `${delayDays} day${delayDays > 1 ? "s" : ""}`,
          decision,
        });
        saveHistory(current);
        renderHistory();
      };

      reconsider.onclick = () => {
        updateHistory("Reconsidered");
        hideModal();
      };

      proceed.onclick = () => {
        updateHistory("Proceeded");
        const toast = document.getElementById("nudge-toast");
        toast.textContent = `Added to leakage tracker. Goal now delayed by ${delayDays} day${delayDays > 1 ? "s" : ""}.`;
        toast.classList.remove("hidden");
        setTimeout(() => toast.classList.add("hidden"), 2500);
        hideModal();
      };
    } catch (error) {
      loading.classList.add("hidden");
      console.error("Nudge failed:", error);
      alert(`Could not compute nudge right now: ${error.message}`);
      hideModal();
    }
  });

  document.getElementById("nudge-close")?.addEventListener("click", hideModal);
}
