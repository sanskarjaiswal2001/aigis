import { Route, Routes } from "react-router-dom";
import { TopBar } from "./components/layout/TopBar";
import { Sidebar } from "./components/layout/Sidebar";
import { Dashboard } from "./components/dashboard/Dashboard";
import { RunList } from "./components/run/RunList";
import { RunDetail } from "./components/run/RunDetail";
import { AuditLog } from "./components/audit/AuditLog";
import { Settings } from "./components/settings/Settings";

export default function App() {
  return (
    <div className="flex flex-col h-screen bg-black">
      <TopBar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto bg-black">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/runs" element={<RunList />} />
            <Route path="/runs/:runId" element={<RunDetail />} />
            <Route path="/audit" element={<AuditLog />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
