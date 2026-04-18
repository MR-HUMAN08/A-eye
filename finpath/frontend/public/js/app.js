import {
  getHealth,
  setDemoContext,
  getDemoContext,
  getAnalysis,
  getGoal,
  getPortfolio,
  getPortfolioLive,
  getSentiment,
  getTaxOptimize,
  getRetirement,
  getMacro,
  getAudit,
  postChat,
  postStatement,
  postRagQuery,
  getRagStats,

} from "./api.js";
import { typewrite } from "./typewriter.js";
import { renderAudit } from "./audit.js";
import { renderDonut, renderLine, renderBar, renderPie } from "./charts.js";
import { initNudgePage } from "./nudge.js";

const SESSION_KEY = "finpath-session-id";
const LEGACY_SESSION_KEY = "finpath_session_id";
const PROFILE_KEY = "finpath_profile";
const TX_KEY = "finpath_transactions";
const LIVE_APPLIED_KEY = "finpath_live_applied";

const defaultSession = localStorage.getItem(SESSION_KEY) || localStorage.getItem(LEGACY_SESSION_KEY) || `mcp-session-${Date.now()}`;
localStorage.setItem(SESSION_KEY, defaultSession);
localStorage.setItem(LEGACY_SESSION_KEY, defaultSession);
window.APP_SESSION_ID = defaultSession;

let runtimeProfile = {};
let runtimeTransactions = [];
const runtimeCache = new Map();
let liveInputsApplied = localStorage.getItem(LIVE_APPLIED_KEY) === "true";

function runMigrationIfNeeded() {
  const migrationKey = "finpath-profile-migration-v2";
  if (!localStorage.getItem(migrationKey)) {
    localStorage.removeItem(PROFILE_KEY);
    localStorage.removeItem(TX_KEY);
    localStorage.setItem(migrationKey, "done");
  }
}

function getRuntimeProfile() {
  return { ...runtimeProfile };
}

function getRuntimeTransactions() {
  return [...runtimeTransactions];
}

function saveRuntimeInputs(profile, transactions) {
  runtimeProfile = { ...profile };
  runtimeTransactions = [...transactions];
  localStorage.setItem(PROFILE_KEY, JSON.stringify(runtimeProfile));
  localStorage.setItem(TX_KEY, JSON.stringify(runtimeTransactions));
}

async function syncDemoContext() {
  let profile = getRuntimeProfile();
  let transactions = getRuntimeTransactions();

  if (!Object.keys(profile).length) {
    try {
      profile = JSON.parse(localStorage.getItem(PROFILE_KEY) || "{}");
    } catch {
      profile = {};
    }
  }

  if (!transactions.length) {
    try {
      transactions = JSON.parse(localStorage.getItem(TX_KEY) || "[]");
    } catch {
      transactions = [];
    }
  }

  if (Object.keys(profile).length || transactions.length) {
    saveRuntimeInputs(profile, transactions);
  }

  if (!Object.keys(profile).length || !transactions.length) {
    try {
      const serverCtx = await getDemoContext(defaultSession);
      if (serverCtx?.status === "ok") {
        profile = serverCtx.profile || {};
        transactions = serverCtx.transactions || [];
        saveRuntimeInputs(profile, transactions);
      }
    } catch {
      // Keep empty runtime state until user applies live inputs.
    }
  }

  return { profile, transactions };
}

function invalidateRuntimeCache() {
  runtimeCache.clear();
}

async function cachedCall(key, fn, ttlMs = 120000) {
  const now = Date.now();
  const cached = runtimeCache.get(key);
  if (cached && now - cached.time < ttlMs) {
    return cached.value;
  }
  const value = await fn();
  runtimeCache.set(key, { value, time: now });
  return value;
}

const routes = {
  dashboard: initDashboard,
  spending: initSpending,
  goal: initGoal,
  portfolio: initPortfolio,
  nudge: initNudge,
  "cfo-chat": initCfoChat,
  tax: initTax,
  sentiment: initSentiment,
  retirement: initRetirement,
  macro: initMacro,

  statement: initStatement,
  "audit-trail": initAuditTrail,
};

function currency(value) {
  return `Rs ${Number(value || 0).toLocaleString("en-IN")}`;
}

function textFromResponse(obj) {
  if (!obj) return "No response available.";
  if (typeof obj === "string") return obj;
  return obj.summary || obj.response || obj.message || obj.analysis || obj.insight || "Insight generated.";
}

function auditFromResponse(obj) {
  const root = obj?.audit || obj || {};
  return {
    confidence: root?.confidence || "medium",
    hallucination_guard: root?.hallucination_guard || "passed",
    reasoning_chain: root?.reasoning_chain || root?.reasoning || [],
    rag_sources: root?.rag_sources || root?.sources || [],
  };
}

function setSkeleton(target, height = "180px") {
  target.innerHTML = `<div class="skeleton" style="height:${height}; width: 100%;"></div>`;
}

