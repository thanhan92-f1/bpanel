import { FileText, RefreshCw } from 'lucide-react';

function EmptyState({ icon, message }) {
  return <div className="empty-state">{icon && <icon size={40} />}<p>{message}</p></div>;
}

export default function Logs({
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
  return (
    <>
      <section className="section">
        <div className="section-title">
          <div>
            <h2>Logs</h2>
            <p className="hint">View system and website logs</p>
          </div>
        </div>
      </section>

      <div className="segmented-control">
        <button className={activeLogTab === 'panel' ? 'active' : ''} onClick={() => setActiveLogTab('panel')}>
          Panel Logs
        </button>
        <button className={activeLogTab === 'website' ? 'active' : ''} onClick={() => setActiveLogTab('website')}>
          Website Logs
        </button>
        <button className={activeLogTab === 'audit' ? 'active' : ''} onClick={() => setActiveLogTab('audit')}>
          Audit Logs
        </button>
        <button className={activeLogTab === 'ssh' ? 'active' : ''} onClick={() => setActiveLogTab('ssh')}>
          SSH Logs
        </button>
        <button className={activeLogTab === 'software' ? 'active' : ''} onClick={() => setActiveLogTab('software')}>
          Software Logs
        </button>
      </div>

      {activeLogTab === 'panel' && (
        <section className="section">
          <div className="log-toolbar">
            <select value={logLines} onChange={e => setLogLines(Number(e.target.value))}>
              <option value={50}>50 lines</option>
              <option value={100}>100 lines</option>
              <option value={200}>200 lines</option>
              <option value={500}>500 lines</option>
              <option value={1000}>1000 lines</option>
            </select>
            <button disabled={!!loading}><RefreshCw size={14}/> Refresh</button>
          </div>
          <pre className="log-output">{panelLogsContent || 'Loading...'}</pre>
        </section>
      )}

      {activeLogTab === 'website' && (
        <section className="section">
          <div className="form-row">
            <select value={selectedWebsiteLogId || ''} onChange={e => setSelectedWebsiteLogId(e.target.value)}>
              <option value="">Select website</option>
              {websites.map(site => (
                <option key={site.id} value={site.id}>{site.domain}</option>
              ))}
            </select>
            <select value={selectedLogType} onChange={e => setSelectedLogType(e.target.value)}>
              <option value="access">Access Log</option>
              <option value="error">Error Log</option>
            </select>
            <select value={logLines} onChange={e => setLogLines(Number(e.target.value))}>
              <option value={50}>50 lines</option>
              <option value={100}>100 lines</option>
              <option value={200}>200 lines</option>
              <option value={500}>500 lines</option>
            </select>
            <button disabled={!!loading}><RefreshCw size={14}/> Refresh</button>
          </div>
          <pre className="log-output">{websiteLogsContent || 'Select a website to view logs.'}</pre>
        </section>
      )}

      {activeLogTab === 'audit' && (
        <section className="section">
          <div className="log-toolbar">
            <button disabled={!!loading}><RefreshCw size={14}/> Refresh</button>
          </div>
          {auditLogs.length === 0 ? (
            <EmptyState icon={FileText} message="No audit logs available." />
          ) : (
            <div className="table">
              <div className="row header-row">
                <span>Timestamp</span>
                <span>Action</span>
                <span>User</span>
                <span>Details</span>
              </div>
              {auditLogs.map((log, idx) => (
                <div className="row" key={idx}>
                  <span><small>{log.timestamp}</small></span>
                  <span>{log.action}</span>
                  <span>{log.username}</span>
                  <span><small>{log.details}</small></span>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {activeLogTab === 'ssh' && (
        <section className="section">
          <div className="log-toolbar">
            <button disabled={!!loading}><RefreshCw size={14}/> Refresh</button>
          </div>
          <pre className="log-output">{sshLogs || 'Loading...'}</pre>
        </section>
      )}

      {activeLogTab === 'software' && (
        <section className="section">
          <div className="form-row">
            <select value={softLogType} onChange={e => setSoftLogType(e.target.value)}>
              <option value="updates">Update Logs</option>
              <option value="installs">Install Logs</option>
              <option value="errors">Error Logs</option>
            </select>
            <select value={logLevel} onChange={e => setLogLevel(e.target.value)}>
              <option value="all">All Levels</option>
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="error">Error</option>
            </select>
            <button disabled={!!loading}><RefreshCw size={14}/> Refresh</button>
          </div>
          <pre className="log-output">{softLogs || 'Loading...'}</pre>
        </section>
      )}
    </>
  );
}
