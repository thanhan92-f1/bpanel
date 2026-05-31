import React from 'react';
import { RefreshCw, ServerCog, Shield, Globe, CheckCircle, XCircle, AlertTriangle, Play, Square, RotateCcw, Wrench } from 'lucide-react';

export function renderWebserver({ isAdmin, loading, currentEngine, webEngines, webserverStatus, safetyCheck, websitesWithEngines, loadWebEngines, loadWebsiteEngines, switchWebEngine, loadEngineStatus, repairEngine, checkSafety, restoreConfig, setWebsiteEngine, runServiceAction, EmptyState }) {
  if (!isAdmin) return <section className="section"><h2>WebServer</h2><p className="hint">No permission.</p></section>;

  const engineNames = ['nginx', 'apache', 'openlitespeed', 'litespeed'];
  const engineLabels = { nginx: 'Nginx', apache: 'Apache', openlitespeed: 'OpenLiteSpeed', litespeed: 'LiteSpeed Enterprise' };

  const isEngineRunning = (engine) => {
    const status = webserverStatus[engine];
    if (!status) return null;
    const text = `${status.stdout || ''} ${status.stderr || ''}`;
    return text.includes('active (running)') ? true : text.includes('inactive') || text.includes('failed') ? false : null;
  };

  return <>
    <section className="section">
      <div className="section-title">
        <div><h2>WebServer Engines</h2><p className="hint">Manage web server engines and switch between them.</p></div>
        <button disabled={!!loading} onClick={() => { loadWebEngines(); loadWebsiteEngines(); }}><RefreshCw size={14}/> Refresh</button>
      </div>
      <div className="info-box">
        <div className="webserver-current"><span><ServerCog size={18}/></span><div><strong>Current Engine:</strong><span className={`badge ${currentEngine ? 'ok' : ''}`}>{currentEngine || 'None'}</span></div></div>
      </div>
      <div className="engine-grid">
        {engineNames.map(engine => {
          const engineInfo = webEngines.find(e => e?.name === engine || e?.engine === engine);
          const installed = engineInfo?.installed || false;
          const running = isEngineRunning(engine);
          return (
            <div className="engine-card" key={engine}>
              <div className="engine-header"><span className="engine-name">{engineLabels[engine]}</span><span className={`badge ${installed ? 'ok' : ''}`}>{installed ? 'Installed' : 'Not Installed'}</span></div>
              <div className="engine-status">
                {running === true && <span className="status-running"><CheckCircle size={14}/> Running</span>}
                {running === false && <span className="status-stopped"><XCircle size={14}/> Stopped</span>}
                {running === null && <span className="status-unknown"><AlertTriangle size={14}/> Unknown</span>}
              </div>
              <div className="engine-actions">
                {installed && (<>
                  {currentEngine !== engine && <button disabled={!!loading || (safetyCheck && !safetyCheck.can_switch)} onClick={() => switchWebEngine(engine)}><Play size={13}/> Switch</button>}
                  {currentEngine === engine && <span className="current-label"><CheckCircle size={13}/> Active</span>}
                  <button disabled={!!loading} onClick={() => loadEngineStatus(engine)}><RefreshCw size={13}/> Status</button>
                  <button disabled={!!loading} onClick={() => repairEngine(engine)}><Wrench size={13}/> Repair</button>
                </>)}
                {!installed && <span className="hint">Not installed</span>}
              </div>
            </div>
          );
        })}
      </div>
    </section>
    <section className="section">
      <div className="section-title">
        <div><h2>Safety Check</h2><p className="hint">Check if it is safe to switch web server engines.</p></div>
        <button disabled={!!loading} onClick={checkSafety}><Shield size={14}/> Run Safety Check</button>
      </div>
      {safetyCheck ? (
        <div className="safety-results">
          <div className="safety-header">
            {safetyCheck.can_switch ? <span className="safety-pass"><CheckCircle size={18}/> Safe to switch</span> : <span className="safety-fail"><XCircle size={18}/> Not safe to switch</span>}
          </div>
          <div className="safety-checks">
            {safetyCheck.checks?.map((check, i) => (
              <div className={`safety-check-item ${check.passed ? 'passed' : 'failed'}`} key={i}>
                {check.passed ? <CheckCircle size={14}/> : <XCircle size={14}/>}
                <span>{check.name}</span>
                {check.message && <small>{check.message}</small>}
              </div>
            ))}
          </div>
          {safetyCheck.warnings?.length > 0 && <div className="safety-warnings"><h4><AlertTriangle size={14}/> Warnings</h4>{safetyCheck.warnings.map((w, i) => <p key={i}>{w}</p>)}</div>}
          {safetyCheck.recommendations?.length > 0 && <div className="safety-recommendations"><h4>Recommendations</h4>{safetyCheck.recommendations.map((r, i) => <p key={i}>{r}</p>)}</div>}
          {safetyCheck.can_switch && <div className="actions"><button className="secondary-light" disabled={!!loading} onClick={restoreConfig}><RotateCcw size={14}/> Restore Original Config</button></div>}
        </div>
      ) : <p className="hint">Click "Run Safety Check" to verify if switching is safe.</p>}
    </section>
    <section className="section">
      <div className="section-title">
        <div><h2>Per-Site WebEngine</h2><p className="hint">Configure the web server engine for each website.</p></div>
        <button disabled={!!loading} onClick={loadWebsiteEngines}><RefreshCw size={14}/> Refresh</button>
      </div>
      {websitesWithEngines.length === 0 ? <EmptyState icon={Globe} message="No websites found." /> : (
        <div className="table">
          <div className="row header-row"><span>Website</span><span>Current Engine</span><span>Status</span><span>Action</span></div>
          {websitesWithEngines.map(site => (
            <div className="row" key={site.id}>
              <span><strong>{site.domain}</strong></span>
              <span>{site.web_engine || currentEngine || 'Default'}</span>
              <span className="badge">{site.status || 'Active'}</span>
              <div className="row-actions">
                <select value={site.web_engine || ''} onChange={e => setWebsiteEngine(site.id, e.target.value)}>
                  <option value="">Default ({currentEngine || 'System'})</option>
                  {engineNames.map(e => <option key={e} value={e}>{engineLabels[e]}</option>)}
                </select>
                <button disabled={!!loading} onClick={() => setWebsiteEngine(site.id, site.web_engine)}>Apply</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
    <section className="section">
      <div className="section-title"><div><h2>Ports</h2><p className="hint">Web server ports configuration.</p></div></div>
      <div className="info-box"><h4>Used Ports</h4><p className="hint">Common web server ports in use.</p></div>
      <div className="ports-grid">
        <div className="port-card"><span className="port-number">80</span><span className="port-label">HTTP</span></div>
        <div className="port-card"><span className="port-number">443</span><span className="port-label">HTTPS</span></div>
        <div className="port-card"><span className="port-number">8188-8290</span><span className="port-label">LiteSpeed Admin</span></div>
      </div>
      <div className="info-box"><h4>Reserved Ports</h4><p className="hint">Ports reserved: 80 (HTTP), 443 (HTTPS), 8188-8290 (LiteSpeed Admin)</p></div>
    </section>
    <section className="section">
      <div className="section-title"><div><h2>Service Control</h2><p className="hint">Start, stop, and restart individual web server engines.</p></div></div>
      <div className="service-grid">
        {engineNames.filter(e => webEngines.find(eng => eng?.name === e || eng?.engine === e)?.installed).map(engine => {
          const running = isEngineRunning(engine);
          return (
            <div className="service-card" key={engine}>
              <div><strong>{engineLabels[engine]}</strong><span className={`badge ${running ? 'ok' : ''}`}>{running ? 'Running' : 'Stopped'}</span></div>
              <small>{engine} service</small>
              <div className="service-actions">
                {running ? (<><button disabled={!!loading} onClick={() => runServiceAction(engine, 'stop')}><Square size={13}/> Stop</button><button disabled={!!loading} onClick={() => runServiceAction(engine, 'restart')}><RotateCcw size={13}/> Restart</button></>) : <button disabled={!!loading} onClick={() => runServiceAction(engine, 'start')}><Play size={13}/> Start</button>}
                <button disabled={!!loading} onClick={() => loadEngineStatus(engine)}><RefreshCw size={13}/> Refresh</button>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  </>;
}