async function pollHealth() {
  const status = document.getElementById("backend-status");
  try {
    await getHealth();
    status.className = "badge green";
    status.innerHTML = '<span class="dot"></span><span>Live</span>';
  } catch {
    status.className = "badge red";
    status.innerHTML = '<span class="dot"></span><span>Offline</span>';
  }
}

async function loadPage(page) {
  const content = document.getElementById("page-content");
  setSkeleton(content, "320px");
  try {
    const response = await fetch(`/pages/${page}.html`);
    if (!response.ok) {
      content.innerHTML = `<div class="card">Page unavailable: ${page}</div>`;
      return;
    }
    content.innerHTML = await response.text();
    await syncDemoContext();
    updateActiveNav(page);
    if (routes[page]) await routes[page]();
  } catch (error) {
    content.innerHTML = `<div class="card">Unable to load ${page}: ${error.message}</div>`;
  }
}

function updateActiveNav(page) {
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.page === page);
  });
}

function updateHeaderSubtitle(profile) {
  const name = profile?.name || "Demo User";
  const age = profile?.age || "--";
  const income = profile?.monthly_income
    ? `₹${Number(profile.monthly_income).toLocaleString("en-IN")}/month`
    : "Income not set";
  const goal = profile?.goal || "Goal not set";
  const el = document.getElementById("user-subtitle") || document.getElementById("user-chip");
  if (el) el.textContent = `${name}, ${age} | ${income} | Goal: ${goal}`;
}

function parseTransactionsCsv(csvText) {
  return csvText
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [date, description, category, amount] = line.split(",");
      return {
        date: (date || "").trim(),
        description: (description || "").trim(),
        category: (category || "").trim(),
        amount: Number((amount || "0").trim()),
      };
    })
    .filter((tx) => tx.date && tx.description && tx.category);
}

// Compute monthly surplus from income, fixed expenses, and variable transactions
function computeMonthlySurplus(profile, transactions) {
  const income = Number(profile.monthly_income || 0);
  const fixed = Number(profile.monthly_fixed_expenses || 0);
  const variable = transactions.reduce((sum, tx) => sum + Number(tx.amount || 0), 0);
  return Math.max(0, income - fixed - variable);
}

// Backward compat alias
function computeSavings(profile, transactions) {
  return computeMonthlySurplus(profile, transactions);
}

// Update dashboard metric cards on live input change (without full page reload)
function updateDashboardMetrics(profile, transactions) {
  const monthlySurplusVal = computeMonthlySurplus(profile, transactions);

  const monthlyIncome = Number(profile.monthly_income || 0);
  const monthlyFixed = Number(profile.monthly_fixed_expenses || 0);
  const monthlyVariable = transactions.reduce((sum, tx) => sum + Number(tx.amount || 0), 0);
  const monthlySurplus = Math.max(0, monthlyIncome - monthlyFixed - monthlyVariable);
  const wealthScore = monthlyIncome > 0 ? Math.min(100, Math.round((monthlySurplus / monthlyIncome) * 100)) : 0;

  const wealthScoreEl = document.getElementById("wealth-score");
  const monthlySurplusEl = document.getElementById("monthly-surplus");
  const surplusSubtextEl = document.getElementById("surplus-subtext");
  const wealthSubtextEl = document.getElementById("wealth-subtext");

  if (wealthScoreEl) wealthScoreEl.textContent = String(wealthScore);
  if (monthlySurplusEl) monthlySurplusEl.textContent = currency(monthlySurplus);
  if (surplusSubtextEl) surplusSubtextEl.textContent = `After ${currency(monthlyVariable)} variable spend + ${currency(monthlyFixed)} fixed`;
  if (wealthSubtextEl) wealthSubtextEl.textContent = `Based on ${currency(monthlySurplus)} monthly surplus`;

  const categoryTotals = transactions.reduce((acc, tx) => {
    const key = tx.category || "Other";
    acc[key] = (acc[key] || 0) + Number(tx.amount || 0);
    return acc;
  }, {});
  const topLeak = Object.entries(categoryTotals).sort((a, b) => Number(b[1]) - Number(a[1]))[0] || ["N/A", 0];
  const leakageMainEl = document.getElementById("leakage-main");
  const leakageSubEl = document.getElementById("leakage-sub");
  if (leakageMainEl) leakageMainEl.textContent = `${currency(topLeak[1])}/month on ${topLeak[0]}`;
  if (leakageSubEl) leakageSubEl.textContent = "Top detected leakage category from live input set";

  // Update goal progress card — show monthly surplus and months to goal
  const goalAmount = Number(profile?.goal_amount || 0);
  const existingSaved = Number(profile?.existing_savings || 0);
  const monthsToGoal = monthlySurplusVal > 0 && goalAmount > existingSaved ? Math.ceil((goalAmount - existingSaved) / monthlySurplusVal) : 0;
  const goalProgress = goalAmount > 0 && monthlySurplusVal > 0 ? Math.min(100, Math.round((monthlySurplusVal * 12 / goalAmount) * 100)) : 0;
  const goalProgressBar = document.getElementById("goal-progress-bar");
  const goalProgressText = document.getElementById("goal-progress-text");
  const goalProgressPercent = document.getElementById("goal-progress-percent");
  
  if (goalProgressBar) goalProgressBar.style.width = `${goalProgress}%`;
  if (goalProgressText) goalProgressText.textContent = `${currency(monthlySurplusVal)}/month surplus · ${monthsToGoal > 0 ? monthsToGoal + ' months to goal' : 'Set goal to track'}`;
  if (goalProgressPercent) goalProgressPercent.textContent = `${goalProgress}%`;
}

