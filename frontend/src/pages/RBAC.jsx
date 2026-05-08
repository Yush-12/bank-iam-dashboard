import { Fragment, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getConsolidationSuggestions, getRbacHealth } from "../api/client";
import ErrorCard from "../components/ErrorCard";
import LoadingSpinner from "../components/LoadingSpinner";
import { healthColor, riskBar } from "../utils/styles";

export default function RBAC() {
  const [expandedKey, setExpandedKey] = useState(null);
  const healthQuery = useQuery({ queryKey: ["rbac-health"], queryFn: getRbacHealth });
  const consolidationQuery = useQuery({
    queryKey: ["rbac-consolidation"],
    queryFn: () => getConsolidationSuggestions({ limit: 200, offset: 0 }),
  });

  const health = healthQuery.data || {};
  const deductions = health.breakdown?.deductions || {};
  const rows = consolidationQuery.data?.items || [];
  const scoreClass = healthColor(health.score ?? 0);

  const deductionRows = useMemo(
    () => [
      ["Critical SoD", deductions.critical_sod || 0],
      ["High SoD", deductions.high_sod || 0],
      ["Orphan Accounts", deductions.orphan_accounts || 0],
      ["Role Explosion", deductions.role_explosion || 0],
      ["Over-Privileged", deductions.over_privileged || 0],
    ],
    [deductions]
  );

  if (healthQuery.isPending || consolidationQuery.isPending || healthQuery.isLoading || consolidationQuery.isLoading || !healthQuery.data || !consolidationQuery.data) {
    return <LoadingSpinner label="Loading RBAC analytics..." />;
  }

  if (healthQuery.isError) return <ErrorCard message={healthQuery.error.message} />;
  if (consolidationQuery.isError) return <ErrorCard message={consolidationQuery.error.message} />;


  return (
    <div className="space-y-5">
      <h2 className="text-lg font-semibold text-slate-100">RBAC Health & Optimisation</h2>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="card p-5">
          <h3 className="text-base font-semibold text-slate-100">Health Score</h3>
          <div className="mt-4 flex items-center gap-6">
            <div
              className={`grid h-28 w-28 place-items-center rounded-full border-8 border-slate-800 bg-slate-900 text-2xl font-bold ${scoreClass}`}
            >
              {health.score}
            </div>
            <div>
              <p className="text-sm text-slate-500">Grade</p>
              <p className={`text-3xl font-bold ${scoreClass}`}>{health.grade}</p>
            </div>
          </div>
        </div>

        <div className="card p-5">
          <h3 className="text-base font-semibold text-slate-100">Health Breakdown</h3>
          <div className="mt-3 space-y-2">
            {deductionRows.map(([label, value]) => (
              <div key={label} className="flex items-center justify-between rounded-md bg-slate-900/50 px-3 py-2 text-sm border border-bankBorder">
                <span className="text-slate-400">{label}</span>
                <span className="font-semibold text-red-400">-{value}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="card p-5">
        <h3 className="text-base font-semibold text-slate-100">Consolidation Suggestions</h3>
        <div className="mt-3 table-shell">
          <table className="table-base">
            <thead>
              <tr>
                <th>Role A</th>
                <th>Role B</th>
                <th>Similarity %</th>
                <th>Shared Permissions</th>
                <th>Users Affected</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-bankBorder bg-bankSurface">
              {rows.map((item) => {
                const key = `${item.role_a_id}-${item.role_b_id}`;
                const expanded = expandedKey === key;
                const percentage = Math.round((item.similarity_score || 0) * 100);
                const barClass = riskBar(percentage);
                return (
                  <Fragment key={key}>
                    <tr className="cursor-pointer hover:bg-slate-800/50 transition-colors" onClick={() => setExpandedKey(expanded ? null : key)}>
                      <td>{item.role_a_name}</td>
                      <td>{item.role_b_name}</td>
                      <td>
                        <div className="w-36">
                          <div className="mb-1 text-xs font-medium text-slate-400">{percentage}%</div>
                          <div className="h-2 rounded-full bg-slate-800">
                            <div className={`h-2 rounded-full ${barClass} shadow-sm shadow-black/20`} style={{ width: `${percentage}%` }} />
                          </div>
                        </div>
                      </td>
                      <td>{item.shared_permissions?.length || 0}</td>
                      <td>{item.estimated_impact}</td>
                      <td>{item.consolidation_recommendation}</td>
                    </tr>
                    {expanded && (
                      <tr>
                        <td colSpan={6} className="bg-slate-900/50 p-4 text-xs text-slate-400 border-t border-bankBorder">
                          <div className="grid gap-2">
                            <p><strong className="text-slate-300">Shared:</strong> {item.shared_permissions?.join(", ") || "-"}</p>
                            <p><strong className="text-slate-300">Unique to {item.role_a_name}:</strong> {item.unique_to_a?.join(", ") || "-"}</p>
                            <p><strong className="text-slate-300">Unique to {item.role_b_name}:</strong> {item.unique_to_b?.join(", ") || "-"}</p>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center text-slate-500">
                    No consolidation suggestions available.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
