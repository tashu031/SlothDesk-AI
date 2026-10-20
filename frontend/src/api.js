const API_BASE = '/api';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Backend health check failed');
  return res.json();
}

export async function fetchAIStatus() {
  const res = await fetch(`${API_BASE}/ai/status`);
  if (!res.ok) throw new Error('Failed to fetch AI status');
  return res.json();
}

export async function scanFolder(folderPath, recursive = true, maxFiles = 200) {
  const res = await fetch(`${API_BASE}/scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ folder_path: folderPath, recursive, max_files: maxFiles })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to scan folder' }));
    throw new Error(err.detail || 'Scan failed');
  }
  return res.json();
}

export async function createSamplePlayground() {
  const res = await fetch(`${API_BASE}/sample/create`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to generate sample playground');
  return res.json();
}

export async function generateSuggestions(sessionId, rootPath, files, customRules = null) {
  const res = await fetch(`${API_BASE}/suggestions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      root_path: rootPath,
      files: files,
      custom_rules: customRules
    })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to generate suggestions' }));
    throw new Error(err.detail || 'Failed to generate suggestions');
  }
  return res.json();
}

export async function approveSuggestions(suggestionIds) {
  const res = await fetch(`${API_BASE}/suggestions/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ suggestion_ids: suggestionIds })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to approve suggestions' }));
    throw new Error(err.detail || 'Failed to approve suggestions');
  }
  return res.json();
}

export async function executeActions(rootPath, actions) {
  const res = await fetch(`${API_BASE}/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ root_path: rootPath, actions: actions })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Execution failed' }));
    throw new Error(err.detail || 'Execution failed');
  }
  return res.json();
}

export async function undoOperation(operationId) {
  const res = await fetch(`${API_BASE}/undo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ operation_id: operationId })
  });
  if (!res.ok) throw new Error('Undo request failed');
  return res.json();
}

export async function fetchHistory(limit = 50) {
  const res = await fetch(`${API_BASE}/history?limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch history');
  return res.json();
}

export async function fetchSummary() {
  const res = await fetch(`${API_BASE}/summary`);
  if (!res.ok) throw new Error('Failed to fetch summary');
  return res.json();
}

export async function fetchSettings() {
  const res = await fetch(`${API_BASE}/settings`);
  if (!res.ok) throw new Error('Failed to fetch settings');
  return res.json();
}

export async function updateSettings(settings) {
  const res = await fetch(`${API_BASE}/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings)
  });
  if (!res.ok) throw new Error('Failed to update settings');
  return res.json();
}

export async function runEvaluation(forceDeterministic = false) {
  const res = await fetch(`${API_BASE}/evaluate?force_deterministic=${forceDeterministic}`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error('Evaluation benchmark failed');
  return res.json();
}