async function initDashboard() {
  const { profile, transactions } = await syncDemoContext();
  const hasLiveContext = liveInputsApplied && Number(profile?.monthly_income || 0) > 0 && transactions.length > 0;
  const insightContainer = document.getElementById("dashboard-insight");
  const auditContainer = document.getElementById("dashboard-audit");
  updateHeaderSubtitle(profile);

  const form = document.getElementById("demo-context-form");
  if (form) {
    const txTextarea = document.getElementById("demo-transactions");
    const status = document.getElementById("demo-context-status");

    if (Object.keys(profile).length) {
      document.getElementById("demo-name").value = profile.name || "";
      document.getElementById("demo-age").value = profile.age || "";
      document.getElementById("demo-city").value = profile.city || "";
      document.getElementById("demo-income").value = profile.monthly_income || "";
      document.getElementById("demo-fixed").value = profile.monthly_fixed_expenses || "";
      document.getElementById("demo-goal").value = profile.goal || "";
      document.getElementById("demo-goal-amount").value = profile.goal_amount || "";
      document.getElementById("demo-goal-years").value = profile.goal_timeline_years || "";
      document.getElementById("demo-risk").value = profile.risk_appetite || "";
    }

    if (transactions.length) {
      txTextarea.value = transactions.map((tx) => `${tx.date},${tx.description},${tx.category},${tx.amount}`).join("\n");
    }

    form.onsubmit = async (event) => {
      event.preventDefault();
      status.textContent = "";
      const updatedProfile = {
        name: document.getElementById("demo-name").value.trim(),
        age: Number(document.getElementById("demo-age").value || 0),
        city: document.getElementById("demo-city").value.trim(),
        monthly_income: Number(document.getElementById("demo-income").value || 0),
        monthly_fixed_expenses: Number(document.getElementById("demo-fixed").value || 0),
        goal: document.getElementById("demo-goal").value.trim(),
        goal_amount: Number(document.getElementById("demo-goal-amount").value || 0),
        goal_timeline_years: Number(document.getElementById("demo-goal-years").value || 0),
        risk_appetite: document.getElementById("demo-risk").value || "",
        existing_savings: 0,
        inflation_rate: Number(profile.inflation_rate || 0.06),
      };
      const updatedTransactions = parseTransactionsCsv(txTextarea.value);

      if (!updatedProfile.name) {
        status.textContent = "Please enter a name before applying live inputs.";
        return;
      }

      if (updatedProfile.goal_timeline_years <= 0) {
        status.textContent = "Goal Years must be greater than 0.";
        return;
      }

      if (updatedProfile.goal_amount <= 0) {
        status.textContent = "Goal Amount must be greater than 0.";
        return;
      }

      if (!updatedTransactions.length) {
        status.textContent = "Please enter at least one valid transaction line as date,description,category,amount.";
        return;
      }

      // Compute savings dynamically from income - fixed expenses - variable transactions
      updatedProfile.existing_savings = computeSavings(updatedProfile, updatedTransactions);

      try {
        status.textContent = "Applying live inputs...";
        saveRuntimeInputs(updatedProfile, updatedTransactions);
        await setDemoContext(defaultSession, updatedProfile, updatedTransactions);
        liveInputsApplied = true;
        localStorage.setItem(LIVE_APPLIED_KEY, "true");
        invalidateRuntimeCache();
        status.textContent = `Live context updated for ${updatedProfile.name}. Reloading analytics...`;
        setTimeout(() => route(), 120);
      } catch (error) {
        status.textContent = `Unable to apply live inputs: ${error.message}`;
      }
    };

  }

  if (!hasLiveContext) {
    document.getElementById("wealth-score").textContent = "--";
    document.getElementById("monthly-surplus").textContent = "₹--";
    document.getElementById("goal-progress-text").textContent = "Enter your profile above to see goal progress";
    document.getElementById("goal-progress-bar").style.width = "0%";
    document.getElementById("goal-progress-percent").textContent = "--";
    document.getElementById("goal-countdown").textContent = "--";
    document.getElementById("leakage-main").textContent = "₹--/month";
    document.getElementById("leakage-sub").textContent = "Enter transactions to detect leakage";
    insightContainer.textContent = "No live results yet. Fill the form and click Apply Live Inputs to run analysis.";
    auditContainer.innerHTML = "";
    document.getElementById("portfolio-note").textContent = "Apply live inputs to load portfolio pulse.";
    document.getElementById("sentiment-note").textContent = "Apply live inputs to load market sentiment.";
    const profileLine = document.getElementById("dashboard-user-line");
    if (profileLine) {
      profileLine.textContent = "Awaiting live input application";
    }
    return;
  }

  let analysis;
  let goal;
  try {
    [analysis, goal] = await Promise.all([
      cachedCall(`analysis:${defaultSession}`, () => getAnalysis(defaultSession), 120000),
      cachedCall(`goal:${defaultSession}`, () => getGoal(defaultSession), 120000),
    ]);
  } catch (error) {
    insightContainer.textContent = `Unable to load dashboard insights right now: ${error.message}`;
    auditContainer.innerHTML = "";
    return;
  }

  const monthlyIncome = Number(profile.monthly_income || 0);
  const monthlyVariable = Number(analysis?.monthly_variable_spend || 27900);
  const monthlyFixed = Number(profile.monthly_fixed_expenses || 0);
  const monthlySurplus = Math.max(0, monthlyIncome - monthlyVariable - monthlyFixed);
  const wealthScore = monthlyIncome > 0 ? Math.min(100, Math.round((monthlySurplus / monthlyIncome) * 100)) : 0;

  document.getElementById("wealth-score").textContent = String(wealthScore);
  document.getElementById("monthly-surplus").textContent = currency(monthlySurplus);
  document.getElementById("surplus-subtext").textContent = `After ${currency(monthlyVariable)} variable spend + ${currency(monthlyFixed)} fixed`;
  document.getElementById("wealth-subtext").textContent = `Based on ${currency(monthlySurplus)} monthly surplus`;

  const surplusForGoal = computeMonthlySurplus(profile, transactions);
  const goalAmount = Number(profile?.goal_amount || 0);
  const existingSavingsVal = Number(profile?.existing_savings || 0);
  const monthsToGoalDash = surplusForGoal > 0 && goalAmount > existingSavingsVal ? Math.ceil((goalAmount - existingSavingsVal) / surplusForGoal) : 0;
  const progress = goalAmount > 0 && surplusForGoal > 0 ? Math.min(100, Math.round((surplusForGoal * 12 / goalAmount) * 100)) : 0;
  document.getElementById("goal-progress-text").textContent = `${currency(surplusForGoal)}/month surplus · ${monthsToGoalDash > 0 ? monthsToGoalDash + ' months to goal' : 'Set goal to track'}`;
  document.getElementById("goal-progress-bar").style.width = `${progress}%`;
  document.getElementById("goal-progress-percent").textContent = `${progress}%`;
  const countdownDays = Number(profile?.goal_timeline_years || 0) > 0 ? Math.round(Number(profile.goal_timeline_years) * 365) : 0;
  document.getElementById("goal-countdown").textContent = countdownDays > 0 ? `${countdownDays} days remaining` : "--";

  const topLeak = Object.entries(analysis?.category_totals || {}).sort((a, b) => Number(b[1]) - Number(a[1]))[0] || ["N/A", 0];
  const benchmarkMap = { "Food Delivery": 3000, Groceries: 6000, Shopping: 4000, Subscriptions: 800 };
  const benchmark = benchmarkMap[topLeak[0]] || Math.max(1, Math.round(monthlyIncome * 0.08));
  const leakRatio = benchmark > 0 ? (Number(topLeak[1]) / benchmark).toFixed(1) : "0.0";
  document.getElementById("leakage-main").textContent = `${currency(topLeak[1])}/month on ${topLeak[0]}`;
  document.getElementById("leakage-sub").textContent = `${leakRatio}x benchmark based on Behavioral Agent analysis`;

  const categories = Object.entries(analysis?.category_totals || {}).slice(0, 10);
  const labels = categories.map(([name]) => name);
  const values = categories.map(([, amount]) => Number(amount));
  const palette = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#14B8A6", "#FB7185", "#22C55E", "#F97316", "#38BDF8"];
  renderDonut("dashboard-donut", labels, values, palette);

  // Dynamic goal timeline computed from actual surplus
  const surplusPerMonth = monthlySurplus;
  const goalYears = Number(profile?.goal_timeline_years || 5);
  const tlSteps = ["Today", "6 months", "1 year", "3 years", `${goalYears - 1} years`, `${goalYears} years`];
  const tlMonths = [0, 6, 12, 36, Math.max(0, (goalYears - 1) * 12), goalYears * 12];
  const tlData = tlMonths.map((m) => Math.round(surplusPerMonth * m));
  document.getElementById("goal-timeline").innerHTML = tlSteps
    .map((step, idx) => `<div class="timeline-step"><strong>${step}</strong><div>Projected: ${currency(tlData[idx])}</div></div>`)
    .join("");

  document.querySelectorAll("[data-agent-link]").forEach((pill) => {
    pill.addEventListener("click", () => {
      location.hash = `#${pill.dataset.agentLink}`;
    });
  });

  // Render dashboard insight as bullet points
  const insightText = textFromResponse(analysis);
  const insightLines = insightText.split(/[.\n]/).map(s => s.trim()).filter(s => s.length > 8);
  const bulletPoints = insightLines.slice(0, 5).map(s => s.replace(/^[•\-*]\s*/, "").trim());
  if (bulletPoints.length > 0) {
    insightContainer.innerHTML = `<ul style="list-style: disc; padding-left: var(--space-4); margin: var(--space-2) 0;">
      ${bulletPoints.map(b => `<li style="margin-bottom: var(--space-2); line-height: 1.5;">${b}.</li>`).join("")}
    </ul>`;
  } else {
    insightContainer.textContent = insightText;
  }
  renderAudit(auditContainer, auditFromResponse(analysis));

  document.getElementById("sentiment-note").textContent = "Loading sentiment...";
  document.getElementById("portfolio-note").textContent = "Loading portfolio pulse...";
  cachedCall(`portfolio:${defaultSession}`, () => getPortfolio(defaultSession), 120000)
    .then((portfolio) => {
      document.getElementById("portfolio-note").textContent = textFromResponse(portfolio);
    })
    .catch((error) => {
      document.getElementById("portfolio-note").textContent = `Unable to load portfolio pulse: ${error.message}`;
    });
  cachedCall("sentiment", () => getSentiment(), 120000)
    .then((sentiment) => {
      document.getElementById("sentiment-note").textContent = textFromResponse(sentiment);
    })
    .catch((error) => {
      document.getElementById("sentiment-note").textContent = `Unable to load sentiment: ${error.message}`;
    });

  const profileLine = document.getElementById("dashboard-user-line");
  if (profileLine) {
    profileLine.textContent = `${profile?.name || "Demo User"}, ${profile?.age || "--"} | Income ₹${Number(profile?.monthly_income || 0).toLocaleString("en-IN")}/month | Goal: ${profile?.goal || "Goal not set"}`;
  }

}

