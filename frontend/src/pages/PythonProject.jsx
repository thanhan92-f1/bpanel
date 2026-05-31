import { TerminalIcon, Plus, Package, Trash2, Download, X, RefreshCw, Square } from 'lucide-react';
import { formatBytes } from '../utils/formatters';

function EmptyState({ icon, message }) {
  return <div className="empty-state">{icon && <icon size={40} />}<p>{message}</p></div>;
}

export default function PythonProject({
  pythonVersion,
  pythonVersions,
  venvs,
  selectedVenv,
  venvPackages,
  pythonProcesses,
  loading,
  newVenvName,
  newVenvVersion,
  installPackageName,
  onSetNewVenvName,
  onSetNewVenvVersion,
  onSetInstallPackageName,
  onCreateVenv,
  onDeleteVenv,
  onLoadVenvPackages,
  onInstallVenvPackage,
  onUninstallVenvPackage,
  onLoadPythonVersion,
  onLoadPythonVersions,
  onLoadVenvs,
  onLoadPythonProcesses,
  onSetSelectedVenv
}) {
  return (
    <>
      <section className="section">
        <div className="section-title">
          <h2>Python</h2>
          <button disabled={!!loading} onClick={() => {
            onLoadPythonVersion?.();
            onLoadPythonVersions?.();
            onLoadVenvs?.();
            onLoadPythonProcesses?.();
          }}>
            <RefreshCw size={15}/> Refresh
          </button>
        </div>
      </section>

      <section className="section">
        <h3>Python Version</h3>
        <div className="info-box">
          <p><strong>Current Python:</strong> {pythonVersion || 'Loading...'}</p>
          <p><strong>Available versions:</strong> {pythonVersions.length > 0 ? pythonVersions.join(', ') : 'Loading...'}</p>
        </div>
      </section>

      <section className="section">
        <h3>Virtual Environments</h3>
        <div className="form-row">
          <input
            value={newVenvName}
            onChange={e => onSetNewVenvName?.(e.target.value)}
            placeholder="venv name"
          />
          <select
            value={newVenvVersion}
            onChange={e => onSetNewVenvVersion?.(e.target.value)}
          >
            <option value="">Default Python</option>
            {pythonVersions.map(v => <option key={v} value={v}>Python {v}</option>)}
          </select>
          <button disabled={!!loading || !newVenvName} onClick={onCreateVenv}>
            <Plus size={14}/> Create venv
          </button>
        </div>

        {venvs.length === 0 ? <p className="hint">No virtual environments found.</p> : (
          <div className="table">
            <div className="row header-row">
              <span>Name</span><span>Python</span><span>Path</span><span>Actions</span>
            </div>
            {venvs.map(venv => (
              <div className="row" key={venv.id}>
                <span><strong>{venv.name}</strong></span>
                <span>{venv.python_version || 'default'}</span>
                <span><small>{venv.path}</small></span>
                <div className="row-actions">
                  <button className="mini secondary-light" disabled={!!loading} onClick={() => onLoadVenvPackages?.(venv.id)}>
                    <Package size={13}/> Packages
                  </button>
                  <button className="mini danger" disabled={!!loading} onClick={() => onDeleteVenv?.(venv.id)}>
                    <Trash2 size={13}/> Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {selectedVenv && (
        <section className="section">
          <h3>Packages - {selectedVenv.name}</h3>
          <div className="form-row">
            <input
              value={installPackageName}
              onChange={e => onSetInstallPackageName?.(e.target.value)}
              placeholder="package name (e.g., requests)"
            />
            <button disabled={!!loading || !installPackageName} onClick={() => onInstallVenvPackage?.(selectedVenv.id)}>
              <Download size={14}/> Install
            </button>
            <button className="secondary-light" onClick={() => onSetSelectedVenv?.(null)}>
              <X size={14}/> Close
            </button>
          </div>

          {venvPackages.length === 0 ? <p className="hint">No packages installed or loading...</p> : (
            <div className="table">
              <div className="row header-row">
                <span>Package</span><span>Version</span><span>Actions</span>
              </div>
              {venvPackages.map(pkg => (
                <div className="row" key={pkg.name}>
                  <span><strong>{pkg.name}</strong></span>
                  <span>{pkg.version}</span>
                  <div className="row-actions">
                    <button className="mini danger" disabled={!!loading} onClick={() => onUninstallVenvPackage?.(selectedVenv.id, pkg.name)}>
                      <Trash2 size={13}/> Uninstall
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      <section className="section">
        <h3>Python Processes</h3>
        <button className="mini" disabled={!!loading} onClick={onLoadPythonProcesses}>
          <RefreshCw size={13}/> Refresh
        </button>

        {pythonProcesses.length === 0 ? <p className="hint">No Python processes running.</p> : (
          <div className="table">
            <div className="row header-row">
              <span>Name</span><span>PID</span><span>Status</span><span>Actions</span>
            </div>
            {pythonProcesses.map(proc => (
              <div className="row" key={proc.pid}>
                <span><strong>{proc.name}</strong></span>
                <span>{proc.pid}</span>
                <span className="badge ok">{proc.status}</span>
                <div className="row-actions">
                  <button className="mini danger" disabled={!!loading}>
                    <Square size={13}/> Stop
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
