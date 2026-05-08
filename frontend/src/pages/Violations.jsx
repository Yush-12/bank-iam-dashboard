import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getOrphanAccounts,
  getOverPrivilegedUsers,
  getSoDViolations,
  updateViolationStatus,
} from "../api/client";
import ErrorCard from "../components/ErrorCard";
import LoadingSpinner from "../components/LoadingSpinner";
import OrphanAccountsTable from "../components/violations/OrphanAccountsTable";
import OverPrivilegedTable from "../components/violations/OverPrivilegedTable";
import SodViolationsTable from "../components/violations/SodViolationsTable";

const tabs = ["SoD Violations", "Orphan Accounts", "Over-Privileged"];

export default function Violations() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState(tabs[0]);
  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("");

  const sodQuery = useQuery({
    queryKey: ["violations-sod", severity, status],
    queryFn: () => getSoDViolations({ severity, status, limit: 100, offset: 0 }),
    enabled: activeTab === "SoD Violations",
  });

  const orphanQuery = useQuery({
    queryKey: ["violations-orphans"],
    queryFn: () => getOrphanAccounts({ limit: 100, offset: 0 }),
    enabled: activeTab === "Orphan Accounts",
  });

  const overQuery = useQuery({
    queryKey: ["violations-over"],
    queryFn: () => getOverPrivilegedUsers({ limit: 100, offset: 0 }),
    enabled: activeTab === "Over-Privileged",
  });

  const statusMutation = useMutation({
    mutationFn: ({ violationId, nextStatus }) => updateViolationStatus(violationId, nextStatus),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["violations-sod"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  const activeQuery =
    activeTab === "SoD Violations"
      ? sodQuery
      : activeTab === "Orphan Accounts"
      ? orphanQuery
      : overQuery;

  const renderTable = () => {
    if (activeQuery.isLoading || (activeTab && !activeQuery.data)) return <LoadingSpinner label={`Loading ${activeTab}...`} />;
    if (activeQuery.isError) return <ErrorCard message={activeQuery.error.message} />;

    if (activeTab === "SoD Violations") {
      return (
        <SodViolationsTable
          items={activeQuery.data.items || []}
          onRemediate={(id) => statusMutation.mutate({ violationId: id, nextStatus: "remediated" })}
          updatingId={statusMutation.isPending ? statusMutation.variables?.violationId : null}
        />
      );
    }

    if (activeTab === "Orphan Accounts") {
      return <OrphanAccountsTable items={activeQuery.data.items || []} />;
    }

    return <OverPrivilegedTable items={activeQuery.data.items || []} />;
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-100">Violations</h2>

      <div className="flex flex-wrap gap-2 rounded-xl border border-bankBorder bg-bankSurface p-2 shadow-inner">
        {tabs.map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            className={`rounded-lg px-3 py-2 text-sm font-medium transition-all ${
              activeTab === tab ? "bg-bankPrimary text-white shadow-md shadow-bankPrimary/20" : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === "SoD Violations" && (
        <div className="flex flex-wrap gap-3 rounded-xl border border-bankBorder bg-bankSurface p-3">
          <select
            value={severity}
            onChange={(event) => setSeverity(event.target.value)}
            className="rounded-md border border-bankBorder bg-slate-900 px-3 py-2 text-sm text-slate-100 focus:border-bankPrimary focus:ring-1 focus:ring-bankPrimary"
          >
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
          </select>
          <select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            className="rounded-md border border-bankBorder bg-slate-900 px-3 py-2 text-sm text-slate-100 focus:border-bankPrimary focus:ring-1 focus:ring-bankPrimary"
          >
            <option value="">All Statuses</option>
            <option value="open">Open</option>
            <option value="remediated">Remediated</option>
            <option value="accepted">Accepted</option>
          </select>
        </div>
      )}

      {statusMutation.isError && <ErrorCard message={statusMutation.error.message} />}
      {renderTable()}
    </div>
  );
}
