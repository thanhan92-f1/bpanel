import { Globe, AlertCircle } from 'lucide-react';
import { formatBytes, formatPercent, clampPercent, storageLimitBytes } from '../utils/formatters';

function ResourceCard({ icon: Icon, label, value, detail, percent }) {
  const safePercent = percent == null ? null : clampPercent(percent);
  return <article className="resource-card">
    <div className="resource-head"><span className="resource-icon"><Icon size={16}/></span><span>{label}</span></div>
    <strong>{value}</strong>
    {safePercent !== null && <div className="resource-track"><span style={{ width: `${safePercent}%` }}></span></div>}
    <small>{detail}</small>
  </article>;
}

function EmptyState({ icon: Icon = AlertCircle, message = 'No data yet' }) {
  return <div className="empty-state"><Icon size={40} /><p>{message}</p></div>;
}

export default function Dashboard({ resourceUsage, websites, databases, currentUser, isAdmin }) {
  const cpu = resourceUsage?.cpu || {};
  const memory = resourceUsage?.memory || {};
  const disk = resourceUsage?.disk || {};
  const network = resourceUsage?.network || {};
  const networkTotal = (Number(network.rx_per_sec) || 0) + (Number(network.tx_per_sec) || 0);

  function websiteUrl(site) {
    const value = (site?.domain || '').trim();
    if (/^https?:\/\//i.test(value)) return value;
    return `${site?.ssl_enabled ? 'https' : 'http'}://${value}`;
  }

  function storageLimitBytes(user) {
    if (!user) return null;
    if (user.storage_limit_bytes === null) return null;
    if (user.storage_limit_bytes !== undefined) return user.storage_limit_bytes;
    return Number(user.storage_limit_mb || 0) * 1024 * 1024;
  }

  function formatBytesLocal(value) {
    const amount = Number(value);
    if (!Number.isFinite(amount) || amount < 0) return '--';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let size = amount;
    let unit = 0;
    while (size >= 1024 && unit < units.length - 1) { size /= 1024; unit += 1; }
    return `${size >= 10 || unit === 0 ? size.toFixed(0) : size.toFixed(1)} ${units[unit]}`;
  }

  function formatPercentLocal(value) {
    const amount = Number(value);
    if (!Number.isFinite(amount)) return '--';
    return `${Math.round(amount)}%`;
  }

  return (
    <>
      <section className="resource-grid">
        <ResourceCard icon={Cpu} label="CPU" value={formatPercentLocal(cpu.percent)} percent={cpu.percent} detail={cpu.load?.length ? `Load ${cpu.load.join(' / ')}` : `${cpu.cores || '--'} cores`} />
        <ResourceCard icon={MemoryStick} label="RAM" value={formatPercentLocal(memory.percent)} percent={memory.percent} detail={`${formatBytesLocal(memory.used)} / ${formatBytesLocal(memory.total)}`} />
        <ResourceCard icon={HardDrive} label="Disk" value={formatPercentLocal(disk.percent)} percent={disk.percent} detail={`${formatBytesLocal(disk.used)} / ${formatBytesLocal(disk.total)}`} />
        <ResourceCard icon={Network} label="Network" value={`${formatBytesLocal(networkTotal)}/s`} detail={`Down ${formatBytesLocal(network.rx_per_sec)}/s / Up ${formatBytesLocal(network.tx_per_sec)}/s`} />
      </section>
      <section className="stats-grid">
        <div className="stat-card"><strong>{websites.length}</strong><span>Websites</span></div>
        <div className="stat-card"><strong>{databases.length}</strong><span>Databases</span></div>
        <div className="stat-card"><strong>{websites.filter(s => s.ssl_enabled).length}</strong><span>SSL active</span></div>
        {currentUser && !isAdmin && <div className="stat-card"><strong>{formatBytesLocal(currentUser.storage_used_bytes)}</strong><span>Storage / {formatBytesLocal(storageLimitBytes(currentUser))}</span></div>}
      </section>
      {websites.length > 0 && <section className="section">
        <h2>Quick overview</h2>
        <div className="site-grid">
          {websites.slice(0, 4).map(site => <article className="site-card" key={site.id}>
            <div className="site-head">
              <div><a className="site-link" href={websiteUrl(site)} target="_blank" rel="noopener noreferrer">{site.domain}</a></div>
            </div>
            <div className="site-meta">
              <span className={`badge site-ssl-badge ${site.ssl_enabled ? 'ok' : ''}`}>{site.ssl_enabled ? 'SSL' : 'No SSL'}</span>
              <span>PHP <strong>{site.php_version}</strong></span>
              <span>Status <strong>{site.status}</strong></span>
            </div>
          </article>)}
        </div>
        {websites.length > 4 && <p className="hint" style={{marginTop:8}}>Showing 4 of {websites.length} websites. Go to Websites for full list.</p>}
      </section>}
      {websites.length === 0 && <section className="section">
        <EmptyState icon={Globe} message="No websites yet. Create your first WordPress site from the Websites menu." />
      </section>}
    </>
  );
}

// Import icons for ResourceCard
import { Cpu, MemoryStick, HardDrive, Network } from 'lucide-react';
