const API_BASE = "/api";

async function apiFetch(path, method = "GET", body = null) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(API_BASE + path, opts);
  if (!res.ok) throw new Error(`API error ${res.status} on ${path}`);
  return res.json();
}

export const getHealth = () => apiFetch("/");
export const setDemoContext = (session_id, profile, transactions) => apiFetch("/demo/context", "POST", { session_id, profile, transactions });
export const getDemoContext = (session_id) => apiFetch(`/demo/context/${session_id}`);
export const getAnalysis = (session_id) => apiFetch(`/analyze${session_id ? `?session_id=${encodeURIComponent(session_id)}` : ""}`);
export const getGoal = (session_id) => apiFetch(`/goal${session_id ? `?session_id=${encodeURIComponent(session_id)}` : ""}`);
export const getPortfolio = (session_id) => apiFetch(`/portfolio${session_id ? `?session_id=${encodeURIComponent(session_id)}` : ""}`);
export const postNudge = (amount, description, session_id) => apiFetch("/nudge", "POST", { amount, description, session_id });
export const postChat = (message, session_id) => apiFetch("/chat", "POST", { message, session_id });
export const getPortfolioLive = (session_id) => apiFetch(`/portfolio/live${session_id ? `?session_id=${encodeURIComponent(session_id)}` : ""}`);
export const postStatement = (data) => apiFetch("/analyze/statement", "POST", data);
export const postGraphQuery = (query, session_id) => apiFetch("/graph/query", "POST", { query, session_id });
export const getSentiment = () => apiFetch("/news/sentiment");
export const getTaxOptimize = (session_id) => apiFetch(`/tax/optimize${session_id ? `?session_id=${encodeURIComponent(session_id)}` : ""}`);
export const postReport = (session_id) => apiFetch(`/report/monthly${session_id ? `?session_id=${encodeURIComponent(session_id)}` : ""}`, "POST", {});
export const getRetirement = (session_id) => apiFetch(`/retirement/plan${session_id ? `?session_id=${encodeURIComponent(session_id)}` : ""}`);
export const getMacro = () => apiFetch("/macro/climate");
export const getAudit = (session_id) => apiFetch(`/audit/${session_id}`);
export const postMemorySave = (data) => apiFetch("/memory/save", "POST", data);
export const getMemoryLoad = () => apiFetch("/memory/load");
export const postRagQuery = (question, top_k = 5) => apiFetch("/rag/query", "POST", { question, top_k });
export const getRagStats = () => apiFetch("/rag/stats");
export const postDocumentUpload = async (formData) => {
  const response = await fetch(API_BASE + "/documents/upload", { method: "POST", body: formData });
  if (!response.ok) throw new Error(`API error ${response.status} on /documents/upload`);
  return response.json();
};
