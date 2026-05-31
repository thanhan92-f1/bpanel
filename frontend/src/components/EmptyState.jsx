export default function EmptyState({ icon: Icon, message }) {
  return (
    <div className="empty-state">
      {Icon && <Icon size={40}/>}
      <p>{message}</p>
    </div>
  );
}
