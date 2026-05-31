import { Globe, Shield, ShieldCheck, Unlock, RefreshCw, Plus, Edit, Trash2, Eye, Save, X } from 'lucide-react';

function EmptyState({ icon, message }) {
  return <div className="empty-state">{icon && <icon size={40} />}<p>{message}</p></div>;
}

export default function NginxProxy({
  proxyConfigs,
  proxyTemplates,
  proxyStatus,
  loading,
  showProxyModal,
  editingProxy,
  newProxyConfig,
  showAdvanced,
  previewConfig,
  onOpenProxyModal,
  onCloseProxyModal,
  onSetNewProxyConfig,
  onSetShowAdvanced,
  onCreateProxyConfig,
  onUpdateProxyConfig,
  onDeleteProxyConfig,
  onToggleProxyConfig,
  onSetupSsl,
  onRenewSsl,
  onReloadNginx,
  onRestartNginx,
  onPreviewProxyConfig,
  onLoadProxyConfigs,
  onLoadProxyTemplates,
  onLoadProxyStatus
}) {
  const templates = proxyTemplates.length > 0 ? proxyTemplates : [
    { name: 'default', description: 'Default' },
    { name: 'websocket', description: 'WebSocket' },
    { name: 'nodejs', description: 'Node.js' },
    { name: 'php', description: 'PHP' },
    { name: 'python', description: 'Python' },
    { name: 'go', description: 'Go' },
    { name: 'static', description: 'Static' },
    { name: 'java', description: 'Java' },
  ];

  return (
    <>
      <section className="section">
        <div className="section-title">
          <div>
            <h2>Nginx Proxy</h2>
            <p className="hint">Configure reverse proxy rules for custom backend applications.</p>
          </div>
          <button disabled={!!loading} onClick={() => {
            onLoadProxyConfigs?.();
            onLoadProxyTemplates?.();
            onLoadProxyStatus?.();
          }}>
            <RefreshCw size={14}/> Refresh
          </button>
        </div>
      </section>

      <section className="section">
        <div className="section-title">
          <h3>Proxy Configs</h3>
          <button disabled={!!loading} onClick={() => onOpenProxyModal?.(null)}>
            <Plus size={14}/> Create
          </button>
        </div>
        {proxyConfigs.length === 0 ? (
          <div className="empty-state"><Globe size={40}/><p>No proxy configs yet. Create one to get started.</p></div>
        ) : (
          <div className="table">
            <div className="row header-row">
              <span>Domain</span><span>Target URL</span><span>Template</span><span>SSL</span><span>Status</span><span>Actions</span>
            </div>
            {proxyConfigs.map(config => (
              <div className="row" key={config.domain}>
                <span><strong>{config.domain}</strong></span>
                <span>{config.target_url}</span>
                <span>{config.template || 'default'}</span>
                <span>{config.ssl_enabled ? <span className="badge ok"><ShieldCheck size={13}/> SSL</span> : <span className="badge"><Unlock size={13}/> No SSL</span>}</span>
                <span>{config.enabled ? <span className="badge ok">Active</span> : <span className="badge bad">Disabled</span>}</span>
                <div className="row-actions">
                  <button className="mini secondary-light" disabled={!!loading} onClick={() => onToggleProxyConfig?.(config)}>
                    {config.enabled ? <Unlock size={13}/> : <Shield size={13}/>}
                    {config.enabled ? 'Disable' : 'Enable'}
                  </button>
                  {!config.ssl_enabled && (
                    <button className="mini secondary-light" disabled={!!loading} onClick={() => onSetupSsl?.(config.domain)}>
                      <Shield size={13}/> SSL
                    </button>
                  )}
                  {config.ssl_enabled && (
                    <button className="mini secondary-light" disabled={!!loading} onClick={() => onRenewSsl?.(config.domain)}>
                      <RefreshCw size={13}/> Renew
                    </button>
                  )}
                  <button className="mini secondary-light" disabled={!!loading} onClick={() => onOpenProxyModal?.(config)}>
                    <Edit size={13}/> Edit
                  </button>
                  <button className="mini danger" disabled={!!loading} onClick={() => onDeleteProxyConfig?.(config.domain)}>
                    <Trash2 size={13}/>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="section">
        <div className="section-title"><h3>Nginx Status</h3></div>
        <div className="info-box">
          <div className="proxy-status-row">
            <span>Status:</span>
            <span className={proxyStatus?.running ? 'badge ok' : 'badge'}>{proxyStatus?.running ? 'Running' : 'Stopped'}</span>
          </div>
          {proxyStatus?.version && (
            <div className="proxy-status-row">
              <span>Nginx Version:</span>
              <span>{proxyStatus.version}</span>
            </div>
          )}
        </div>
        <div className="actions">
          <button disabled={!!loading} onClick={onReloadNginx}>
            <RefreshCw size={14}/> Reload
          </button>
          <button disabled={!!loading} onClick={onRestartNginx}>
            <RotateCcw size={14}/> Restart
          </button>
        </div>
      </section>

      {showProxyModal && (
        <section className="section nginx-modal">
          <div className="section-title">
            <h2>{editingProxy ? 'Edit Proxy Config' : 'Create Proxy Config'}</h2>
            <button className="secondary-light" onClick={onCloseProxyModal}>
              <X size={14}/> Close
            </button>
          </div>
          <div className="proxy-form">
            <label>
              <span>Domain</span>
              <input
                value={newProxyConfig.domain}
                onChange={e => onSetNewProxyConfig?.({ ...newProxyConfig, domain: e.target.value })}
                placeholder="proxy.example.com"
                disabled={!!editingProxy}
              />
            </label>
            <label>
              <span>Target URL</span>
              <input
                value={newProxyConfig.target_url}
                onChange={e => onSetNewProxyConfig?.({ ...newProxyConfig, target_url: e.target.value })}
                placeholder="http://localhost:3000"
              />
            </label>
            <label>
              <span>Template</span>
              <select
                value={newProxyConfig.template}
                onChange={e => onSetNewProxyConfig?.({ ...newProxyConfig, template: e.target.value })}
              >
                {templates.map(t => (
                  <option key={t.name} value={t.name}>{t.name.charAt(0).toUpperCase() + t.name.slice(1)} - {t.description}</option>
                ))}
              </select>
            </label>
            <label className="check-line">
              <input
                type="checkbox"
                checked={newProxyConfig.ssl_enabled}
                onChange={e => onSetNewProxyConfig?.({ ...newProxyConfig, ssl_enabled: e.target.checked })}
              />
              <span>Enable SSL (Let's Encrypt)</span>
            </label>
            <div className="advanced-section">
              <button className="advanced-toggle" onClick={() => onSetShowAdvanced?.(!showAdvanced)}>
                Advanced Options {showAdvanced ? '▼' : '▶'}
              </button>
              {showAdvanced && (
                <div className="advanced-fields">
                  <label>
                    <span>Connect Timeout (s)</span>
                    <input
                      type="number"
                      value={newProxyConfig.connect_timeout}
                      onChange={e => onSetNewProxyConfig?.({ ...newProxyConfig, connect_timeout: e.target.value })}
                      min="1"
                      max="300"
                    />
                  </label>
                  <label>
                    <span>Send Timeout (s)</span>
                    <input
                      type="number"
                      value={newProxyConfig.send_timeout}
                      onChange={e => onSetNewProxyConfig?.({ ...newProxyConfig, send_timeout: e.target.value })}
                      min="1"
                      max="300"
                    />
                  </label>
                  <label>
                    <span>Read Timeout (s)</span>
                    <input
                      type="number"
                      value={newProxyConfig.read_timeout}
                      onChange={e => onSetNewProxyConfig?.({ ...newProxyConfig, read_timeout: e.target.value })}
                      min="1"
                      max="300"
                    />
                  </label>
                </div>
              )}
            </div>
            <div className="actions">
              <button disabled={!!loading} onClick={onPreviewProxyConfig}>
                <Eye size={14}/> Preview Config
              </button>
            </div>
            {previewConfig && (
              <div className="config-preview">
                <h4>Config Preview</h4>
                <pre>{typeof previewConfig === 'string' ? previewConfig : JSON.stringify(previewConfig, null, 2)}</pre>
              </div>
            )}
            <div className="actions">
              {editingProxy ? (
                <button disabled={!!loading} onClick={onUpdateProxyConfig}>
                  <Save size={14}/> Update
                </button>
              ) : (
                <button disabled={!!loading} onClick={onCreateProxyConfig}>
                  <Plus size={14}/> Create
                </button>
              )}
              <button className="secondary-light" onClick={onCloseProxyModal}>Cancel</button>
            </div>
          </div>
        </section>
      )}
    </>
  );
}

import { RotateCcw } from 'lucide-react';
