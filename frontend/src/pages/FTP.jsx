import { Server, Plus, Trash2, KeyRound, RefreshCw, AlertCircle } from 'lucide-react';

function EmptyState({ icon: Icon = AlertCircle, message = 'No data yet' }) {
  return <div className="empty-state"><Icon size={40} /><p>{message}</p></div>;
}

export default function FTP({
  ftpUsers,
  ftpStatus,
  websites,
  loading,
  newFtpUser,
  onNewFtpUserChange,
  onCreateFtpUser,
  onDeleteFtpUser,
  onChangeFtpPassword,
  onConfigureFtp,
  onLoadFtpStatus,
  onLoadFtpUsers
}) {
  return (
    <>
      <section className="section">
        <div className="section-title">
          <div>
            <h2>FTP Manager</h2>
            <p className="hint">FTP status: {ftpStatus?.running ? <span className="badge ok">Running</span> : <span className="badge">Stopped</span>}</p>
          </div>
          <button disabled={!!loading} onClick={() => { onLoadFtpStatus?.(); onLoadFtpUsers?.(); }}>
            <RefreshCw size={15}/> Refresh
          </button>
        </div>
      </section>

      <section className="section">
        <h2>Create FTP User</h2>
        <div className="form-row">
          <input
            value={newFtpUser.username}
            onChange={e => onNewFtpUserChange({ ...newFtpUser, username: e.target.value })}
            placeholder="Username"
          />
          <select
            value={newFtpUser.website_id}
            onChange={e => onNewFtpUserChange({ ...newFtpUser, website_id: e.target.value })}
          >
            <option value="">Select website</option>
            {websites.map(site => <option key={site.id} value={site.id}>{site.domain}</option>)}
          </select>
          <button
            disabled={!!loading || !newFtpUser.username || !newFtpUser.website_id}
            onClick={onCreateFtpUser}
          >
            <Plus size={15}/> Create
          </button>
        </div>
      </section>

      <section className="section">
        <h2>FTP Users</h2>
        {ftpUsers.length === 0 ? <EmptyState icon={Server} message="No FTP users found." /> : (
          <div className="table">
            <div className="row header-row">
              <span>Username</span>
              <span>Website</span>
              <span>Home</span>
              <span>Actions</span>
            </div>
            {ftpUsers.map(user => (
              <div className="row" key={user.username}>
                <span><strong>{user.username}</strong></span>
                <span>{websites.find(s => s.id === user.website_id)?.domain || `Website #${user.website_id}`}</span>
                <span><small>{user.home || '-'}</small></span>
                <div className="row-actions">
                  <button className="mini secondary-light" disabled={!!loading} onClick={() => onChangeFtpPassword?.(user.username)}>
                    <KeyRound size={13}/> Password
                  </button>
                  <button className="mini danger" disabled={!!loading} onClick={() => onDeleteFtpUser?.(user.username)}>
                    <Trash2 size={13}/>
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
