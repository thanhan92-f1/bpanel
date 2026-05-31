import { Box, RefreshCw, Plus, RotateCcw, Square, FileText, Trash2, Download } from 'lucide-react';
import { formatBytes, formatNodeUptime } from '../utils/formatters';

function EmptyState({ icon, message }) {
  return <div className="empty-state">{icon && <icon size={40} />}<p>{message}</p></div>;
}

export default function NodeJS({
  nodeVersion,
  nodeVersions,
  pm2Processes,
  websites,
  selectedWebsiteId,
  loading,
  installingVersion,
  pm2LogModal,
  pm2Logs,
  onSetSelectedWebsiteId,
  onLoadNodeVersion,
  onLoadNodeVersions,
  onLoadPm2Processes,
  onInstallNodeVersion,
  onRestartPm2Process,
  onStopPm2Process,
  onDeletePm2Process,
  onLoadPm2Logs,
  onSetupPm2ForWebsite,
  onSetPm2LogModal
}) {
  return (
    <>
      <section className="section">
        <div className="section-title">
          <div>
            <h2>Node.js Management</h2>
            <p className="hint">Current version: <strong>{nodeVersion || 'Loading...'}</strong></p>
          </div>
          <button disabled={!!loading} onClick={() => {
            onLoadNodeVersion?.();
            onLoadNodeVersions?.();
            onLoadPm2Processes?.();
          }}>
            <RefreshCw size={15}/> Refresh
          </button>
        </div>
      </section>

      <section className="section">
        <h2>Node.js Versions</h2>
        <p className="hint">Install and manage Node.js versions using nvm.</p>
        {nodeVersions.length === 0 ? <p className="hint">Loading...</p> : (
          <div className="table">
            <div className="row header-row"><span>Version</span><span>Actions</span></div>
            {nodeVersions.map(version => (
              <div className="row" key={version}>
                <span><strong>{version}</strong></span>
                <div className="row-actions">
                  {nodeVersion === version ? <span className="badge ok">Current</span> : (
                    <button className="mini" disabled={!!loading || installingVersion === version} onClick={() => onInstallNodeVersion?.(version)}>
                      <Download size={13}/> Install
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="section">
        <h2>PM2 Process Manager</h2>
        <p className="hint">Manage Node.js applications with PM2 process manager.</p>
        <div className="form-row">
          <select value={selectedWebsiteId} onChange={e => onSetSelectedWebsiteId?.(e.target.value)}>
            <option value="">Select website</option>
            {websites.map(site => <option key={site.id} value={site.id}>{site.domain}</option>)}
          </select>
          <button disabled={!!loading || !selectedWebsiteId} onClick={() => onSetupPm2ForWebsite?.(selectedWebsiteId)}>
            <Plus size={14}/> Setup PM2
          </button>
        </div>
        {pm2Processes.length === 0 ? <EmptyState icon={Box} message="No PM2 processes found." /> : (
          <div className="table">
            <div className="row header-row"><span>Name</span><span>Status</span><span>CPU</span><span>Memory</span><span>Uptime</span><span>Actions</span></div>
            {pm2Processes.map(proc => (
              <div className="row" key={proc.name}>
                <span><strong>{proc.name}</strong></span>
                <span className={`badge ${proc.status === 'online' ? 'ok' : proc.status === 'errored' ? 'bad' : ''}`}>{proc.status || 'unknown'}</span>
                <span>{proc.cpu !== undefined ? `${proc.cpu}%` : '-'}</span>
                <span>{proc.memory ? formatBytes(proc.memory) : '-'}</span>
                <span>{proc.uptime ? formatNodeUptime(proc.uptime) : '-'}</span>
                <div className="row-actions">
                  <button className="mini" disabled={!!loading} onClick={() => onRestartPm2Process?.(proc.name)}><RotateCcw size={13}/> Restart</button>
                  {proc.status !== 'stopped' && proc.status !== 'errored' && (
                    <button className="mini" disabled={!!loading} onClick={() => onStopPm2Process?.(proc.name)}><Square size={13}/> Stop</button>
                  )}
                  <button className="mini secondary-light" disabled={!!loading} onClick={() => onLoadPm2Logs?.(proc.name)}><FileText size={13}/> Logs</button>
                  <button className="mini danger" disabled={!!loading} onClick={() => onDeletePm2Process?.(proc.name)}><Trash2 size={13}/></button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {pm2LogModal && (
        <section className="section log-viewer">
          <div className="section-title">
            <div><h2>PM2 Logs - {pm2LogModal}</h2></div>
            <button className="secondary-light" onClick={() => onSetPm2LogModal?.(null)}><X size={14}/> Close</button>
          </div>
          <div className="log-toolbar">
            <select value={pm2Logs.lines} onChange={e => onLoadPm2Logs?.(pm2LogModal, Number(e.target.value))} disabled={!!loading}>
              <option value={50}>50 lines</option>
              <option value={100}>100 lines</option>
              <option value={200}>200 lines</option>
              <option value={500}>500 lines</option>
            </select>
            <button disabled={!!loading} onClick={() => onLoadPm2Logs?.(pm2LogModal, pm2Logs.lines)}><RefreshCw size={14}/> Refresh</button>
          </div>
          <pre className="log-output">{pm2Logs.content || 'Loading...'}</pre>
        </section>
      )}
    </>
  );
}

import { X } from 'lucide-react';
