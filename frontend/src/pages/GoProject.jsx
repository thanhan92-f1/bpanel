import { Hexagon, Plus, RefreshCw, Play, Search, RotateCcw, Square, FileText, Wrench, X } from 'lucide-react';

export default function GoProject({
  goVersion,
  goVersions,
  goProcesses,
  goModules,
  websites,
  selectedWebsiteId,
  loading,
  installingVersion,
  selectedProcess,
  goLogs,
  goBuildPath,
  goRunPath,
  goModulePath,
  onSetSelectedWebsiteId,
  onSetGoBuildPath,
  onSetGoRunPath,
  onSetGoModulePath,
  onLoadGoVersion,
  onLoadGoVersions,
  onLoadGoProcesses,
  onInstallGoVersion,
  onBuildGoProject,
  onRunGoProject,
  onLoadGoModules,
  onSetupGoForWebsite,
  onViewGoProcessLogs,
  onStopGoProcess,
  onRestartGoProcess,
  onSetSelectedProcess
}) {
  return (
    <>
      <section className="section">
        <div className="section-title">
          <h2>Go Project</h2>
          <button disabled={!!loading} onClick={() => {
            onLoadGoVersion?.();
            onLoadGoVersions?.();
            onLoadGoProcesses?.();
          }}>
            <RefreshCw size={15}/> Refresh
          </button>
        </div>
      </section>

      <section className="section">
        <h3>Go Version</h3>
        <div className="info-box">
          <p><strong>Current Version:</strong> {goVersion || 'Loading...'}</p>
        </div>
        <div className="form-row">
          <select
            value={installingVersion}
            onChange={e => {/* handled by parent */}}
            disabled={!!loading}
          >
            <option value="">Select version to install</option>
            {goVersions.filter(v => v !== goVersion).map(v => <option key={v} value={v}>Go {v}</option>)}
          </select>
          <button
            disabled={!!loading || !installingVersion}
            onClick={() => onInstallGoVersion?.(installingVersion)}
          >
            <Plus size={15}/> Install
          </button>
        </div>
      </section>

      <section className="section">
        <h3>Build and Run</h3>
        <div className="form-row">
          <input
            value={goBuildPath}
            onChange={e => onSetGoBuildPath?.(e.target.value)}
            placeholder="Project path"
          />
          <button disabled={!!loading || !goBuildPath} onClick={onBuildGoProject}>
            <Play size={15}/> Build
          </button>
        </div>
        <div className="form-row">
          <input
            value={goRunPath}
            onChange={e => onSetGoRunPath?.(e.target.value)}
            placeholder="Project path to run"
          />
          <button disabled={!!loading || !goRunPath} onClick={onRunGoProject}>
            <Play size={15}/> Run
          </button>
        </div>
      </section>

      <section className="section">
        <h3>Go Modules</h3>
        <div className="form-row">
          <input
            value={goModulePath}
            onChange={e => onSetGoModulePath?.(e.target.value)}
            placeholder="Project path"
          />
          <button disabled={!!loading || !goModulePath} onClick={() => onLoadGoModules?.(goModulePath)}>
            <Search size={15}/> Check
          </button>
        </div>
        {goModules.length > 0 && (
          <div className="table">
            <div className="row header-row"><span>Module</span><span>Version</span></div>
            {goModules.map((mod, idx) => <div className="row" key={idx}><span><strong>{mod.path}</strong></span><span>{mod.version}</span></div>)}
          </div>
        )}
      </section>

      <section className="section">
        <h3>Go Services</h3>
        {goProcesses.length === 0 ? <p className="hint">No Go processes running.</p> : (
          <div className="table">
            <div className="row header-row"><span>Name</span><span>Status</span><span>PID</span><span>Actions</span></div>
            {goProcesses.map(proc => (
              <div className="row" key={proc.name}>
                <span><strong>{proc.name}</strong></span>
                <span className={`badge ${proc.status === 'running' ? 'ok' : ''}`}>{proc.status}</span>
                <span>{proc.pid || '-'}</span>
                <div className="row-actions">
                  <button className="mini secondary-light" disabled={!!loading} onClick={() => onRestartGoProcess?.(proc.name)}><RotateCcw size={13}/> Restart</button>
                  <button className="mini secondary-light" disabled={!!loading} onClick={() => onViewGoProcessLogs?.(proc.name)}><FileText size={13}/> Logs</button>
                  <button className="mini danger" disabled={!!loading} onClick={() => onStopGoProcess?.(proc.name)}><Square size={13}/> Stop</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {selectedProcess && (
        <section className="section">
          <div className="section-title">
            <h3>Logs - {selectedProcess}</h3>
            <button className="secondary-light" onClick={() => onSetSelectedProcess?.(null)}><X size={14}/> Close</button>
          </div>
          <button className="mini secondary-light" onClick={() => onViewGoProcessLogs?.(selectedProcess)}><RefreshCw size={13}/> Refresh</button>
          <pre className="log-output">{goLogs || 'Loading...'}</pre>
        </section>
      )}

      <section className="section">
        <h3>Setup Go for Website</h3>
        <div className="form-row">
          <select value={selectedWebsiteId} onChange={e => onSetSelectedWebsiteId?.(e.target.value)}>
            <option value="">Select website</option>
            {websites.map(site => <option key={site.id} value={site.id}>{site.domain}</option>)}
          </select>
          <button disabled={!!loading || !selectedWebsiteId} onClick={() => onSetupGoForWebsite?.(selectedWebsiteId)}>
            <Wrench size={15}/> Setup
          </button>
        </div>
      </section>
    </>
  );
}
