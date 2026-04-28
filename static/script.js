const API = '';  // empty = same server as Flask

// ── HTTP helpers ─────────────────────────────────────────
async function get(url) {
  const res = await fetch(API + url, { credentials: 'include' });
  return res.json();
}

async function post(url, data) {
  const res = await fetch(API + url, {
    method:      'POST',
    headers:     { 'Content-Type': 'application/json' },
    credentials: 'include',
    body:        JSON.stringify(data)
  });
  return res.json();
}

async function put(url, data = {}) {
  const res = await fetch(API + url, {
    method:      'PUT',
    headers:     { 'Content-Type': 'application/json' },
    credentials: 'include',
    body:        JSON.stringify(data)
  });
  return res.json();
}

// ── Auth guard ───────────────────────────────────────────
async function requireLogin() {
  try {
    const data = await get('/me');
    if (data.error) {
      window.location.href = '/login';
      return null;
    }
    return data;
  } catch {
    window.location.href = '/login';
    return null;
  }
}

// ── Show toast message ───────────────────────────────────
function showToast(message, type = 'info') {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  toast.style.cssText = `
    position: fixed; bottom: 1.5rem; right: 1.5rem;
    padding: 0.8rem 1.2rem; border-radius: 8px;
    font-size: 0.9rem; font-weight: 600;
    z-index: 9999; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    animation: slideIn 0.3s ease;
    background: ${type === 'success' ? '#28A745' : type === 'danger' ? '#DC3545' : type === 'warning' ? '#FFC107' : '#2E75B6'};
    color: ${type === 'warning' ? '#333' : '#fff'};
  `;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

// ── Format date ──────────────────────────────────────────
function formatDate(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric'
  });
}

// ── Set active nav link ──────────────────────────────────
function setActiveNav() {
  const path = window.location.pathname;
  document.querySelectorAll('.navbar-nav a').forEach(a => {
    a.classList.toggle('active', a.getAttribute('href') === path);
  });
}

document.addEventListener('DOMContentLoaded', setActiveNav);