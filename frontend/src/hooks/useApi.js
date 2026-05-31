import { useState, useCallback } from 'react';

const API = import.meta.env.VITE_API_URL || '/api';

export function useApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const readCookie = useCallback((name) => {
    const match = document.cookie.match(new RegExp('(?:^|; )' + name.replace(/[$()*+./?[\\\]^{|}]/g, '\\$&') + '=([^;]*)'));
    return match ? decodeURIComponent(match[1]) : '';
  }, []);

  const request = useCallback(async (path, options = {}, label = '', setErrorCallback = null, setLoadingCallback = null, panelSettings = { app_name: 'BPanel' }) => {
    try {
      if (setErrorCallback) setErrorCallback('');
      if (setLoadingCallback) setLoadingCallback(label);
      const method = (options.method || 'GET').toUpperCase();
      const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
      const headers = isFormData ? { ...(options.headers || {}) } : {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      };
      // CSRF: echo the bpanel_csrf cookie back in a header for mutating requests
      if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
        const csrf = readCookie('bpanel_csrf');
        if (csrf) headers['X-CSRF-Token'] = csrf;
      }
      const res = await fetch(`${API}${path}`, {
        ...options,
        credentials: 'include',
        headers,
      });
      const text = await res.text();
      let data;
      try { data = text ? JSON.parse(text) : {}; } catch { data = { detail: text || `HTTP ${res.status}` }; }
      if (!res.ok && handleAuthExpired(res.status, data.detail, setErrorCallback)) return null;
      if (!res.ok) {
        const errMsg = data.detail || `Request failed with status ${res.status}`;
        if (setErrorCallback) setErrorCallback(errMsg);
        setError(errMsg);
      }
      if (res.ok && data?.message && setNotice) setNotice(data.message);
      return res.ok ? data : null;
    } catch (err) {
      const connErr = `Cannot connect to the ${panelSettings.app_name || 'BPanel'} API at ${API}. Check bpanel-api and the panel port.`;
      if (setErrorCallback) setErrorCallback(connErr);
      setError(connErr);
      return null;
    } finally {
      if (setLoadingCallback) setLoadingCallback('');
    }
  }, [readCookie]);

  const handleAuthExpired = useCallback((status, detail, setErrorCallback) => {
    if (status === 401 || detail === 'Could not validate credentials' || detail === 'Not authenticated') {
      // Dispatch event for app to handle session expiration
      window.dispatchEvent(new CustomEvent('bpanel:auth-expired', { detail }));
      return true;
    }
    return false;
  }, []);

  return { request, loading, error, setError };
}
