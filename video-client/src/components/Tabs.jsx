/* eslint-disable react/prop-types */

const Tabs = ({ tabs, activeTab, onTabChange }) => {
  return (
    <div className="w-full border-b border-gray-200 bg-white">
      <div className="max-w-2xl mx-auto px-4">
        <nav className="flex justify-center -mb-px space-x-8" aria-label="Tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`
                relative py-4 px-1 transition-colors duration-200
                ${
                  activeTab === tab.id
                    ? "border-b-2 border-blue-500 text-blue-600"
                    : "border-b-2 border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
                }
              `}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>
    </div>
  );
};

export default Tabs;
