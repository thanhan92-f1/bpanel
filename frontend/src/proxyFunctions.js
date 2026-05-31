// Nginx Proxy functions for App.jsx
// These functions should be added to the App component

export const proxyFunctionsCode = `  // Nginx Proxy functions
  async function loadProxyConfigs() {
    const data = await request('/nginx-proxy/configs');
    if (data) setProxyConfigs(Array.isArray(data) ? data : []);
  }

  async function loadProxyTemplates() {
    const data = await request('/nginx-proxy/templates');
    if (data) setProxyTemplates(Array.isArray(data) ? data : []);
  }

  async function loadProxyStatus() {
    const data = await request('/nginx-proxy/status');
    if (data) setProxyStatus(data);
  }

  async function createProxyConfig() {
    if (!newProxyConfig.domain) { setError('Please enter a domain name.'); return; }
    if (!newProxyConfig.target_url) { setError('Please enter a target URL.'); return; }
    const body = {
      domain: newProxyConfig.domain,
      target_url: newProxyConfig.target_url,
      template: newProxyConfig.template,
      ssl_enabled: newProxyConfig.ssl_enabled,
      connect_timeout: Number(newProxyConfig.connect_timeout) || 60,
      send_timeout: Number(newProxyConfig.send_timeout) || 60,
      read_timeout: Number(newProxyConfig.read_timeout) || 60,
    };
    const data = await request('/nginx-proxy/configs', { method: 'POST', body: JSON.stringify(body) }, 'Creating proxy config...');
    if (data) {
      setNotice(\`Created proxy config for \${data.domain || newProxyConfig.domain}\`);
      resetProxyForm();
      await loadProxyConfigs();
    }
  }

  async function updateProxyConfig() {
    if (!editingProxy || !newProxyConfig.domain) return;
    const body = {
      target_url: newProxyConfig.target_url,
      template: newProxyConfig.template,
      ssl_enabled: newProxyConfig.ssl_enabled,
      connect_timeout: Number(newProxyConfig.connect_timeout) || 60,
      send_timeout: Number(newProxyConfig.send_timeout) || 60,
      read_timeout: Number(newProxyConfig.read_timeout) || 60,
    };
    const data = await request(\`/nginx-proxy/configs/\${encodeURIComponent(newProxyConfig.domain)}\`, {
      method: 'PUT',
      body: JSON.stringify(body),
    }, 'Updating proxy config...');
    if (data) {
      setNotice(\`Updated proxy config for \${newProxyConfig.domain}\`);
      resetProxyForm();
      await loadProxyConfigs();
    }
  }

  async function deleteProxyConfig(domain) {
    if (!confirm(\`Delete proxy config for \${domain}?\`)) return;
    const data = await request(\`/nginx-proxy/configs/\${encodeURIComponent(domain)}\`, { method: 'DELETE' }, \`Deleting proxy config for \${domain}...\`);
    if (data) {
      setNotice(\`Deleted proxy config for \${domain}\`);
      await loadProxyConfigs();
    }
  }

  async function toggleProxyConfig(config) {
    const data = await request(\`/nginx-proxy/configs/\${encodeURIComponent(config.domain)}\`, {
      method: 'PATCH',
      body: JSON.stringify({ enabled: !config.enabled }),
    }, \`\${config.enabled ? 'Disabling' : 'Enabling'} proxy for \${config.domain}...\`);
    if (data) {
      setNotice(\`\${config.enabled ? 'Disabled' : 'Enabled'} proxy for \${config.domain}\`);
      await loadProxyConfigs();
    }
  }

  async function setupSsl(domain) {
    const data = await request(\`/nginx-proxy/ssl/\${encodeURIComponent(domain)}\`, { method: 'POST' }, \`Setting up SSL for \${domain}...\`);
    if (data) {
      setNotice(data.message || \`SSL setup initiated for \${domain}\`);
      await loadProxyConfigs();
    }
  }

  async function renewSsl(domain) {
    const data = await request(\`/nginx-proxy/ssl/\${encodeURIComponent(domain)}/renew\`, { method: 'POST' }, \`Renewing SSL for \${domain}...\`);
    if (data) {
      setNotice(data.message || \`SSL renewal initiated for \${domain}\`);
      await loadProxyConfigs();
    }
  }

  async function reloadNginx() {
    const data = await request('/nginx-proxy/reload', { method: 'POST' }, 'Reloading Nginx...');
    if (data) {
      setNotice(data.message || 'Nginx reloaded');
      await loadProxyStatus();
    }
  }

  async function restartNginx() {
    if (!confirm('Restart Nginx? Active connections may be interrupted.')) return;
    const data = await request('/nginx-proxy/restart', { method: 'POST' }, 'Restarting Nginx...');
    if (data) {
      setNotice(data.message || 'Nginx restarted');
      await loadProxyStatus();
    }
  }

  async function previewProxyConfig() {
    const data = await request('/nginx-proxy/configs/preview', {
      method: 'POST',
      body: JSON.stringify({
        domain: newProxyConfig.domain,
        target_url: newProxyConfig.target_url,
        template: newProxyConfig.template,
        ssl_enabled: newProxyConfig.ssl_enabled,
        connect_timeout: Number(newProxyConfig.connect_timeout) || 60,
        send_timeout: Number(newProxyConfig.send_timeout) || 60,
        read_timeout: Number(newProxyConfig.read_timeout) || 60,
      }),
    });
    if (data) {
      setPreviewConfig(data.config || data);
    }
  }

  function openProxyModal(config = null) {
    if (config) {
      setEditingProxy(config);
      setNewProxyConfig({
        domain: config.domain,
        target_url: config.target_url || '',
        template: config.template || 'default',
        ssl_enabled: config.ssl_enabled || false,
        connect_timeout: config.connect_timeout || 60,
        send_timeout: config.send_timeout || 60,
        read_timeout: config.read_timeout || 60,
      });
    } else {
      resetProxyForm();
    }
    setShowProxyModal(true);
  }

  function resetProxyForm() {
    setShowProxyModal(false);
    setEditingProxy(null);
    setNewProxyConfig({
      domain: '',
      target_url: '',
      template: 'default',
      ssl_enabled: false,
      connect_timeout: 60,
      send_timeout: 60,
      read_timeout: 60,
    });
    setShowAdvanced(false);
    setPreviewConfig(null);
  }
`;
