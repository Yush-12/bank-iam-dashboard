import React, { useState, useEffect } from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import RBAC from "./pages/RBAC";
import Report from "./pages/Report";
import UserDetail from "./pages/UserDetail";
import Users from "./pages/Users";
import Violations from "./pages/Violations";
import Settings from "./pages/Settings";
import { warmupBackend } from "./api/client";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
});

function App() {
  const [isWarmingUp, setIsWarmingUp] = useState(true);

  useEffect(() => {
    warmupBackend().finally(() => setIsWarmingUp(false));
  }, []);

  if (isWarmingUp) {
    return (
      <div className="flex h-screen flex-col items-center justify-center bg-bankBg">
        <div className="mb-6 relative">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-slate-800 border-t-bankPrimary"></div>
          <div className="absolute inset-0 h-12 w-12 animate-ping rounded-full border-4 border-bankPrimary/20"></div>
        </div>
        <h2 className="text-xl font-bold text-slate-100 tracking-tight">Initializing Bank Security Engine</h2>
        <p className="mt-2 text-sm text-slate-500 font-medium text-center max-w-xs">
          Waking up cloud instances... <br/> 
          <span className="text-[10px] uppercase mt-2 block opacity-50">Secure Connection Establishing</span>
        </p>
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="violations" element={<Violations />} />
          <Route path="users" element={<Users />} />
          <Route path="users/:id" element={<UserDetail />} />
          <Route path="rbac" element={<RBAC />} />
          <Route path="report" element={<Report />} />
          <Route path="settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
);