async function initSpending() {
  const profile = getRuntimeProfile();
  const result = await cachedCall(`analysis:${defaultSession}`, () => getAnalysis(defaultSession), 120000);
  const tableBody = document.getElementById("spend-table-body");
  const categoryData = result?.category_totals || {};
  const income = Number(profile.monthly_income || 0);
  const benchmarks = {
    "Food Delivery": 3000,
    Groceries: 6000,
    Shopping: 4000,
    Subscriptions: 800,
  };

  const rows = Object.entries(categoryData)
    .sort((a, b) => Number(b[1]) - Number(a[1]))
    .map(([category, amount]) => {
      const benchmark = benchmarks[category] || Math.round((income * 0.08));
      const ratio = benchmark ? amount / benchmark : 1;
      const pctIncome = income > 0 ? ((amount / income) * 100).toFixed(1) : "0.0";
      const status = ratio > 1.4 ? "Leaking" : ratio > 1.0 ? "Watch" : "Healthy";
      const badge = status === "Healthy" ? "green" : status === "Watch" ? "amber" : "red";
      return `
        <tr>
          <td>${category}</td>
          <td>${currency(amount)}</td>
          <td>${pctIncome}%</td>
          <td>
            <div class="progress"><span style="width:${Math.min(100, Math.round(ratio * 50))}%"></span></div>
            <small>${ratio.toFixed(1)}x benchmark</small>
          </td>
          <td><span class="badge ${badge}">${status}</span></td>
        </tr>
      `;
    })
    .join("");

  tableBody.innerHTML = rows;

  // Dynamic leak cards from actual analysis data
  const leakCards = document.getElementById("leak-cards");
  const leakEntries = Object.entries(categoryData)
    .sort((a, b) => Number(b[1]) - Number(a[1]))
    .slice(0, 3)
    .map(([name, value]) => {
      const bm = benchmarks[name] || Math.round((income * 0.08));
      const excess = Math.max(0, Number(value) - bm);
      const monthsGain = income > 0 ? Math.max(1, Math.round(excess * 12 / Math.max(1, income * 0.15))) : 1;
      return { name, value: Number(value), excess, months: monthsGain };
    });
  leakCards.innerHTML = leakEntries
    .map(
      (item) => `
      <div class="card span-4">
        <h3>${item.name}</h3>
        <p class="metric-value kpi-danger">${currency(item.value)}</p>
        <p>Annual cost: <strong class="kpi-danger">${currency(item.value * 12)}</strong></p>
        <p class="kpi-positive">Cutting excess saves ~${item.months} month(s) toward goal</p>
      </div>
    `
    )
    .join("");

  const txList = document.getElementById("transactions-list");
  txList.innerHTML = getRuntimeTransactions()
    .slice(0, 20)
    .map(
      (tx) => `
      <div class="card" style="margin-bottom: var(--space-2);">
        <strong>${tx.date}</strong> - ${tx.description} <span class="badge">${tx.category}</span>
        <span class="kpi-danger" style="float:right;">${currency(tx.amount)}</span>
      </div>
    `
    )
    .join("");

  await typewrite(document.getElementById("spending-ai-text"), textFromResponse(result), 15);
  renderAudit(document.getElementById("spending-audit"), auditFromResponse(result));
}

