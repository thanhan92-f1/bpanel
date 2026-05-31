import { Mail, Plus, Trash2, RefreshCw } from 'lucide-react';

function EmptyState({ icon, message }) {
  return <div className="empty-state">{icon && <icon size={40} />}<p>{message}</p></div>;
}

export default function MailServer({
  mailDomains,
  mailboxes,
  emails,
  mailSettings,
  selectedDomain,
  selectedMailbox,
  mailFolder,
  loading,
  newMailDomain,
  newMailbox,
  onSetNewMailDomain,
  onSetNewMailbox,
  onSetSelectedDomain,
  onSetMailFolder,
  onAddMailDomain,
  onDeleteMailDomain,
  onAddMailbox,
  onDeleteMailbox,
  onLoadMailDomains,
  onLoadMailboxes,
  onLoadEmails
}) {
  return (
    <>
      <section className="section">
        <div className="section-title">
          <div>
            <h2>Mail Server</h2>
            <p className="hint">Status: {mailSettings?.status?.running ? <span className="badge ok">Running</span> : <span className="badge">Stopped</span>}</p>
          </div>
          <button disabled={!!loading} onClick={() => {
            onLoadMailDomains?.();
          }}>
            <RefreshCw size={15}/> Refresh
          </button>
        </div>
      </section>

      <section className="section">
        <h3>Mail Domains</h3>
        <div className="form-row">
          <input
            value={newMailDomain.domain}
            onChange={e => onSetNewMailDomain?.({ ...newMailDomain, domain: e.target.value })}
            placeholder="domain.com"
          />
          <button disabled={!!loading || !newMailDomain.domain} onClick={onAddMailDomain}>
            <Plus size={14}/> Add Domain
          </button>
        </div>

        {mailDomains.length === 0 ? (
          <EmptyState icon={Mail} message="No mail domains configured." />
        ) : (
          <div className="table">
            <div className="row header-row">
              <span>Domain</span>
              <span>Quota (GB)</span>
              <span>Actions</span>
            </div>
            {mailDomains.map(domain => (
              <div className="row" key={domain.domain}>
                <span><strong>{domain.domain}</strong></span>
                <span>{domain.quota_gb || 10} GB</span>
                <div className="row-actions">
                  <button className="mini secondary-light" onClick={() => onSetSelectedDomain?.(domain.domain)}>
                    Select
                  </button>
                  <button className="mini danger" disabled={!!loading} onClick={() => onDeleteMailDomain?.(domain.domain)}>
                    <Trash2 size={13}/>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {selectedDomain && (
        <section className="section">
          <h3>Mailboxes for {selectedDomain}</h3>
          <div className="form-row">
            <input
              value={newMailbox.username}
              onChange={e => onSetNewMailbox?.({ ...newMailbox, username: e.target.value })}
              placeholder="username"
              style={{ textTransform: 'lowercase' }}
            />
            <span>@{selectedDomain}</span>
            <input
              value={newMailbox.password}
              onChange={e => onSetNewMailbox?.({ ...newMailbox, password: e.target.value })}
              placeholder="password"
              type="password"
            />
            <button disabled={!!loading || !newMailbox.username || !newMailbox.password} onClick={onAddMailbox}>
              <Plus size={14}/> Create Mailbox
            </button>
          </div>

          {mailboxes.length === 0 ? (
            <p className="hint">No mailboxes for this domain.</p>
          ) : (
            <div className="table">
              <div className="row header-row">
                <span>Username</span>
                <span>Quota</span>
                <span>Actions</span>
              </div>
              {mailboxes.map(box => (
                <div className="row" key={box.username}>
                  <span><strong>{box.username}@{selectedDomain}</strong></span>
                  <span>{box.quota_gb || 1} GB</span>
                  <div className="row-actions">
                    <button className="mini danger" disabled={!!loading} onClick={() => onDeleteMailbox?.(box.username)}>
                      <Trash2 size={13}/>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </>
  );
}
