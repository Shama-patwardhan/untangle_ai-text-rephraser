/**
 * API client communicating with Untangle FastAPI backend.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

async function handleResponse(response) {
  if (!response.ok) {
    let errorMessage = `HTTP Error ${response.status}`;
    try {
      const errorJson = await response.json();
      if (errorJson?.error?.message) {
        errorMessage = errorJson.error.message;
      } else if (errorJson?.detail) {
        if (Array.isArray(errorJson.detail)) {
          errorMessage = errorJson.detail.map((d) => d.msg || JSON.stringify(d)).join(', ');
        } else {
          errorMessage = errorJson.detail;
        }
      }
    } catch {
      // Use fallback error message if JSON parsing fails
    }
    throw new Error(errorMessage);
  }
  return response.json();
}

export async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    return await handleResponse(res);
  } catch (err) {
    // If relative proxy failed, try fallback direct port 8000
    if (API_BASE === '/api/v1') {
      try {
        const fallback = await fetch('http://127.0.0.1:8000/api/v1/health');
        return await handleResponse(fallback);
      } catch {
        throw err;
      }
    }
    throw err;
  }
}

export async function analyzeText(text) {
  const url = `${API_BASE}/analyze`;
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({ text }),
    });
    return await handleResponse(res);
  } catch (err) {
    // Fallback if relative proxy isn't configured
    if (API_BASE === '/api/v1' && err.message.includes('Failed to fetch')) {
      const fallback = await fetch('http://127.0.0.1:8000/api/v1/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ text }),
      });
      return await handleResponse(fallback);
    }
    throw err;
  }
}

export async function improveText(text, includeDraftPreview = true) {
  const url = `${API_BASE}/improve`;
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({
        text,
        include_draft_preview: includeDraftPreview,
      }),
    });
    return await handleResponse(res);
  } catch (err) {
    // Fallback if relative proxy isn't configured
    if (API_BASE === '/api/v1' && err.message.includes('Failed to fetch')) {
      const fallback = await fetch('http://127.0.0.1:8000/api/v1/improve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ text, include_draft_preview: includeDraftPreview }),
      });
      return await handleResponse(fallback);
    }
    throw err;
  }
}
