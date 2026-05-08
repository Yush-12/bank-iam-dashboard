import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { getUserDetail } from "../api/client";
import ErrorCard from "../components/ErrorCard";
import LoadingSpinner from "../components/LoadingSpinner";
import { formatDateTime, titleCase } from "../utils/format";
import { statusPill } from "../utils/styles";

export default function UserDetail() {
  const { id } = useParams();

  const detailQuery = useQuery({
    queryKey: ["user-detail", id],
    queryFn: () => getUserDetail(id),
    enabled: Boolean(id),
  });

  if (detailQuery.isLoading || !detailQuery.data) return <LoadingSpinner label="Loading user details..." />;
  if (detailQuery.isError) return <ErrorCard message={detailQuery.error.message} />;

  const { user, roles = [], access_logs: accessLogs = [], risk_summary: riskSummary = {}, violations = [] } = detailQuery.data;

  return (
    <div className="space-y-4">
      <Link to="/users" className="inline-flex items-center gap-1 text-sm font-medium text-bankPrimary hover:text-bankAccent transition-colors">
        <span className="text-lg">←</span> Back to users
      </Link>

      <section className="card p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold text-slate-100">{user.name}</h2>
            <p className="text-sm text-slate-400 font-mono tracking-tight">{user.employee_id}</p>
          </div>
          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusPill(user.status)}`}>
            {titleCase(user.status)}
          </span>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <InfoItem label="Email" value={user.email} />
          <InfoItem label="Department" value={user.department} />
          <InfoItem label="Job Title" value={user.job_title} />
          <InfoItem label="Employment End Date" value={formatDateTime(user.employment_end_date)} />
          <InfoItem label="Last Login" value={formatDateTime(user.last_login)} />
          <InfoItem label="Created At" value={formatDateTime(user.created_at)} />
        </div>
      </section>

      <section className="card p-5">
        <h3 className="mb-3 text-base font-semibold text-slate-100">Roles</h3>
        <div className="table-shell">
          <table className="table-base">
            <thead>
              <tr>
                <th>Role</th>
                <th>System</th>
                <th>Risk Level</th>
                <th>Assigned Date</th>
                <th>Last Reviewed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-bankBorder bg-bankSurface">
              {roles.map((role, index) => (
                <tr key={`${role.role_name}-${index}`}>
                  <td>{role.role_name}</td>
                  <td>{role.system}</td>
                  <td className="capitalize">{role.risk_level}</td>
                  <td>{formatDateTime(role.assigned_date)}</td>
                  <td>{formatDateTime(role.last_reviewed)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card p-5">
        <h3 className="mb-3 text-base font-semibold text-slate-100">Access Logs</h3>
        <div className="table-shell">
          <table className="table-base">
            <thead>
              <tr>
                <th>System</th>
                <th>Last Accessed</th>
                <th>90d Usage Count</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-bankBorder bg-bankSurface">
              {accessLogs.map((log, index) => (
                <tr key={`${log.system}-${index}`}>
                  <td>{log.system}</td>
                  <td>{formatDateTime(log.last_accessed)}</td>
                  <td>{log.access_count_90d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card p-5">
        <h3 className="mb-3 text-base font-semibold text-slate-100">Risk Summary</h3>
        <div className="grid gap-3 md:grid-cols-3">
          <RiskFlag label="Has SoD Violation" value={riskSummary.has_sod_violation} />
          <RiskFlag label="Is Orphan Account" value={riskSummary.is_orphan} />
          <RiskFlag label="Is Over-Privileged" value={riskSummary.is_overprivileged} />
        </div>
        <p className="mt-3 text-sm text-slate-400">Total violation records: {violations.length}</p>
      </section>
    </div>
  );
}

function InfoItem({ label, value }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
      <p className="text-sm">{value || "N/A"}</p>
    </div>
  );
}

function RiskFlag({ label, value }) {
  return (
    <div className={`rounded-lg border p-3 transition-colors ${value ? "border-red-500/20 bg-red-500/5" : "border-green-500/20 bg-green-500/5"}`}>
      <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
      <p className={`text-sm font-semibold ${value ? "text-red-400" : "text-green-400"}`}>
        {value ? "Yes" : "No"}
      </p>
    </div>
  );
}
