import { Code, RefreshCw } from 'lucide-react';

export default function PHPVersions({
  phpVersions,
  phpAvailableVersions,
  loading,
  phpConfig,
  onPhpVersionChange,
  onUpdatePhpConfig,
  onLoadPhpVersions,
  onInstallPhpVersion
}) {
  return (
    <>
      <section className="section">
        <div className="section-title">
          <div>
            <h2>PHP Management</h2>
            <p className="hint">Manage PHP versions, extensions, configuration, and FPM pools.</p>
          </div>
          <button disabled={!!loading} onClick={onLoadPhpVersions}>
            <RefreshCw size={15}/> Refresh
          </button>
        </div>
      </section>

      <section className="section">
        <h2>PHP Configuration</h2>
        <div className="user-create-card">
          <label>
            <span>PHP version</span>
            <select
              value={phpConfig.php_version}
              onChange={e => {
                const v = e.target.value;
                onPhpVersionChange?.(v);
              }}
            >
              {phpVersions.map(v => <option key={v} value={v}>PHP {v}</option>)}
            </select>
          </label>
          <label>
            <span>display_errors</span>
            <select
              value={phpConfig.display_errors}
              onChange={e => onUpdatePhpConfig({ ...phpConfig, display_errors: e.target.value })}
            >
              <option value="Off">Off (production)</option>
              <option value="On">On (debug)</option>
            </select>
          </label>
          <label>
            <span>max_execution_time</span>
            <input
              type="number"
              value={phpConfig.max_execution_time}
              onChange={e => onUpdatePhpConfig({ ...phpConfig, max_execution_time: e.target.value })}
            />
          </label>
          <label>
            <span>max_input_time</span>
            <input
              type="number"
              value={phpConfig.max_input_time}
              onChange={e => onUpdatePhpConfig({ ...phpConfig, max_input_time: e.target.value })}
            />
          </label>
          <label>
            <span>max_input_vars</span>
            <input
              type="number"
              value={phpConfig.max_input_vars}
              onChange={e => onUpdatePhpConfig({ ...phpConfig, max_input_vars: e.target.value })}
            />
          </label>
          <label>
            <span>memory_limit</span>
            <input
              value={phpConfig.memory_limit}
              onChange={e => onUpdatePhpConfig({ ...phpConfig, memory_limit: e.target.value })}
              placeholder="512M"
            />
          </label>
          <label>
            <span>post_max_size</span>
            <input
              value={phpConfig.post_max_size}
              onChange={e => onUpdatePhpConfig({ ...phpConfig, post_max_size: e.target.value })}
              placeholder="1024M"
            />
          </label>
          <label>
            <span>upload_max_filesize</span>
            <input
              value={phpConfig.upload_max_filesize}
              onChange={e => onUpdatePhpConfig({ ...phpConfig, upload_max_filesize: e.target.value })}
              placeholder="1024M"
            />
          </label>
          <button disabled={!!loading} onClick={onUpdatePhpConfig}>Save PHP config</button>
        </div>
        <p className="hint">Note: <code>post_max_size</code> should be greater than or equal to <code>upload_max_filesize</code>.</p>
      </section>
    </>
  );
}