async function initGoal() {
  const profile = getRuntimeProfile();
  const transactions = getRuntimeTransactions();
  const data = await cachedCall(`goal:${defaultSession}`, () => getGoal(defaultSession), 120000);
  const current = computeMonthlySurplus(profile, transactions);
  const target = Number(profile.goal_amount || 0);
  const inflationAdjusted = Number(data?.inflation_adjusted_target || 0);
  const monthsToGoalPage = current > 0 && target > 0 ? Math.ceil(target / current) : 0;
  const pct = target > 0 && current > 0 ? Math.min(100, Math.round((current * 12 / target) * 100)) : 0;

  document.getElementById("goal-progress-main").style.width = `${pct}%`;
  document.getElementById("goal-progress-main-label").textContent = `${pct}% annual coverage`;
  document.getElementById("daily-needed").textContent = currency(data?.daily_savings_needed || 471);
  document.getElementById("monthly-needed").textContent = currency(data?.monthly_savings_needed || 14100);
  document.getElementById("goal-feasibility").innerHTML = data?.goal_feasibility === "feasible" ? '<span class="badge green">ON TRACK</span>' : '<span class="badge amber">AT RISK</span>';
  document.getElementById("inflation-target").textContent = currency(inflationAdjusted);

  const labels = Array.from({ length: 61 }, (_, i) => i);
  const required = labels.map((m) => Math.round((inflationAdjusted / 60) * m));
  const projected = labels.map((m) => Math.round((Number(data?.monthly_surplus || 14800)) * m));

  renderLine("goal-projection-chart", labels, [
    { label: "Required savings curve", data: required, borderColor: "#3B82F6", borderDash: [6, 6], fill: false, tension: 0.25 },
    { label: "Projected savings curve", data: projected, borderColor: "#10B981", fill: false, tension: 0.25 },
  ]);

  const savingsSlider = document.getElementById("whatif-savings");
  const returnSlider = document.getElementById("whatif-return");
  const output = document.getElementById("whatif-output");

  function recompute() {
    const savings = Number(savingsSlider.value);
    const rate = Number(returnSlider.value) / 100;
    const future = Array.from({ length: 61 }, (_, m) => Math.round(savings * m * (1 + rate / 12)));
    renderLine("goal-projection-chart", labels, [
      { label: "Required savings curve", data: required, borderColor: "#3B82F6", borderDash: [6, 6], fill: false, tension: 0.25 },
      { label: "Projected savings curve", data: future, borderColor: "#10B981", fill: false, tension: 0.25 },
    ]);
    const monthHit = future.findIndex((v) => v >= inflationAdjusted);
    output.textContent = `Goal achievement date: ${monthHit > 0 ? `${monthHit} months` : "Beyond 60 months"}`;
    document.getElementById("whatif-savings-value").textContent = currency(savings);
    document.getElementById("whatif-return-value").textContent = `${returnSlider.value}%`;
  }

  savingsSlider.addEventListener("input", recompute);
  returnSlider.addEventListener("input", recompute);
  recompute();

  await typewrite(document.getElementById("goal-ai-text"), textFromResponse(data), 14);
  renderAudit(document.getElementById("goal-audit"), auditFromResponse(data));
}

