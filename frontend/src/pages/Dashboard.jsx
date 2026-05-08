import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getDashboardSummary, getRoles, runAnalysis } from "../api/client";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorCard from "../components/ErrorCard";
import { healthColor, severityPill } from "../utils/styles";

const systemCriticalityMap = {
  "Core Banking System (CBS)": "critical",
  "SWIFT Payment Gateway": "critical",
  FINACLE: "critical",
  "Treasury Management System": "high",
  "Active Directory": "high",
  "HR Portal": "medium",
};

export default function Dashboard() {
  const queryClient = useQueryClient();
  const dashboardQuery = useQuery({ queryKey: ["dashboard"], queryFn: getDashboardSummary });
  const rolesQuery = useQuery({
    queryKey: ["roles-all"],
    queryFn: () => getRoles({ limit: 200, offset: 0 }),
  });

  const analysisMutation = useMutation({
    mutationFn: runAnalysis,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
        queryClient.invalidateQueries({ queryKey: ["rbac-health"] }),
        queryClient.invalidateQueries({ queryKey: ["violations-sod"] }),
        queryClient.invalidateQueries({ queryKey: ["violations-orphans"] }),
        queryClient.invalidateQueries({ queryKey: ["violations-over"] }),
      ]);
    },
  });

  const systems = useMemo(() => {
    const names = [...new Set((rolesQuery.data?.items || []).map((item) => item.system).filter(Boolean))];
    return names.map((name) => ({
      name,
      criticality: systemCriticalityMap[name] || "medium",
    }));
  }, [rolesQuery.data?.items]);

  if (dashboardQuery.isLoading || rolesQuery.isLoading || !dashboardQuery.data) return <LoadingSpinner label="Loading dashboard..." />;
  if (dashboardQuery.isError) return <ErrorCard message={dashboardQuery.error.message} />;
  if (rolesQuery.isError) return <ErrorCard message={rolesQuery.error.message} />;

  const dashboard = dashboardQuery.data;
  const healthScore = dashboard.rbac_health_score ?? 0;
  const healthClass = healthColor(healthScore);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">Executive Overview</h2>
          <p className="text-sm text-slate-400">Last analysis: {new Date(dashboard.last_analysis).toLocaleString()}</p>
        </div>
        <button
          type="button"
          onClick={() => analysisMutation.mutate()}
          disabled={analysisMutation.isPending}
          className="inline-flex items-center gap-2 rounded-lg bg-bankPrimary px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-bankPrimary/20 transition-all hover:bg-bankAccent disabled:opacity-60"
        >
          {analysisMutation.isPending && <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />}
          Run Analysis
        </button>
      </div>

      {analysisMutation.isError && <ErrorCard message={analysisMutation.error.message} />}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SummaryCard iconType="users" label="Total Users" value={dashboard.total_users} change={`Active ${dashboard.active_users}`} />
        <SummaryCard iconType="alert" label="SoD Violations" value={dashboard.sod_violations.total} change={`Critical ${dashboard.sod_violations.critical}`} />
        <SummaryCard iconType="document" label="Orphan Accounts" value={dashboard.orphan_accounts.total} change={`High+Critical ${dashboard.orphan_accounts.high + dashboard.orphan_accounts.critical}`} />
        <SummaryCard
          iconType="shield"
          label="Health Score"
          value={healthScore}
          valueClass={healthClass}
          change={`Role Explosion ${dashboard.role_explosion.score}`}
        />
      </section>

      <section className="card p-5">
        <h3 className="text-base font-semibold text-slate-100">Compliance Flags</h3>
        <div className="mt-4 space-y-3">
          {dashboard.compliance_flags.length === 0 && <p className="text-sm text-slate-400">No active compliance flags.</p>}
          {dashboard.compliance_flags.map((flag, index) => (
            <div
              key={`${flag.type}-${index}`}
              className={`rounded-lg border border-bankBorder bg-slate-900/30 p-3 ${
                flag.severity === "critical" ? "border-l-4 border-l-red-500" : ""
              }`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded-full px-2 py-1 text-xs font-semibold ${severityPill(flag.severity)}`}>
                  {flag.severity}
                </span>
                <p className="text-sm font-medium text-slate-100">{flag.message}</p>
              </div>
              <p className="mt-2 text-xs text-slate-500">{flag.regulatory_ref}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="card p-5">
        <h3 className="text-base font-semibold text-slate-100">Systems Monitored</h3>
        <p className="mt-1 text-sm text-slate-400">{dashboard.systems_monitored} systems currently under review.</p>
        <div className="mt-4 flex flex-wrap gap-3">
          {systems.map((system) => (
            <div key={system.name} className="rounded-lg border border-bankBorder bg-slate-900/50 px-3 py-2">
              <p className="text-sm font-medium text-slate-100">{system.name}</p>
              <span className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${severityPill(system.criticality)}`}>
                {system.criticality}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function SummaryCard({ iconType, label, value, change, valueClass = "text-bankPrimary" }) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</p>
        <div className="rounded-lg bg-slate-900 p-2 border border-bankBorder">
          <SummaryIcon type={iconType} />
        </div>
      </div>
      <p className={`mt-3 text-3xl font-bold tracking-tight ${valueClass}`}>{value}</p>
      <div className="mt-3 flex items-center gap-2">
        <span className="h-1.5 w-1.5 rounded-full bg-bankPrimary animate-pulse" />
        <p className="text-xs font-medium text-slate-400">{change}</p>
      </div>
    </div>
  );
}

function SummaryIcon({ type }) {
  const props = {
    width: 18,
    height: 18,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "#60a5fa",
    strokeWidth: 2,
    strokeLinecap: "round",
    strokeLinejoin: "round",
  };

  if (type === "users") {
    return (
      <svg {...props}>
        <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="8.5" cy="7" r="4" />
        <path d="M20 8v6" />
        <path d="M23 11h-6" />
      </svg>
    );
  }

  if (type === "alert") {
    return (
      <svg {...props}>
        <path d="m10.29 3.86-8 14A1 1 0 0 0 3.16 19h16.68a1 1 0 0 0 .87-1.5l-8-14a1 1 0 0 0-1.74 0Z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
    );
  }

  if (type === "shield") {
    return (
      <svg {...props}>
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
      </svg>
    );
  }

  return (
    <svg {...props}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6" />
      <path d="M16 13H8" />
      <path d="M16 17H8" />
    </svg>
  );
}
