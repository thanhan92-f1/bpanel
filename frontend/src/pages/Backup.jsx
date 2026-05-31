import { Package, History, HardDrive, RotateCcw, Play, Edit, Trash2, Download, Check, Plus, RefreshCw, AlertTriangle } from 'lucide-react';

function EmptyState({ icon, message }) {
  return <div className="empty-state">{icon && <icon size={40} />}<p>{message}</p></div>;
}

export default function Backup({
  backupJobs,
  backupHistory,
  storageConfigs,
  loading,
  backupActiveTab,
  excludePatterns,
  websites,
  databases,
  editingBackupJob,
  showBackupJobModal,
  showStorageModal,
  storageModalType,
  onSetBackupActiveTab,
  onLoadBackupJobs,
  onLoadBackupHistory,
  onLoadStorageConfigs,
  onOpenBackupJobModal,
  onCloseBackupJobModal,
  onOpenStorageModal,
  onCloseStorageModal,
  onSaveBackupJob,
  onUpdateBackupJob,
  onDeleteBackupJob,
  onRunBackupJob,
  onToggleJobEnabled,
  onConfigureStorage,
  onTestStorageConnection,
  onDeleteStorageConfig,
  onSetEditingBackupJob
}) {
  const BACKUP_TABS = [
    { key: 'jobs', label: 'Backup Jobs', icon: Package },
    { key: 'history', label: 'History', icon: History },
    { key: 'storage', label: 'Storage', icon: HardDrive },
    { key: 'restore', label: 'Restore', icon: RotateCcw },
  ];

  function formatSize(bytes) {
    if (!bytes) return '0 B';
    for (const unit of ['B', 'KB', 'MB', 'GB', 'TB']) {
      if (bytes < 1024) return `${bytes.toFixed(2)} ${unit}`;
      bytes /= 1024;
    }
    return `${bytes.toFixed(2)} PB`;
  }

  function getDestinationIcon(type) {
    const icons = { local: HardDrive, ftp: Upload, ssh: Server, s3: Cloud, onedrive: Cloud, webdav: Link, b2: HardDrive };
    return icons[type] || HardDrive;
  }

  return (
    <>
      <section className="section backup-section">
        <div className="section-title">
          <h2>Enhanced Backup</h2>
          <button
            disabled={!!loading}
            onClick={() => {
              onLoadBackupJobs?.();
              onLoadBackupHistory?.();
              onLoadStorageConfigs?.();
            }}
          >
            <RefreshCw size={15}/> Refresh
          </button>
        </div>

        <div className="segmented-control">
          {BACKUP_TABS.map(tab => (
            <button
              key={tab.key}
              className={backupActiveTab === tab.key ? 'active' : ''}
              onClick={() => onSetBackupActiveTab?.(tab.key)}
            >
              <tab.icon size={15}/> {tab.label}
            </button>
          ))}
        </div>

        <div className="tab-content">
          {backupActiveTab === 'jobs' && (
            <div className="backup-jobs-tab">
              <div className="section-actions">
                <button disabled={!!loading} onClick={() => onOpenBackupJobModal?.()}>
                  <Plus size={14}/> Create Job
                </button>
              </div>

              {backupJobs.length === 0 ? (
                <EmptyState icon={Package} message="No backup jobs configured." />
              ) : (
                <div className="jobs-grid">
                  {backupJobs.map(job => (
                    <div key={job.id} className="job-card">
                      <div className="job-header">
                        <h3>{job.name}</h3>
                        <span className={`badge ${job.job_type === 'full' ? 'ok' : 'info'}`}>{job.job_type}</span>
                      </div>
                      <div className="job-destinations">
                        <span className="label">Destinations:</span>
                        {(job.destinations || []).map(dest => {
                          const Icon = getDestinationIcon(dest);
                          return <span key={dest} className="destination-badge"><Icon size={14}/></span>;
                        })}
                      </div>
                      <div className="job-meta">
                        <span><Clock size={12}/> {job.schedule || 'Manual'}</span>
                        <span><Shield size={12}/> {job.retention_days || 30} days</span>
                      </div>
                      <div className="job-actions">
                        <label className="toggle">
                          <input type="checkbox" checked={job.enabled} onChange={() => onToggleJobEnabled?.(job)} />
                          <span>{job.enabled ? 'Enabled' : 'Disabled'}</span>
                        </label>
                        <button className="mini" disabled={!!loading} onClick={() => onRunBackupJob?.(job.id)}>
                          <Play size={13}/> Run Now
                        </button>
                        <button className="mini secondary-light" disabled={!!loading} onClick={() => { onSetEditingBackupJob?.(job); onOpenBackupJobModal?.(); }}>
                          <Edit size={13}/>
                        </button>
                        <button className="mini danger" disabled={!!loading} onClick={() => onDeleteBackupJob?.(job.id)}>
                          <Trash2 size={13}/>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {backupActiveTab === 'history' && (
            <div className="backup-history-tab">
              <div className="stats-row">
                <div className="stat-card">
                  <span className="stat-value">{backupHistory.filter(b => b.status === 'completed').length}</span>
                  <span className="stat-label">Completed</span>
                </div>
                <div className="stat-card">
                  <span className="stat-value">{backupHistory.filter(b => b.status === 'failed').length}</span>
                  <span className="stat-label">Failed</span>
                </div>
                <div className="stat-card">
                  <span className="stat-value">{formatSize(backupHistory.reduce((sum, b) => sum + (b.file_size || 0), 0))}</span>
                  <span className="stat-label">Total Size</span>
                </div>
              </div>

              {backupHistory.length === 0 ? (
                <EmptyState icon={History} message="No backup history yet." />
              ) : (
                <div className="table">
                  <div className="row header-row">
                    <span>Date</span><span>Type</span><span>Size</span><span>Status</span><span>Actions</span>
                  </div>
                  {backupHistory.map(backup => (
                    <div className="row" key={backup.id}>
                      <span>{new Date(backup.started_at).toLocaleString()}</span>
                      <span className="badge">{backup.backup_type}</span>
                      <span>{formatSize(backup.file_size)}</span>
                      <span className={`badge ${backup.status === 'completed' ? 'ok' : backup.status === 'failed' ? 'bad' : ''}`}>{backup.status}</span>
                      <div className="row-actions">
                        <button className="mini" disabled={!!loading || backup.status !== 'completed'} onClick={() => {}}><Download size={13}/></button>
                        <button className="mini" disabled={!!loading} onClick={() => {}}><Check size={13}/></button>
                        <button className="mini danger" disabled={!!loading} onClick={() => {}}><Trash2 size={13}/></button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {backupActiveTab === 'storage' && (
            <div className="backup-storage-tab">
              <div className="storage-grid">
                {['local', 'ftp', 'ssh', 's3', 'onedrive', 'google_drive', 'webdav', 'b2'].map(type => (
                  <div key={type} className="storage-card" onClick={() => onOpenStorageModal?.(type)}>
                    <HardDrive size={32}/>
                    <h4>{type.toUpperCase()}</h4>
                    <p>{type} storage</p>
                  </div>
                ))}
              </div>

              {storageConfigs.length > 0 && (
                <div className="configured-storages">
                  <h3>Configured Storage</h3>
                  <div className="table">
                    <div className="row header-row">
                      <span>Name</span><span>Type</span><span>Actions</span>
                    </div>
                    {storageConfigs.map(config => (
                      <div className="row" key={config.id}>
                        <span><strong>{config.name}</strong></span>
                        <span>{config.storage_type}</span>
                        <div className="row-actions">
                          <button className="mini" disabled={!!loading} onClick={() => onTestStorageConnection?.(config.id)}>Test</button>
                          <button className="mini danger" disabled={!!loading} onClick={() => onDeleteStorageConfig?.(config.id)}><Trash2 size={13}/></button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {backupActiveTab === 'restore' && (
            <div className="backup-restore-tab">
              <div className="info-box">
                <p><AlertTriangle size={16}/> Select a backup from the History tab to restore.</p>
                <button disabled={!!loading} onClick={() => onSetBackupActiveTab?.('history')}>
                  <History size={14}/> Go to History
                </button>
              </div>
            </div>
          )}
        </div>
      </section>
    </>
  );
}

// Additional imports needed
import { Upload, Server, Cloud, Shield, Clock } from 'lucide-react';