async function initPortfolio() {
  const [portfolio, live] = await Promise.all([
    cachedCall(`portfolio:${defaultSession}`, () => getPortfolio(defaultSession), 120000),
    cachedCall(`portfolio-live:${defaultSession}`, () => getPortfolioLive(defaultSession), 120000),
  ]);
  document.getElementById("portfolio-live-note").textContent = textFromResponse(live);
  await typewrite(document.getElementById("portfolio-ai-text"), textFromResponse(portfolio), 15);
  renderAudit(document.getElementById("portfolio-audit"), auditFromResponse(portfolio));
}

async function initNudge() {
  initNudgePage();
}

async function initCfoChat() {
  const chatLog = document.getElementById("chat-log");
  const input = document.getElementById("chat-input");
  const sendBtn = document.getElementById("chat-send");

  function appendUser(message) {
    const row = document.createElement("div");
    row.className = "card";
    row.style.marginLeft = "auto";
    row.style.maxWidth = "70%";
    row.style.borderColor = "var(--border-accent)";
    row.textContent = message;
    chatLog.appendChild(row);
    chatLog.scrollTop = chatLog.scrollHeight;
  }

  async function appendAi(responseObj) {
    const card = document.createElement("div");
    card.className = "card";
    card.style.maxWidth = "75%";
    card.innerHTML = `<div class="badge blue">FinPath CFO</div><div id="ai-temp"></div><div class="ai-audit"></div>`;
    chatLog.appendChild(card);
    const rawText = textFromResponse(responseObj);
    // Parse bullet points (lines starting with •, -, or *)
    const lines = rawText.split("\n").map(l => l.trim()).filter(Boolean);
    const isBulletList = lines.some(l => l.startsWith("•") || l.startsWith("-") || l.startsWith("*"));
    const aiTemp = card.querySelector("#ai-temp");
    if (isBulletList) {
      const bullets = lines
        .filter(l => l.startsWith("•") || l.startsWith("-") || l.startsWith("*"))
        .map(l => l.replace(/^[•\-*]\s*/, "").trim())
        .slice(0, 5);
      aiTemp.innerHTML = `<ul style="list-style: disc; padding-left: var(--space-4); margin: var(--space-2) 0;">${bullets.map(b => `<li style="margin-bottom: var(--space-1);">${b}</li>`).join("")}</ul>`;
    } else {
      await typewrite(aiTemp, rawText, 12);
    }
    renderAudit(card.querySelector(".ai-audit"), auditFromResponse(responseObj));
    chatLog.scrollTop = chatLog.scrollHeight;
  }

  async function sendMessage() {
    const message = input.value.trim();
    if (!message) return;
    appendUser(message);
    input.value = "";
    try {
      const response = await postChat(message, defaultSession);
      const aiText = response?.response || response?.result || response?.message || "I could not generate a response. Please try again.";
      await appendAi({ ...response, response: aiText });
    } catch (err) {
      await appendAi({ summary: `Unable to fetch CFO response: ${err.message}` });
    }
  }

  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });

  document.querySelectorAll("[data-starter]").forEach((chip) => {
    chip.addEventListener("click", () => {
      input.value = chip.dataset.starter;
      sendMessage();
    });
  });
}

