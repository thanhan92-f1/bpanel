import { Clock, Plus, Play, Edit, Trash2, ToggleLeft, ToggleRight, RefreshCw, Save, X } from 'lucide-react';

function EmptyState({ icon, message }) {
  return <div className="empty-state">{icon && <icon size={40} />}<p>{message}</p></div>;
}

export default function CronJobs({
  cronJobs,
  loading,
  showCronModal,
  editingCron,
  cronForm,
  cronMinute,
  cronHour,
  cronDayOfMonth,
  cronMonth,
  cronDayOfWeek,
  cronPreview,
  selectedPreset,
  onSetCronForm,
  onSetCronMinute,
  onSetCronHour,
  onSetCronDayOfMonth,
  onSetCronMonth,
  onSetCronDayOfWeek,
  onSetSelectedPreset,
  onOpenCronModal,
  onCloseCronModal,
  onCreateCronJob,
  onUpdateCronJob,
  onDeleteCronJob,
  onToggleCronJob,
  onRunCronJobNow,
  onLoadCronJobs,
  onGenerateSchedulePreview,
  onApplyPreset
}) {
  const presets = [
    { label: 'Every 5 minutes', value: '*/5 * * * *' },
    { label: 'Every 10 minutes', value: '*/10 * * * *' },
    { label: 'Every 15 minutes', value: '*/15 * * * *' },
    { label: 'Every 30 minutes', value: '*/30 * * * *' },
    { label: 'Every hour', value: '0 * * * *' },
    { label: 'Daily at midnight', value: '0 0 * * *' },
    { label: 'Daily at 6 AM', value: '0 6 * * *' },
    { label: 'Weekly on Monday', value: '0 0 * * 1' },
    { label: 'Monthly on 1st', value: '0 0 1 * *' },
  ];

  const minuteOptions = ['*', '*/5', '*/10', '*/15', '*/30', '0', '15', '30', '45'];
  const hourOptions = ['*', '*/2', '*/4', '*/6', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23'];
  const dayOfMonthOptions = ['*', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30', '31'];
  const monthOptions = ['*', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'];
  const dayOfWeekOptions = ['*', '0', '1', '2', '3', '4', '5', '6'];

  return (
    <>
      <section className="section cron-page">
        <div className="section-title">
          <div>
            <h2>Cron Jobs</h2>
            <p className="hint">Schedule and manage automated tasks</p>
          </div>
          <div className="cron-actions-header">
            <button disabled={!!loading} onClick={onLoadCronJobs}>
              <RefreshCw size={14}/> Refresh
            </button>
            <button disabled={!!loading} onClick={() => onOpenCronModal?.()}>
              <Plus size={14}/> Create Job
            </button>
          </div>
        </div>

        {cronJobs.length === 0 ? (
          <EmptyState icon={Clock} message="No cron jobs configured. Create your first job to schedule automated tasks." />
        ) : (
          <div className="table cron-table">
            <div className="row header-row">
              <span>Command</span>
              <span>Schedule</span>
              <span>Next Run</span>
              <span>Enabled</span>
              <span>Last Run</span>
              <span>Actions</span>
            </div>
            {cronJobs.map(cron => (
              <div className="row" key={cron.id}>
                <span className="cron-command"><strong>{cron.description || 'Untitled'}</strong><small>{cron.command}</small></span>
                <span className="cron-schedule">{cron.schedule}</span>
                <span className="cron-next-run">{cron.next_run || '--'}</span>
                <span>
                  <button className="mini" onClick={() => onToggleCronJob?.(cron)} disabled={!!loading}>
                    {cron.enabled ? <ToggleRight size={18} color="var(--color-success)" /> : <ToggleLeft size={18} />}
                  </button>
                </span>
                <span className="cron-last-run">{cron.last_run || 'Never'}</span>
                <span className="row-actions">
                  <button className="mini secondary-light" onClick={() => onRunCronJobNow?.(cron)} disabled={!!loading} title="Run now">
                    <Play size={14}/>
                  </button>
                  <button className="mini secondary-light" onClick={() => onOpenCronModal?.(cron)} disabled={!!loading} title="Edit">
                    <Edit size={14}/>
                  </button>
                  <button className="mini danger" onClick={() => onDeleteCronJob?.(cron)} disabled={!!loading} title="Delete">
                    <Trash2 size={14}/>
                  </button>
                </span>
              </div>
            ))}
          </div>
        )}

        {showCronModal && (
          <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) onCloseCronModal?.(); }}>
            <div className="modal cron-modal">
              <div className="modal-header">
                <h3>{editingCron ? 'Edit Cron Job' : 'Create Cron Job'}</h3>
                <button className="close-btn" onClick={onCloseCronModal}><X size={18}/></button>
              </div>
              <div className="modal-body">
                <div className="form-group">
                  <label>Command</label>
                  <textarea
                    value={cronForm.command}
                    onChange={e => onSetCronForm?.({ ...cronForm, command: e.target.value })}
                    placeholder="wp cron event run --due-now --allow-root"
                    rows={3}
                  />
                </div>

                <div className="form-group">
                  <label>Description</label>
                  <input
                    type="text"
                    value={cronForm.description}
                    onChange={e => onSetCronForm?.({ ...cronForm, description: e.target.value })}
                    placeholder="Run WordPress cron events"
                  />
                </div>

                <div className="form-group">
                  <label>Schedule Preset</label>
                  <select value={selectedPreset} onChange={e => { onApplyPreset?.(e.target.value); onGenerateSchedulePreview?.(); }}>
                    <option value="">Custom schedule...</option>
                    {presets.map(preset => (
                      <option key={preset.value} value={preset.value}>{preset.label}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group schedule-builder">
                  <label>Custom Schedule</label>
                  <div className="schedule-fields">
                    <div className="schedule-field">
                      <span className="field-label">Minute</span>
                      <select value={cronMinute} onChange={e => { onSetCronMinute?.(e.target.value); onSetSelectedPreset?.(''); onGenerateSchedulePreview?.(); }}>
                        {minuteOptions.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                      </select>
                    </div>
                    <div className="schedule-field">
                      <span className="field-label">Hour</span>
                      <select value={cronHour} onChange={e => { onSetCronHour?.(e.target.value); onSetSelectedPreset?.(''); onGenerateSchedulePreview?.(); }}>
                        {hourOptions.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                      </select>
                    </div>
                    <div className="schedule-field">
                      <span className="field-label">Day (Month)</span>
                      <select value={cronDayOfMonth} onChange={e => { onSetCronDayOfMonth?.(e.target.value); onSetSelectedPreset?.(''); onGenerateSchedulePreview?.(); }}>
                        {dayOfMonthOptions.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                      </select>
                    </div>
                    <div className="schedule-field">
                      <span className="field-label">Month</span>
                      <select value={cronMonth} onChange={e => { onSetCronMonth?.(e.target.value); onSetSelectedPreset?.(''); onGenerateSchedulePreview?.(); }}>
                        {monthOptions.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                      </select>
                    </div>
                    <div className="schedule-field">
                      <span className="field-label">Day (Week)</span>
                      <select value={cronDayOfWeek} onChange={e => { onSetCronDayOfWeek?.(e.target.value); onSetSelectedPreset?.(''); onGenerateSchedulePreview?.(); }}>
                        {dayOfWeekOptions.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                      </select>
                    </div>
                  </div>
                </div>

                <div className="form-group cron-preview">
                  <label>Schedule Preview</label>
                  <div className="preview-box">
                    <div className="preview-expression">
                      <code>{cronPreview.expression || `${cronMinute} ${cronHour} ${cronDayOfMonth} ${cronMonth} ${cronDayOfWeek}`}</code>
                    </div>
                    <div className="preview-human">
                      {cronPreview.human_readable || 'Custom schedule'}
                    </div>
                    {cronPreview.next_runs && cronPreview.next_runs.length > 0 && (
                      <div className="preview-next-runs">
                        <strong>Next 5 runs:</strong>
                        <ul>
                          {cronPreview.next_runs.slice(0, 5).map((run, idx) => (
                            <li key={idx}>{run}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button className="secondary-light" onClick={onCloseCronModal}><X size={14}/> Cancel</button>
                <button disabled={!cronForm.command || !!loading} onClick={editingCron ? onUpdateCronJob : onCreateCronJob}>
                  <Save size={14}/> {editingCron ? 'Update' : 'Create'}
                </button>
              </div>
            </div>
          </div>
        )}
      </section>
    </>
  );
}
