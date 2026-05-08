import { NavLink, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getRbacHealth } from "../api/client";
import { healthBadge } from "../utils/styles";

const navItems = [
  { to: "/", label: "Dashboard", icon: DashboardIcon },
  { to: "/violations", label: "Violations", icon: AlertIcon },
  { to: "/users", label: "Users", icon: UsersIcon },
  { to: "/rbac", label: "RBAC", icon: ShieldIcon },
  { to: "/report", label: "Report", icon: ReportIcon },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

export default function Layout() {
  const { data: health } = useQuery({
    queryKey: ["rbac-health"],
    queryFn: getRbacHealth,
    staleTime: 60_000,
  });

  const score = health?.score ?? "--";
  const badgeClass = typeof score === "number" ? healthBadge(score) : "bg-slate-200 text-slate-700";

  return (
    <div className="min-h-screen bg-bankBg text-slate-100 md:flex">
      <aside className="border-r border-bankBorder bg-bankSurface md:w-64">
        <div className="px-5 py-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-bankPrimary">Navigation</p>
        </div>
        <nav className="space-y-1 px-3">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${isActive
                  ? "bg-bankPrimary text-white shadow-lg shadow-bankPrimary/20"
                  : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                }`
              }
            >
              <item.icon />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="mx-3 mt-6 rounded-lg border border-bankBorder bg-slate-900/50 p-3">
          <p className="text-xs font-semibold uppercase text-slate-500">Compliance Health</p>
          <div className={`mt-2 inline-flex rounded-full px-3 py-1 text-sm font-semibold ${badgeClass}`}>
            {score}
          </div>
        </div>
      </aside>

      <div className="flex-1">
        <header className="border-b border-bankBorder bg-bankSurface/50 backdrop-blur-md sticky top-0 z-10 px-4 py-4 md:px-8">
          <h1 className="text-xl font-bold text-slate-100">IAM Access Review Dashboard</h1>
          <p className="text-sm text-slate-500 font-medium">Bank Monitoring System</p>
        </header>
        <main className="px-4 py-6 md:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function iconProps() {
  return {
    width: 18,
    height: 18,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round",
    strokeLinejoin: "round",
  };
}

function DashboardIcon() {
  return (
    <svg {...iconProps()}>
      <rect x="3" y="3" width="7" height="7" />
      <rect x="14" y="3" width="7" height="4" />
      <rect x="14" y="10" width="7" height="11" />
      <rect x="3" y="13" width="7" height="8" />
    </svg>
  );
}

function AlertIcon() {
  return (
    <svg {...iconProps()}>
      <path d="m10.29 3.86-8 14A1 1 0 0 0 3.16 19h16.68a1 1 0 0 0 .87-1.5l-8-14a1 1 0 0 0-1.74 0Z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

function UsersIcon() {
  return (
    <svg {...iconProps()}>
      <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="8.5" cy="7" r="4" />
      <path d="M20 8v6" />
      <path d="M23 11h-6" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg {...iconProps()}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}

function ReportIcon() {
  return (
    <svg {...iconProps()}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6" />
      <path d="M16 13H8" />
      <path d="M16 17H8" />
      <path d="M10 9H8" />
    </svg>
  );
}

function SettingsIcon() {
  return (
    <svg {...iconProps()}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}
