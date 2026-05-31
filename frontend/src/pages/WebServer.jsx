import { ServerCog, RefreshCw, RotateCcw } from 'lucide-react';

function EmptyState({ icon, message }) {
  return <div className="empty-state">{icon && <icon size={40} />}<p>{message}</p></div>;
}

export default function WebServer({
  isAdmin,
  loading,
  currentEngine,
  webEngines,
  webserverStatus,
  safetyCheck,
  websitesWithEngines,
  onLoadWebEngines,
  onLoadWebsiteEngines,
  onSwitchWebEngine,
  onLoadEngineStatus,
  onRepairEngine,
  onCheckSafety,
  onRestoreConfig,
  onSetWebsiteEngine,
  onRunServiceAction
}) {
  if (!isAdmin) {
    return <section className="section"><h2>WebServer</h2><p className="hint">No permission.</p></section>;
  }

  return (
    <>
      <section className="section">
        <div className="section-title">
          <div>
            <h2>Multi-WebServer</h2>
            <p className="hint">Switch between Nginx, Apache, and LiteSpeed.</p>
          </div>
          <button disabled={!!loading} onClick={() => {
            onLoadWebEngines?.();
            onLoadWebsiteEngines?.();
          }}>
            <RefreshCw size={15}/> Refresh
          </button>
        </div>
      </section>

      <section className="section">
        <h3>Web Engines</h3>
        <p className="hint">Select the web server engine to use.</p>
        <div className="webserver-grid">
          {webEngines.map(engine => (
            <div key={engine.name} className={`webserver-card ${currentEngine === engine.name ? 'active' : ''}`}>
              <h4>{engine.name}</h4>
              <p>{engine.description || 'Web server engine'}</p>
              <div className="webserver-status">
                <span className={`badge ${engine.active ? 'ok' : ''}`}>
                  {engine.active ? 'Active' : 'Inactive'}
                </span>
              </div>
              {currentEngine !== engine.name && (
                <button
                  className="mini"
                  disabled={!!loading}
                  onClick={() => onSwitchWebEngine?.(engine.name)}
                >
                  Switch to {engine.name}
                </button>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="section">
        <h3>Website Engines</h3>
        {websitesWithEngines.length === 0 ? (
          <EmptyState icon={ServerCog} message="No websites configured." />
        ) : (
          <div className="table">
            <div className="row header-row">
              <span>Website</span>
              <span>Engine</span>
              <span>Status</span>
              <span>Actions</span>
            </div>
            {websitesWithEngines.map(site => (
              <div className="row" key={site.id}>
                <span><strong>{site.domain}</strong></span>
                <span>{site.engine || 'default'}</span>
                <span className={`badge ${site.engine_status === 'running' ? 'ok' : ''}`}>
                  {site.engine_status || 'unknown'}
                </span>
                <div className="row-actions">
                  <select
                    value={site.engine || ''}
                    onChange={e => onSetWebsiteEngine?.(site.id, e.target.value)}
                    disabled={!!loading}
                  >
                    {webEngines.map(eng => (
                      <option key={eng.name} value={eng.name}>{eng.name}</option>
                    ))}
                  </select>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="section">
        <h3>Safety Check</h3>
        <div className="actions">
          <button disabled={!!loading} onClick={onCheckSafety}>
            <ServerCog size={14}/> Run Safety Check
          </button>
          <button className="secondary-light" disabled={!!loading} onClick={onRestoreConfig}>
            <RotateCcw size={14}/> Restore Default Config
          </button>
        </div>
        {safetyCheck && (
          <div className="info-box">
            <pre>{JSON.stringify(safetyCheck, null, 2)}</pre>
          </div>
        )}
      </section>
    </>
  );
}
