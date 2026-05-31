import { RefreshCw, Download, Play, RotateCcw, Archive, Trash2, CheckCircle } from 'lucide-react';
import { formatBytes } from '../utils/formatters';

function EmptyState({ icon, message }) {
  return <div className="empty-state">{icon && <icon size={40} />}<p>{message}</p></div>;
}

export default function Update({
  isAdmin,
  loading,
  updateStatus,
  availableUpdate,
  updateBackups,
  updateSettings,
  updateLogs,
  onLoadUpdateStatus,
  onCheckForUpdates,
  onDownloadUpdate,
  onInstallUpdate,
  onCreateUpdateBackup,
  onLoadUpdateBackups,
  onRestoreUpdateBackup,
  onDeleteUpdateBackup,
  onRollbackUpdate,
  onLoadUpdateSettings,
  onSaveUpdateSettings,
  onLoadUpdateLogs,
  onSetUpdateSettings
}) {
  if (!isAdmin) {
    return <section className="section"><h2>Auto Update</h2><p className="hint">No permission.</p></section>;
  }

  const scheduleOptions = [
    { value: 'disabled', label: 'Disabled - Never' },
    { value: 'daily', label: 'Daily at 3 AM' },
    { value: 'weekly', label: 'Weekly on Sunday' },
    { value: 'monthly', label: 'Monthly on 1st' },
    { value: 'security_only', label: 'Security updates only' },
  ];

  return (
    <>
      <section className="section">
        <div className="section-title">
          <div>
            <h2>Auto Update</h2>
            <p className="hint">Automatically update BPanel from GitHub releases.</p>
          </div>
          <button
            disabled={!!loading}
            onClick={() => {
              onLoadUpdateStatus?.();
              onLoadUpdateSettings?.();
              onLoadUpdateBackups?.();
              onLoadUpdateLogs?.();
            }}
          >
            <RefreshCw size={14}/> Refresh
          </button>
        </div>

        <div className="info-box">
          <div className="update-status">
            <div className="update-version">
              <span className="label">Current Version:</span>
              <strong>{updateStatus?.version || 'Loading...'}</strong>
            </div>
            <div className="update-commit">
              <span className="label">Commit:</span>
              <code>{updateStatus?.commit || '--'}</code>
            </div>
          </div>
        </div>

        <div className="actions" style={{ marginTop: 16, marginBottom: 16 }}>
          <button disabled={!!loading} onClick={onCheckForUpdates}><RefreshCw size={14}/> Check for Updates</button>
        </div>

        {availableUpdate?.available ? (
          <div className="info-box" style={{ borderColor: 'var(--accent)', marginBottom: 16 }}>
            <h3>Update Available</h3>
            <div className="update-info">
              <p><strong>Version:</strong> {availableUpdate.version}</p>
              {availableUpdate.release_name && <p><strong>Release:</strong> {availableUpdate.release_name}</p>}
            </div>
            <div className="actions" style={{ marginTop: 12 }}>
              <button disabled={!!loading} onClick={() => onDownloadUpdate?.(availableUpdate.version)}><Download size={14}/> Download</button>
              <button disabled={!!loading} onClick={() => onInstallUpdate?.(availableUpdate.version)} className="primary"><Play size={14}/> Install Now</button>
            </div>
          </div>
        ) : availableUpdate && !availableUpdate.available ? (
          <div className="info-box" style={{ borderColor: 'var(--success)', marginBottom: 16 }}>
            <p><CheckCircle size={16}/> You are running the latest version ({availableUpdate.current_version})</p>
          </div>
        ) : null}

        <div className="settings-section">
          <h3>Auto Update Settings</h3>
          <div className="settings-form">
            <label className="check-line">
              <input
                type="checkbox"
                checked={updateSettings?.auto_update_enabled || false}
                onChange={e => onSetUpdateSettings?.({ ...updateSettings, auto_update_enabled: e.target.checked })}
              />
              <span>Enable Auto Update</span>
            </label>
            <label className="setting-row">
              <span>Update Schedule:</span>
              <select
                value={updateSettings?.schedule || 'disabled'}
                onChange={e => onSaveUpdateSettings?.({ ...updateSettings, schedule: e.target.value })}
              >
                {scheduleOptions.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </label>
            <label className="check-line">
              <input
                type="checkbox"
                checked={updateSettings?.include_beta || false}
                onChange={e => onSetUpdateSettings?.({ ...updateSettings, include_beta: e.target.checked })}
              />
              <span>Include Beta Versions</span>
            </label>
            <label className="check-line">
              <input
                type="checkbox"
                checked={updateSettings?.auto_backup !== false}
                onChange={e => onSetUpdateSettings?.({ ...updateSettings, auto_backup: e.target.checked })}
              />
              <span>Auto Backup Before Update</span>
            </label>
          </div>
        </div>

        <div className="settings-section">
          <h3>Backups</h3>
          <div className="actions" style={{ marginBottom: 12 }}>
            <button disabled={!!loading} onClick={onCreateUpdateBackup}><Archive size={14}/> Create Backup</button>
          </div>
          {updateBackups.length > 0 ? (
            <div className="backup-list">
              {updateBackups.map(backup => (
                <div className="backup-item" key={backup.id}>
                  <div className="backup-info">
                    <strong>{backup.created_at || backup.id}</strong>
                    <small>Version: {backup.version || 'unknown'}</small>
                    <small>Size: {formatBytes(backup.size)}</small>
                  </div>
                  <div className="actions">
                    <button disabled={!!loading} onClick={() => onRestoreUpdateBackup?.(backup.id)}><RotateCcw size={14}/> Restore</button>
                    <button disabled={!!loading} className="danger" onClick={() => onDeleteUpdateBackup?.(backup.id)}><Trash2 size={14}/></button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="hint">No backups available. Create a backup before updating.</p>
          )}
        </div>

        <div className="settings-section">
          <h3>Rollback</h3>
          <p className="hint">Rollback to the previous version using the most recent backup.</p>
          <button disabled={!!loading || updateBackups.length === 0} onClick={onRollbackUpdate} className="danger"><RotateCcw size={14}/> Rollback to Previous Version</button>
        </div>

        <div className="settings-section">
          <div className="section-title">
            <h3>Update Logs</h3>
            <button disabled={!!loading} onClick={onLoadUpdateLogs}><RefreshCw size={14}/> Refresh</button>
          </div>
          {updateLogs.length > 0 ? (
            <div className="log-output" style={{ maxHeight: 300, overflow: 'auto' }}>
              {updateLogs.map((log, idx) => (
                <div key={idx} className="log-entry">
                  <span className="log-time">{log.timestamp}</span>
                  <span className={`log-level ${log.level}`}>{log.level}</span>
                  <span className="log-message">{log.message}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="hint">No update logs available.</p>
          )}
        </div>
      </section>
    </>
  );
}
