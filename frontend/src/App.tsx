import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Sidebar } from './components/layout/Sidebar';
import { TopBar } from './components/layout/TopBar';
import { DashboardPage } from './pages/DashboardPage';
import { WorkflowPage } from './pages/WorkflowPage';
import { AgentsPage } from './pages/AgentsPage';
import { InventoryPage } from './pages/InventoryPage';
import { ReportsPage } from './pages/ReportsPage';
import { SimulatePage } from './pages/SimulatePage';
import { EventsPage } from './pages/EventsPage';
import { healthApi } from './services/api';
import './App.css';

const App: React.FC = () => {
  const [systemOnline, setSystemOnline] = useState(false);

  useEffect(() => {
    const check = async () => {
      const h = await healthApi.check();
      setSystemOnline(h.status === 'ok');
    };
    check();
    const interval = setInterval(check, 30_000);
    return () => clearInterval(interval);
  }, []);

  return (
    <BrowserRouter>
      <div className="layout">
        <Sidebar systemOnline={systemOnline} />
        <div className="main-content">
          <TopBar />
          <main>
            <Routes>
              <Route path="/"          element={<DashboardPage />} />
              <Route path="/workflows" element={<WorkflowPage />} />
              <Route path="/workflow"  element={<WorkflowPage />} />
              <Route path="/agents"    element={<AgentsPage />} />
              <Route path="/inventory" element={<InventoryPage />} />
              <Route path="/reports"   element={<ReportsPage />} />
              <Route path="/simulate"  element={<SimulatePage />} />
              <Route path="/events"    element={<EventsPage />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
};

export default App;
