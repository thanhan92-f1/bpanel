export function formatBytes(value) {
  const amount = Number(value);
  if (!Number.isFinite(amount) || amount < 0) return '--';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = amount;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) { size /= 1024; unit += 1; }
  return `${size >= 10 || unit === 0 ? size.toFixed(0) : size.toFixed(1)} ${units[unit]}`;
}

export function formatPercent(value) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return '--';
  return `${Math.round(amount)}%`;
}

export function clampPercent(value) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return 0;
  return Math.max(0, Math.min(100, amount));
}

export function storageLimitBytes(user) {
  if (!user) return null;
  if (user.storage_limit_bytes === null) return null;
  if (user.storage_limit_bytes !== undefined) return user.storage_limit_bytes;
  return Number(user.storage_limit_mb || 0) * 1024 * 1024;
}

export function formatNumber(value) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return '--';
  return amount.toLocaleString();
}

export function formatNodeUptime(seconds) {
  if (!seconds || seconds < 0) return '-';
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${mins}m`;
  return `${mins}m`;
}
