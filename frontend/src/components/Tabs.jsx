export default function Tabs({ tabs, activeTab, onChange }) {
  return (
    <div className="tabs">
      {tabs.map(tab => (
        <button
          key={tab.key}
          className={activeTab === tab.key ? 'active' : ''}
          onClick={() => onChange(tab.key)}
        >
          {tab.icon && <tab.icon size={16}/>}
          {tab.label}
        </button>
      ))}
    </div>
  );
}
