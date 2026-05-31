export default function Table({ headers, children, emptyMessage = 'No data' }) {
  return (
    <div className="table">
      <div className="row header-row">
        {headers.map((h, i) => <span key={i}>{h}</span>)}
      </div>
      {children}
      {!children && <div className="empty-state"><p>{emptyMessage}</p></div>}
    </div>
  );
}