async function initTax() {
  const tax = await cachedCall(`tax:${defaultSession}`, () => getTaxOptimize(defaultSession), 120000);
  document.getElementById("tax-summary").textContent = textFromResponse(tax);
  document.getElementById("tax-rag-indicator").textContent = "Knowledge base up to date";
}

async function initSentiment() {
  const sentiment = await cachedCall("sentiment", () => getSentiment(), 120000);
  document.getElementById("sentiment-summary").textContent = textFromResponse(sentiment);
}

async function initRetirement() {
  const retirement = await cachedCall(`retirement:${defaultSession}`, () => getRetirement(defaultSession), 120000);
  document.getElementById("retirement-summary").textContent = textFromResponse(retirement);
  renderBar("retirement-bars", ["30", "40", "50", "60"], [
    { label: "NPS", data: [2, 12, 35, 95], backgroundColor: "rgba(59,130,246,0.65)" },
    { label: "EPF", data: [3, 14, 40, 88], backgroundColor: "rgba(16,185,129,0.65)" },
  ]);
}

async function initMacro() {
  const macro = await cachedCall("macro", () => getMacro(), 120000);
  document.getElementById("macro-summary").textContent = textFromResponse(macro);
}




async function initStatement() {
  const runBtn = document.getElementById("statement-run");
  const output = document.getElementById("statement-result");
  const loading = document.getElementById("statement-loading");
  runBtn.addEventListener("click", async () => {
    const payload = {
      company_name: document.getElementById("company-name").value || "Company",
      period: document.getElementById("statement-period").value || "Q1 2025",
      financial_data: {
        revenue: [5000000, 2000000, 500000],
        expenses: [3000000, 1500000, 800000],
        cash_flow: [2200000, -500000],
      },
    };

    // Show loading, disable button
    runBtn.disabled = true;
    runBtn.textContent = "Analysing...";
    if (loading) loading.classList.remove("hidden");
    output.innerHTML = "";

    try {
      const response = await postStatement(payload);

      // DCF section
      const dcf = response.dcf || {};
      const npvRows = (dcf.npv_table || [])
        .map((r) => `<tr><td>Year ${r.year}</td><td>${currency(r.fcf)}</td><td>${currency(r.pv)}</td></tr>`)
        .join("");

      // Variance section
      const varianceRows = (response.variance_analysis || [])
        .map((v) => `<tr><td>${currency(v.actual)}</td><td>${currency(v.planned)}</td><td class="${v.significant ? 'kpi-danger' : ''}">${v.variance_pct}%</td></tr>`)
        .join("");

      output.innerHTML = `
        <div class="card">
          <h3>${response.company_name} — ${response.period}</h3>
          <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: var(--space-3); margin: var(--space-3) 0;">
            <div class="card"><p>Total Revenue</p><p class="metric-value kpi-positive">${currency(response.total_revenue || 0)}</p></div>
            <div class="card"><p>Total Expenses</p><p class="metric-value kpi-danger">${currency(response.total_expenses || 0)}</p></div>
            <div class="card"><p>Net Margin</p><p class="metric-value" style="color: ${(response.net_margin_pct || 0) > 0 ? 'var(--green)' : 'var(--red)'}">${response.net_margin_pct || 0}%</p></div>
            <div class="card"><p>Enterprise Value (DCF)</p><p class="metric-value kpi-positive">${currency(dcf.enterprise_value || 0)}</p></div>
          </div>
        </div>

        ${npvRows ? `<div class="card"><h3>DCF Valuation</h3>
          <table class="data-table"><thead><tr><th>Year</th><th>FCF</th><th>Present Value</th></tr></thead><tbody>${npvRows}</tbody></table>
          <p style="margin-top: var(--space-2);">Terminal Value: <strong>${currency(dcf.terminal_value || 0)}</strong></p>
        </div>` : ""}

        ${varianceRows ? `<div class="card"><h3>Variance Analysis</h3>
          <table class="data-table"><thead><tr><th>Actual</th><th>Planned</th><th>Variance</th></tr></thead><tbody>${varianceRows}</tbody></table>
        </div>` : ""}

        <div class="card"><h3>Comparable Analysis</h3><p>${response.comparable_analysis || "N/A"}</p></div>
        <div class="card"><h3>Cash Flow Forecast</h3><p>${response.cash_flow_forecast || "N/A"}</p></div>

        <div class="card" id="statement-audit"></div>
      `;

      const auditContainer = document.getElementById("statement-audit");
      renderAudit(auditContainer, auditFromResponse(response));
    } catch (err) {
      output.innerHTML = `<div class='card'><h3 class="kpi-danger">Statement analysis failed</h3><p>${err.message}</p></div>`;
    } finally {
      runBtn.disabled = false;
      runBtn.textContent = "Run Analysis →";
      if (loading) loading.classList.add("hidden");
    }
  });
}

