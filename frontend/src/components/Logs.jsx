import React, { useState } from 'react';
import { RefreshCw, Download, RotateCcw, Trash2, FileText, Globe, Shield, Terminal, Package } from 'lucide-react';

const API = import.meta.env.VITE_API_URL || '/api';

export function Logs({
  websites,
  auditLogs,
  setAuditLogs,
  auditStats,
  setAuditStats,
  sshLogs,
  setSshLogs,
  sshStats,
  setSshStats,
  softLogs,
  setSoftLogs,
  softLogType,
  setSoftLogType,
  selectedService,
  setSelectedService,
  logLines,
  setLogLines,
  logLevel,
  setLogLevel,
  logAutoRefresh,
  setLogAutoRefresh,
  activeLogTab,
  setActiveLogTab,
  panelLogsContent,
  setPanelLogsContent,
  websiteLogsContent,
  setWebsiteLogsContent,
  selectedWebsiteLogId,
  setSelectedWebsiteLogId,
  selectedLogType,
  setSelectedLogType,
  loading,
  setNotice,
  setError
}) {
  // SSH filter state (local to this component)
  const [sshFilter, setSshFilter] = useState('');

  async function request(path, options = {}, label = '') {
    try {
      setError('');
      const method = (options.method || 'GET').toUpperCase();
      const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      };
      const res = await fetch(`${API}${path}`, {
        ...options,
        credentials: 'include',
        headers,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.detail || `Request failed with status ${res.status}`);
        return null;
      }
      return data;
    } catch (err) {
      setError(`Cannot connect to the API.`);
      return null;
    }
  }

  async function loadPanelLogs() {
    const level = logLevel !== 'all' ? `&level=${logLevel}` : '';
    const data = await request(`/logs/panel?lines=${logLines}${level}`, {}, 'Loading panel logs...');
    if (data) {
      setPanelLogsContent(data.content || '');
    }
  }

  async function loadWebsiteLogs(websiteId, logType = selectedLogType) {
    if (!websiteId) return;
    const data = await request(`/logs/websites/${websiteId}?log_type=${logType}&lines=${logLines}`, {}, 'Loading website logs...');
    if (data) {
      setWebsiteLogsContent(data.content || '');
    }
  }

  async function loadAuditLogs() {
    const data = await request(`/logs/audit?lines=${logLines}`, {}, 'Loading audit logs...');
    if (data) {
      setAuditLogs(data.logs || []);
    }
    const statsData = await request('/logs/audit/stats', {}, 'Loading audit stats...');
    if (statsData) {
      setAuditStats(statsData);
    }
  }

  async function loadSshLogs(filter = '') {
    let endpoint = '/logs/ssh';
    if (filter === 'failed') endpoint = '/logs/ssh/failed';
    else if (filter === 'successful') endpoint = '/logs/ssh/successful';
    const data = await request(`${endpoint}?lines=${logLines}`, {}, 'Loading SSH logs...');
    if (data) {
      setSshLogs(data.content || '');
    }
    const statsData = await request('/logs/ssh/stats', {}, 'Loading SSH stats...');
    if (statsData) {
      setSshStats(statsData);
    }
  }

  async function loadSoftLogs(type) {
    let endpoint = '';
    if (type === 'updates') endpoint = '/logs/system/updates';
    else if (type === 'install') endpoint = '/logs/system/install';
    else if (type === 'service') endpoint = `/logs/system/service/${selectedService}`;
    else if (type === 'docker') endpoint = '/logs/docker';
    else if (type === 'mail') endpoint = '/logs/mail';
    else if (type === 'cron') endpoint = '/logs/cron';
    if (endpoint) {
      const data = await request(`${endpoint}?lines=${logLines}`, {}, 'Loading logs...');
      if (data) {
        setSoftLogs(data.content || '');
      }
    }
  }

  async function exportLogsAction(logType, format = 'txt') {
    const data = await request(`/logs/export?log_type=${logType}&format=${format}`, {}, 'Exporting logs...');
    if (data?.content) {
      const blob = new Blob([data.content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `logs-${logType}.${format === 'json' ? 'json' : format === 'csv' ? 'csv' : 'txt'}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setNotice('Logs exported successfully');
    }
  }

  async function rotateLogsAction() {
    const data = await request('/logs/rotate', { method: 'POST' }, 'Rotating logs...');
    if (data) {
      setNotice(data.success ? 'Logs rotated successfully' : `Log rotation failed: ${data.message}`);
    }
  }

  async function clearOldLogsAction(days = 30) {
    if (!confirm(`Clear logs older than ${days} days?`)) return;
    const data = await request(`/logs/clear?days=${days}`, { method: 'POST' }, 'Clearing old logs...');
    if (data) {
      setNotice(`Cleared ${data.deleted_count || 0} old log files`);
    }
  }

  function getLogLevelBadgeClass(level) {
    if (!level) return '';
    const l = level.toLowerCase();
    if (l === 'error' || l === 'failed') return 'bad';
    if (l === 'warning' || l === 'warn') return 'warn';
    if (l === 'info' || l === 'accepted') return 'ok';
    return '';
  }

  const LOG_TABS = [
    { key: 'panel', label: 'Panel Logs', icon: FileText },
    { key: 'website', label: 'Website Logs', icon: Globe },
    { key: 'audit', label: 'Audit Logs', icon: Shield },
    { key: 'ssh', label: 'SSH Login', icon: Terminal },
    { key: 'soft', label: 'Soft Logs', icon: Package },
  ];

  const LOG_LEVELS = [
    { value: 'all', label: 'All' },
    { value: 'error', label: 'Error' },
    { value: 'warning', label: 'Warning' },
    { value: 'info', label: 'Info' },
    { value: 'debug', label: 'Debug' },
  ];

  const WEBSITE_LOG_TYPES = [
    { value: 'access', label: 'Access' },
    { value: 'error', label: 'Error' },
    { value: 'ssl', label: 'SSL' },
    { value: 'php', label: 'PHP' },
    { value: 'fpm-slow', label: 'FPM Slow' },
  ];

  const SOFT_LOG_TYPES = [
    { value: 'updates', label: 'System Updates' },
    { value: 'install', label: 'Package Install' },
    { value: 'service', label: 'Services' },
    { value: 'docker', label: 'Docker' },
    { value: 'mail', label: 'Mail' },
    { value: 'cron', label: 'Cron' },
  ];

  const SERVICES = ['nginx', 'php8.3-fpm', 'php8.4-fpm', 'mariadb', 'redis-server', 'bpanel-api'];

  // Panel Logs Tab
  function renderPanelLogsTab() {
    return (
      <section className="subsection">
        <div className="form-row">
          <select value={logLevel} onChange={e => setLogLevel(e.target.value)}>
            {LOG_LEVELS.map(l => <option key={l.value} value={l.value}>{l.label}</option>)}
          </select>
          <select value={logLines} onChange={e => setLogLines(Number(e.target.value))}>
            <option value={50}>50 lines</option>
            <option value={100}>100 lines</option>
            <option value={200}>200 lines</option>
            <option value={500}>500 lines</option>
          </select>
          <button disabled={!!loading} onClick={loadPanelLogs}><RefreshCw size={15}/> Refresh</button>
          <button onClick={() => exportLogsAction('panel', 'txt')}><Download size={15}/> Export</button>
        </div>
        <div className="log-viewer">
          {panelLogsContent ? (
            <pre className="log-output">{panelLogsContent}</pre>
          ) : (
            <p className="hint">Click Refresh to load panel logs</p>
          )}
        </div>
      </section>
    );
  }

  // Website Logs Tab
  function renderWebsiteLogsTab() {
    return (
      <section className="subsection">
        <div className="form-row">
          <select value={selectedWebsiteLogId || ''} onChange={e => setSelectedWebsiteLogId(e.target.value || null)}>
            <option value="">Select website</option>
            {websites.map(site => <option key={site.id} value={site.id}>{site.domain}</option>)}
          </select>
          <div className="segmented-control small">
            {WEBSITE_LOG_TYPES.map(t => (
              <button key={t.value} className={selectedLogType === t.value ? 'active' : ''} onClick={() => { setSelectedLogType(t.value); if (selectedWebsiteLogId) loadWebsiteLogs(selectedWebsiteLogId, t.value); }}>
                {t.label}
              </button>
            ))}
          </div>
          <select value={logLines} onChange={e => setLogLines(Number(e.target.value))}>
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={200}>200</option>
            <option value={500}>500</option>
          </select>
          <button disabled={!!loading || !selectedWebsiteLogId} onClick={() => loadWebsiteLogs(selectedWebsiteLogId, selectedLogType)}><RefreshCw size={15}/></button>
        </div>
        <div className="log-viewer">
          {websiteLogsContent ? (
            <pre className="log-output">{websiteLogsContent}</pre>
          ) : (
            <p className="hint">Select a website to view its logs</p>
          )}
        </div>
      </section>
    );
  }

  // Audit Logs Tab
  function renderAuditLogsTab() {
    return (
      <section className="subsection">
        {auditStats && (
          <div className="stats-grid">
            <div className="stat-card">
              <span className="stat-value">{auditStats.total_actions || 0}</span>
              <span className="stat-label">Total Actions (30d)</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{auditStats.recent_actions || 0}</span>
              <span className="stat-label">Last 24h</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{auditStats.by_action?.length || 0}</span>
              <span className="stat-label">Action Types</span>
            </div>
          </div>
        )}
        <div className="form-row">
          <select value={logLines} onChange={e => setLogLines(Number(e.target.value))}>
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={200}>200</option>
          </select>
          <button disabled={!!loading} onClick={loadAuditLogs}><RefreshCw size={15}/> Refresh</button>
          <button onClick={() => exportLogsAction('audit', 'json')}><Download size={15}/> JSON</button>
          <button onClick={() => exportLogsAction('audit', 'csv')}><Download size={15}/> CSV</button>
        </div>
        <div className="table">
          <div className="row header">
            <span>Time</span>
            <span>User</span>
            <span>Action</span>
            <span>Target</span>
            <span>Details</span>
          </div>
          {auditLogs.map(log => (
            <div key={log.id} className="row">
              <span className="timestamp">{log.created_at ? new Date(log.created_at).toLocaleString() : '-'}</span>
              <span>{log.username || 'System'}</span>
              <span className="badge">{log.action}</span>
              <span>{log.target}</span>
              <span className="hint">{log.detail || '-'}</span>
            </div>
          ))}
          {auditLogs.length === 0 && <div className="row"><span className="hint" colSpan={5}>No audit logs found</span></div>}
        </div>
      </section>
    );
  }

  // SSH Logs Tab
  function renderSshLogsTab() {
    return (
      <section className="subsection">
        {sshStats && (
          <div className="stats-grid">
            <div className="stat-card">
              <span className="stat-value">{sshStats.total || 0}</span>
              <span className="stat-label">Total Attempts</span>
            </div>
            <div className="stat-card ok">
              <span className="stat-value">{sshStats.successful || 0}</span>
              <span className="stat-label">Successful</span>
            </div>
            <div className="stat-card bad">
              <span className="stat-value">{sshStats.failed || 0}</span>
              <span className="stat-label">Failed</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{sshStats.unique_ips || 0}</span>
              <span className="stat-label">Unique IPs</span>
            </div>
          </div>
        )}
        <div className="form-row">
          <div className="segmented-control small">
            <button className={sshFilter === '' ? 'active' : ''} onClick={() => { setSshFilter(''); loadSshLogs(''); }}>All</button>
            <button className={sshFilter === 'successful' ? 'active' : ''} onClick={() => { setSshFilter('successful'); loadSshLogs('successful'); }}>Successful</button>
            <button className={sshFilter === 'failed' ? 'active' : ''} onClick={() => { setSshFilter('failed'); loadSshLogs('failed'); }}>Failed</button>
          </div>
          <select value={logLines} onChange={e => setLogLines(Number(e.target.value))}>
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={200}>200</option>
          </select>
          <button disabled={!!loading} onClick={() => loadSshLogs(sshFilter)}><RefreshCw size={15}/> Refresh</button>
          <button onClick={() => exportLogsAction('ssh', 'txt')}><Download size={15}/> Export</button>
        </div>
        <div className="log-viewer">
          {sshLogs ? (
            <pre className="log-output">{sshLogs}</pre>
          ) : (
            <p className="hint">Click Refresh to load SSH logs</p>
          )}
        </div>
      </section>
    );
  }

  // Soft Logs Tab
  function renderSoftLogsTab() {
    return (
      <section className="subsection">
        <div className="form-row">
          <select value={softLogType} onChange={e => { setSoftLogType(e.target.value); loadSoftLogs(e.target.value); }}>
            {SOFT_LOG_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
          {softLogType === 'service' && (
            <select value={selectedService} onChange={e => { setSelectedService(e.target.value); loadSoftLogs('service'); }}>
              {SERVICES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          )}
          <select value={logLines} onChange={e => setLogLines(Number(e.target.value))}>
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={200}>200</option>
          </select>
          <button disabled={!!loading} onClick={() => loadSoftLogs(softLogType)}><RefreshCw size={15}/> Refresh</button>
        </div>
        <div className="log-viewer">
          {softLogs ? (
            <pre className="log-output">{softLogs}</pre>
          ) : (
            <p className="hint">Select a log type and click Refresh</p>
          )}
        </div>
      </section>
    );
  }

  return (
    <section className="section">
      <div className="section-title">
        <div>
          <h2>Logs Management</h2>
          <p className="hint">View and manage system logs</p>
        </div>
        <div className="form-row">
          <label style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <input type="checkbox" checked={logAutoRefresh} onChange={e => setLogAutoRefresh(e.target.checked)} />
            Auto-refresh
          </label>
          <button disabled={!!loading} onClick={rotateLogsAction}><RotateCcw size={15}/> Rotate Logs</button>
          <button onClick={() => clearOldLogsAction(30)}><Trash2 size={15}/> Clear Old</button>
        </div>
      </div>

      <div className="segmented-control">
        {LOG_TABS.map(tab => (
          <button key={tab.key} className={activeLogTab === tab.key ? 'active' : ''} onClick={() => setActiveLogTab(tab.key)}>
            <tab.icon size={15}/> {tab.label}
          </button>
        ))}
      </div>

      {activeLogTab === 'panel' && renderPanelLogsTab()}
      {activeLogTab === 'website' && renderWebsiteLogsTab()}
      {activeLogTab === 'audit' && renderAuditLogsTab()}
      {activeLogTab === 'ssh' && renderSshLogsTab()}
      {activeLogTab === 'soft' && renderSoftLogsTab()}
    </section>
  );
}

export default Logs;
