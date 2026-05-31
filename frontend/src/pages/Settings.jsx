import { Settings as SettingsIcon, Globe, Shield, Code, Lock, Palette, Database, Bell, ArrowRightLeft, Server, RefreshCw } from 'lucide-react';

function EmptyState({ icon, message }) {
  return <div className="empty-state">{icon && <icon size={40} />}<p>{message}</p></div>;
}

export default function Settings({
  isAdmin,
  loading,
  settingsData,
  sslStatus,
  apiKey,
  alarmTasks,
  backupList,
  services,
  showApiKey,
  activeSettingsTab,
  onSetActiveSettingsTab,
  onSettingsDataChange,
  onSaveSettings,
  onToggleSetting,
  onLoadSettingsData,
  onLoadSslStatus,
  onLoadApiKey,
  onResetApiKey,
  onShowApiKey,
  onCreatePanelBackup,
  onDeleteAlarmTask
}) {
  const SETTINGS_TABS = [
    { key: 'general', label: 'General', icon: SettingsIcon },
    { key: 'network', label: 'Network', icon: Globe },
    { key: 'ssl', label: 'SSL', icon: Shield },
    { key: 'developer', label: 'Developer', icon: Code },
    { key: 'security', label: 'Security', icon: Lock },
    { key: 'interface', label: 'Interface', icon: Palette },
    { key: 'backup', label: 'Backup', icon: Database },
    { key: 'alarm', label: 'Alarm', icon: Bell },
    { key: 'migrate', label: 'Migrate', icon: ArrowRightLeft },
    { key: 'service', label: 'Service', icon: Server },
  ];

  const THEMES = [
    { key: 'fresh', label: 'Fresh', color: '#0084FF' },
    { key: 'dark', label: 'Dark', color: '#18181b' },
    { key: 'light', label: 'Light', color: '#ffffff' },
  ];

  const THEME_COLORS = [
    { key: 'default', label: 'Default', color: '#0084FF' },
    { key: 'mint', label: 'Mint', color: '#10B981' },
    { key: 'violet', label: 'Violet', color: '#8B5CF6' },
    { key: 'sky', label: 'Sky Blue', color: '#0EA5E9' },
  ];

  if (!isAdmin) {
    return <section className="section"><h2>Settings</h2><p className="hint">No permission.</p></section>;
  }

  return (
    <>
      <div className="settings-tabs">
        {SETTINGS_TABS.map(tab => (
          <button
            key={tab.key}
            className={`settings-tab ${activeSettingsTab === tab.key ? 'active' : ''}`}
            onClick={() => onSetActiveSettingsTab?.(tab.key)}
          >
            <tab.icon size={16} />
            {tab.label}
          </button>
        ))}
      </div>

      <div className="settings-content">
        {activeSettingsTab === 'general' && (
          <div className="settings-section">
            <h3>Panel Information</h3>
            <div className="settings-grid two-col">
              <div className="settings-field">
                <label>Panel Alias</label>
                <input
                  value={settingsData.panel_alias || ''}
                  onChange={e => onSettingsDataChange?.({ ...settingsData, panel_alias: e.target.value })}
                  placeholder="My Server"
                />
              </div>
              <div className="settings-field">
                <label>Session Timeout</label>
                <select
                  value={settingsData.session_timeout || '24h'}
                  onChange={e => onSaveSettings?.('session_timeout', e.target.value)}
                >
                  <option value="1h">1 Hour</option>
                  <option value="6h">6 Hours</option>
                  <option value="12h">12 Hours</option>
                  <option value="24h">24 Hours</option>
                  <option value="48h">48 Hours</option>
                  <option value="7d">7 Days</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {activeSettingsTab === 'ssl' && sslStatus && (
          <div className="settings-section">
            <h3>SSL Status</h3>
            <div className="settings-info-box">
              <p>Status: {sslStatus?.ssl_enabled ? <span className="badge ok">Enabled</span> : <span className="badge">Disabled</span>}</p>
              {sslStatus?.domain && <p><strong>Domain:</strong> {sslStatus.domain}</p>}
              {sslStatus?.expiry_date && <p><strong>Expires:</strong> {sslStatus.expiry_date}</p>}
            </div>
          </div>
        )}

        {activeSettingsTab === 'developer' && (
          <div className="settings-section">
            <h3>Developer Mode</h3>
            <div className="settings-toggle" onClick={() => onToggleSetting?.('developer_mode')}>
              <div className="settings-toggle-label">
                <strong>Enable Developer Mode</strong>
                <span>Show debug tools and advanced options</span>
              </div>
              <div className={`toggle-switch ${settingsData.developer_mode ? 'active' : ''}`}></div>
            </div>
            <h3>API Key</h3>
            <div className="settings-info-box">
              <p><strong>API Key:</strong> {apiKey?.api_key ? (showApiKey ? apiKey.api_key : '••••••••••••••••••••') : 'Not generated'}</p>
            </div>
            <div className="actions">
              <button disabled={!!loading} onClick={() => onShowApiKey?.(!showApiKey)}>Show/Hide</button>
              <button disabled={!!loading} onClick={onResetApiKey}><RefreshCw size={14}/> Reset Key</button>
            </div>
          </div>
        )}

        {activeSettingsTab === 'security' && (
          <div className="settings-section">
            <h3>Password Security</h3>
            <div className="settings-toggle" onClick={() => onToggleSetting?.('strong_password_enabled')}>
              <div className="settings-toggle-label">
                <strong>Strong Password Required</strong>
                <span>Require complex passwords for users</span>
              </div>
              <div className={`toggle-switch ${settingsData.strong_password_enabled ? 'active' : ''}`}></div>
            </div>
          </div>
        )}

        {activeSettingsTab === 'interface' && (
          <div className="settings-section">
            <h3>Theme</h3>
            <div className="settings-grid">
              {THEMES.map(theme => (
                <div
                  key={theme.key}
                  className={`theme-preset ${settingsData.theme === theme.key ? 'selected' : ''}`}
                  onClick={() => onSaveSettings?.('theme', theme.key)}
                >
                  <div style={{ width: 24, height: 24, borderRadius: 4, background: theme.color }}></div>
                  <span>{theme.label}</span>
                </div>
              ))}
            </div>
            <h3>Theme Color</h3>
            <div className="color-picker">
              {THEME_COLORS.map(color => (
                <div
                  key={color.key}
                  className={`color-swatch ${settingsData.theme_color === color.key ? 'selected' : ''}`}
                  style={{ background: color.color }}
                  onClick={() => onSaveSettings?.('theme_color', color.key)}
                  title={color.label}
                ></div>
              ))}
            </div>
          </div>
        )}

        {activeSettingsTab === 'alarm' && (
          <div className="settings-section">
            <h3>Alarm Tasks</h3>
            <div className="settings-info-box info">
              <p>Configure monitoring alerts for CPU, memory, disk, and services.</p>
            </div>
            {alarmTasks.length === 0 ? (
              <EmptyState icon={Bell} message="No alarm tasks configured." />
            ) : (
              <div className="settings-list">
                {alarmTasks.map(task => (
                  <div key={task.id} className="settings-list-item">
                    <div>
                      <strong>{task.title}</strong>
                      <br /><small>{task.alarm_type} - {task.notification_method}</small>
                    </div>
                    <div className="actions">
                      <span className={`badge ${task.enabled ? 'ok' : ''}`}>{task.enabled ? 'Active' : 'Disabled'}</span>
                      <button className="mini danger" disabled={!!loading} onClick={() => onDeleteAlarmTask?.(task.id)}>Delete</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeSettingsTab === 'service' && (
          <div className="settings-section">
            <h3>System Services</h3>
            <div className="settings-list">
              {services.map(service => (
                <div key={service.name} className="settings-list-item">
                  <div>
                    <strong>{service.name}</strong>
                    <br /><small>{service.version || 'N/A'}</small>
                  </div>
                  <div className="actions">
                    <span className={`badge ${service.active ? 'ok' : 'bad'}`}>{service.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="actions" style={{ marginTop: 16 }}>
        <button disabled={!!loading} onClick={onLoadSettingsData}><RefreshCw size={14}/> Refresh All</button>
      </div>
    </>
  );
}
