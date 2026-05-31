import { Container, Image, Play, Square, RotateCcw, Eye, Trash2, Download, RefreshCw, AlertCircle } from 'lucide-react';

function EmptyState({ icon: Icon = AlertCircle, message = 'No data yet' }) {
  return <div className="empty-state"><Icon size={40} /><p>{message}</p></div>;
}

export default function Docker({
  dockerStatus,
  containers,
  images,
  loading,
  selectedContainer,
  containerLogs,
  onLoadDockerStatus,
  onLoadContainers,
  onLoadImages,
  onStartContainer,
  onStopContainer,
  onRestartContainer,
  onGetContainerLogs,
  onDeleteContainer,
  onPullImage,
  onDeleteImage,
  onSelectContainer,
  onCloseLogs
}) {
  const isRunning = dockerStatus?.running || dockerStatus?.status === 'running';

  return (
    <>
      <section className="section">
        <div className="section-title">
          <div>
            <h2>Docker Management</h2>
            <p className="hint">Status: {isRunning ? <span className="badge ok">Running</span> : <span className="badge bad">Not Running</span>}</p>
          </div>
          <button disabled={!!loading} onClick={() => { onLoadDockerStatus?.(); onLoadContainers?.(); onLoadImages?.(); }}>
            <RefreshCw size={15}/> Refresh
          </button>
        </div>
        {!isRunning && <div className="info-box"><p>Docker is not running. Start the Docker service to manage containers and images.</p></div>}
      </section>

      <section className="section">
        <h2>Containers</h2>
        {containers.length === 0 ? <EmptyState icon={Container} message="No containers found." /> : (
          <div className="table">
            <div className="row header-row">
              <span>Name</span>
              <span>Image</span>
              <span>Status</span>
              <span>Ports</span>
              <span>Actions</span>
            </div>
            {containers.map(container => (
              <div className="row" key={container.id}>
                <span><strong>{container.name || container.names?.[0] || container.id?.substring(0, 12)}</strong></span>
                <span>{container.image}</span>
                <span className={`badge ${container.state === 'running' ? 'ok' : ''}`}>{container.state || container.status}</span>
                <span>{container.ports || '-'}</span>
                <div className="row-actions">
                  {container.state !== 'running' && <button className="mini" disabled={!!loading} onClick={() => onStartContainer?.(container.id)}><Play size={13}/> Start</button>}
                  {container.state === 'running' && <button className="mini" disabled={!!loading} onClick={() => onStopContainer?.(container.id)}><Square size={13}/> Stop</button>}
                  <button className="mini" disabled={!!loading} onClick={() => onRestartContainer?.(container.id)}><RotateCcw size={13}/> Restart</button>
                  <button className="mini secondary-light" disabled={!!loading} onClick={() => onGetContainerLogs?.(container.id)}><Eye size={13}/> Logs</button>
                  <button className="mini danger" disabled={!!loading} onClick={() => onDeleteContainer?.(container.id)}><Trash2 size={13}/></button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="section">
        <h2>Images</h2>
        <div className="actions" style={{marginBottom: 12}}>
          <button disabled={!!loading} onClick={onPullImage}><Download size={15}/> Pull Image</button>
        </div>
        {images.length === 0 ? <EmptyState icon={Image} message="No images found." /> : (
          <div className="table">
            <div className="row header-row">
              <span>Repository</span>
              <span>Tag</span>
              <span>Size</span>
              <span>Actions</span>
            </div>
            {images.map(image => (
              <div className="row" key={image.id}>
                <span><strong>{image.repository || image.repo}</strong></span>
                <span>{image.tag}</span>
                <span>{image.size}</span>
                <div className="row-actions">
                  <button className="mini danger" disabled={!!loading} onClick={() => onDeleteImage?.(image.id)}><Trash2 size={13}/></button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {selectedContainer && (
        <section className="section docker-logs-modal">
          <div className="section-title">
            <div>
              <h2>Container Logs</h2>
              <p className="hint">Container: {containers.find(c => c.id === selectedContainer)?.name || selectedContainer}</p>
            </div>
            <button className="secondary-light" onClick={onCloseLogs}><X size={14}/> Close</button>
          </div>
          <div className="log-toolbar">
            <button disabled={!!loading} onClick={() => onGetContainerLogs?.(selectedContainer)}><RefreshCw size={14}/> Refresh</button>
          </div>
          <textarea
            className="code-editor"
            value={containerLogs}
            readOnly
            rows={20}
            style={{ fontFamily: 'monospace', background: '#1e1e1e', color: '#d4d4d4' }}
          />
        </section>
      )}
    </>
  );
}

import { X } from 'lucide-react';