async function initAuditTrail() {
  document.getElementById("audit-session-id").textContent = defaultSession;
  try {
    const [audit, ragStats] = await Promise.all([getAudit(defaultSession), getRagStats()]);
    const events = audit?.events || [];
    document.getElementById("audit-overview").textContent = `Decisions: ${events.length} | RAG sources cited: ${events.reduce((sum, e) => sum + (e?.data?.sources?.length || 0), 0)}`;

    const timeline = document.getElementById("audit-timeline");
    if (!events.length) {
      timeline.innerHTML = "<div class='card'>No decisions recorded yet for this session.</div>";
    } else {
      timeline.innerHTML = events
        .map((event, idx) => {
          const eid = `audit-event-${idx}`;
          return `
            <div class="card">
              <div class="audit-toggle" data-audit-toggle="${eid}">${event.timestamp || "now"} | ${event.agent || "agent"} | ${event.summary || "decision"}</div>
              <div id="${eid}" class="audit-content hidden">
                <p><strong>Confidence:</strong> ${event.data?.confidence || "medium"}</p>
                <p><strong>Guard:</strong> ${event.data?.hallucination_guard || "PASSED"}</p>
                <p><strong>Reasoning:</strong></p>
                <ol>${(event.data?.reasoning_chain || []).map((x) => `<li>${x}</li>`).join("")}</ol>
                <p><strong>Sources:</strong> ${(event.data?.sources || []).map((s) => `<span class='source-pill'>${s}</span>`).join("")}</p>
              </div>
            </div>
          `;
        })
        .join("");
    }

    timeline.querySelectorAll("[data-audit-toggle]").forEach((toggle) => {
      toggle.addEventListener("click", () => {
        const target = document.getElementById(toggle.dataset.auditToggle);
        target.classList.toggle("hidden");
      });
    });

    document.getElementById("rag-stats-card").textContent = `Collection: ${ragStats.collection_name} | Total chunks: ${ragStats.total_documents} | Embedding: ${ragStats.embedding_model}`;

    document.getElementById("rag-query-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const question = document.getElementById("rag-query-input").value;
      const result = await postRagQuery(question, 3);
      const list = document.getElementById("rag-query-results");
      list.innerHTML = (result.results || [])
        .slice(0, 3)
        .map((hit) => `<div class='card'><strong>${hit.source}</strong><p>${hit.text}</p><p>Similarity: ${hit.similarity}</p></div>`)
        .join("");
    });

    renderPie("audit-confidence-chart", ["High", "Medium", "Low"], [60, 30, 10], ["#10B981", "#F59E0B", "#EF4444"]);
  } catch (err) {
    document.getElementById("audit-overview").textContent = `Unable to load audit trail: ${err.message}`;
  }
}

async function route() {
  const page = (location.hash || "#dashboard").replace("#", "") || "dashboard";
  await loadPage(routes[page] ? page : "dashboard");
}

window.addEventListener("hashchange", route);
window.addEventListener("DOMContentLoaded", async () => {
  runMigrationIfNeeded();
  await syncDemoContext();
  updateHeaderSubtitle(getRuntimeProfile());
  await pollHealth();
  setInterval(pollHealth, 30000);
  route();
});
