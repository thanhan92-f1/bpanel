import { Activity, Cpu, MemoryStick, HardDrive } from 'lucide-react';
import { formatBytes, formatPercent, clampPercent, formatNumber } from '../utils/formatters';

function EmptyState({ icon, message }) {
  return <div className="empty-state">{icon && <icon size={40} />}<p>{message}</p></div>;
}

export default function Monitor({
  monitorData,
  loading,
  autoRefresh,
  refreshInterval,
  onSetAutoRefresh,
  onSetRefreshInterval,
  onLoadMonitorData
}) {
  const sysInfo = monitorData?.system_info || {};
  const cpuInfo = monitorData?.cpu_info || {};
  const load = monitorData?.load || {};
  const cpu = monitorData?.cpu || {};
  const memory = monitorData?.memory || {};
  const swap = monitorData?.swap || {};
  const diskUsage = monitorData?.disk_usage || {};
  const diskIo = monitorData?.disk_io || {};
  const networkIo = monitorData?.network_io || {};
  const processes = monitorData?.processes || [];

  return (
    <>
      <section className="section">
        <div className="section-title">
          <div>
            <h2>System Monitor</h2>
            <p className="hint">{sysInfo.hostname} - {sysInfo.os}</p>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <label className="check-line" style={{ margin: 0 }}>
              <input type="checkbox" checked={autoRefresh} onChange={e => onSetAutoRefresh?.(e.target.checked)} />
              <span>Auto-refresh</span>
            </label>
            <select value={refreshInterval} onChange={e => onSetRefreshInterval?.(Number(e.target.value))} disabled={!autoRefresh}>
              <option value={1000}>1s</option>
              <option value={2000}>2s</option>
              <option value={5000}>5s</option>
              <option value={10000}>10s</option>
            </select>
            <button disabled={!!loading} onClick={onLoadMonitorData}>
              <RefreshCw size={15}/> Refresh
            </button>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>System Information</h2>
        <div className="monitor-info-grid">
          <div className="monitor-info-item">
            <span className="monitor-info-label">Hostname</span>
            <span className="monitor-info-value">{sysInfo.hostname || '--'}</span>
          </div>
          <div className="monitor-info-item">
            <span className="monitor-info-label">Operating System</span>
            <span className="monitor-info-value">{sysInfo.os || '--'}</span>
          </div>
          <div className="monitor-info-item">
            <span className="monitor-info-label">Kernel</span>
            <span className="monitor-info-value">{sysInfo.kernel || '--'}</span>
          </div>
          <div className="monitor-info-item">
            <span className="monitor-info-label">Uptime</span>
            <span className="monitor-info-value">{sysInfo.uptime || '--'}</span>
          </div>
          <div className="monitor-info-item">
            <span className="monitor-info-label">CPU Model</span>
            <span className="monitor-info-value">{cpuInfo.model || '--'}</span>
          </div>
          <div className="monitor-info-item">
            <span className="monitor-info-label">CPU Cores / Threads</span>
            <span className="monitor-info-value">{cpuInfo.cores || '--'} / {cpuInfo.threads || '--'}</span>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>Load Average</h2>
        <div className="resource-grid">
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><Activity size={16}/></span><span>1 min</span></div>
            <strong>{load['1min']?.toFixed(2) || '--'}</strong>
            <small>Load average</small>
          </div>
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><Activity size={16}/></span><span>5 min</span></div>
            <strong>{load['5min']?.toFixed(2) || '--'}</strong>
            <small>Load average</small>
          </div>
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><Activity size={16}/></span><span>15 min</span></div>
            <strong>{load['15min']?.toFixed(2) || '--'}</strong>
            <small>Load average</small>
          </div>
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><Cpu size={16}/></span><span>CPUs</span></div>
            <strong>{load.cpus || '--'}</strong>
            <small>Logical cores</small>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>CPU Usage</h2>
        <div className="resource-grid">
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><Cpu size={16}/></span><span>User</span></div>
            <strong>{formatPercent(cpu.user)}</strong>
            <div className="resource-track"><span style={{ width: `${clampPercent(cpu.user)}%` }}></span></div>
            <small>{cpu.user?.toFixed(1) || 0}%</small>
          </div>
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><Cpu size={16}/></span><span>System</span></div>
            <strong>{formatPercent(cpu.system)}</strong>
            <div className="resource-track"><span style={{ width: `${clampPercent(cpu.system)}%` }}></span></div>
            <small>{cpu.system?.toFixed(1) || 0}%</small>
          </div>
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><Cpu size={16}/></span><span>Idle</span></div>
            <strong>{formatPercent(cpu.idle)}</strong>
            <div className="resource-track"><span style={{ width: `${clampPercent(cpu.idle)}%` }}></span></div>
            <small>{cpu.idle?.toFixed(1) || 0}%</small>
          </div>
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><Cpu size={16}/></span><span>I/O Wait</span></div>
            <strong>{formatPercent(cpu.iowait)}</strong>
            <div className="resource-track"><span style={{ width: `${clampPercent(cpu.iowait)}%` }}></span></div>
            <small>{cpu.iowait?.toFixed(1) || 0}%</small>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>Memory Usage</h2>
        <div className="resource-grid">
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><MemoryStick size={16}/></span><span>Used</span></div>
            <strong>{formatBytes(memory.used)}</strong>
            <div className="resource-track"><span style={{ width: `${clampPercent(memory.percent)}%` }}></span></div>
            <small>{memory.percent?.toFixed(1) || 0}% of {formatBytes(memory.total)}</small>
          </div>
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><MemoryStick size={16}/></span><span>Free</span></div>
            <strong>{formatBytes(memory.free)}</strong>
            <small>{formatBytes(memory.free)}</small>
          </div>
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><MemoryStick size={16}/></span><span>Available</span></div>
            <strong>{formatBytes(memory.available)}</strong>
            <small>{formatBytes(memory.available)}</small>
          </div>
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><MemoryStick size={16}/></span><span>Cached</span></div>
            <strong>{formatBytes(memory.cached)}</strong>
            <small>{formatBytes(memory.buffers)} buffers</small>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>Swap Usage</h2>
        <div className="resource-grid">
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><HardDrive size={16}/></span><span>Swap</span></div>
            <strong>{formatPercent(swap.percent)}</strong>
            <div className="resource-track"><span style={{ width: `${clampPercent(swap.percent)}%` }}></span></div>
            <small>{formatBytes(swap.used)} / {formatBytes(swap.total)}</small>
          </div>
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><HardDrive size={16}/></span><span>Free</span></div>
            <strong>{formatBytes(swap.free)}</strong>
            <small>Swap free</small>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>Disk Usage</h2>
        {Object.keys(diskUsage).length === 0 ? <p className="hint">No disk data available</p> : (
          <div className="resource-grid">
            {Object.entries(diskUsage).map(([mount, info]) => (
              <div className="resource-card" key={mount}>
                <div className="resource-head"><span className="resource-icon"><HardDrive size={16}/></span><span>{mount}</span></div>
                <strong>{formatPercent(info.percent)}</strong>
                <div className="resource-track"><span style={{ width: `${clampPercent(info.percent)}%` }}></span></div>
                <small>{formatBytes(info.used)} / {formatBytes(info.total)}</small>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="section">
        <h2>Disk I/O</h2>
        {Object.keys(diskIo).length === 0 ? <p className="hint">No disk I/O data available</p> : (
          <div className="table">
            <div className="row header-row">
              <span>Device</span>
              <span>Reads</span>
              <span>Writes</span>
              <span>Read Bytes</span>
              <span>Write Bytes</span>
            </div>
            {Object.entries(diskIo).map(([device, stats]) => (
              <div className="row" key={device}>
                <span><strong>{device}</strong></span>
                <span>{formatNumber(stats.reads)}</span>
                <span>{formatNumber(stats.writes)}</span>
                <span>{formatBytes(stats.read_bytes)}</span>
                <span>{formatBytes(stats.write_bytes)}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="section">
        <h2>Network I/O</h2>
        {Object.keys(networkIo).length === 0 ? <p className="hint">No network data available</p> : (
          <div className="table">
            <div className="row header-row">
              <span>Interface</span>
              <span>RX Bytes</span>
              <span>RX Packets</span>
              <span>TX Bytes</span>
              <span>TX Packets</span>
            </div>
            {Object.entries(networkIo).map(([iface, stats]) => (
              <div className="row" key={iface}>
                <span><strong>{iface}</strong></span>
                <span>{formatBytes(stats.rx_bytes)}</span>
                <span>{formatNumber(stats.rx_packets)}</span>
                <span>{formatBytes(stats.tx_bytes)}</span>
                <span>{formatNumber(stats.tx_packets)}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="section">
        <h2>Top Processes</h2>
        {processes.length === 0 ? <p className="hint">No process data available</p> : (
          <div className="table">
            <div className="row header-row">
              <span>PID</span>
              <span>Name</span>
              <span>CPU %</span>
              <span>MEM %</span>
            </div>
            {processes.slice(0, 10).map(proc => (
              <div className="row" key={proc.pid}>
                <span>{proc.pid}</span>
                <span title={proc.name}>{proc.name.length > 30 ? proc.name.substring(0, 30) + '...' : proc.name}</span>
                <span className={proc.cpu > 50 ? 'badge bad' : ''}>{proc.cpu?.toFixed(1)}</span>
                <span>{proc.mem?.toFixed(1)}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </>
  );
}

import { RefreshCw } from 'lucide-react';
