import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Sidebar } from './components/layout/Sidebar';
import { TopBar } from './components/layout/TopBar';
import { DashboardPage } from './pages/DashboardPage';
import { OrdersPage } from './pages/OrdersPage';
import { ShipmentsPage } from './pages/ShipmentsPage';
import { ProcurementPage } from './pages/ProcurementPage';
import { InventoryPage } from './pages/InventoryPage';
import { ControlTowerPage } from './pages/ControlTowerPage';
import { WorkflowPage } from './pages/WorkflowPage';
import { AgentsPage } from './pages/AgentsPage';
import { ReportsPage } from './pages/ReportsPage';
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
    const interval = setInterval(check, 10_000);
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
              <Route path="/"              element={<DashboardPage />} />
              <Route path="/orders"        element={<OrdersPage />} />
              <Route path="/shipments"     element={<ShipmentsPage />} />
              <Route path="/procurement"   element={<ProcurementPage />} />
              <Route path="/inventory"     element={<InventoryPage />} />
              <Route path="/control-tower" element={<ControlTowerPage />} />
              <Route path="/events"        element={<Navigate to="/control-tower" replace />} />
              <Route path="/simulate"      element={<Navigate to="/control-tower" replace />} />
              <Route path="/workflows"     element={<WorkflowPage />} />
              <Route path="/workflow"      element={<WorkflowPage />} />
              <Route path="/agents"        element={<AgentsPage />} />
              <Route path="/reports"       element={<ReportsPage />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
};

export default App;
