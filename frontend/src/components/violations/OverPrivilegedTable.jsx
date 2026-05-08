import { riskBar } from "../../utils/styles";

export default function OverPrivilegedTable({ items }) {
  return (
    <div className="table-shell">
      <table className="table-base">
        <thead>
          <tr>
            <th>Employee</th>
            <th>Dept</th>
            <th>Total Roles</th>
            <th>Unused Admin Roles</th>
            <th>Risk Score</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-bankBorder bg-bankSurface">
          {items.map((item) => (
            <tr key={item.user_id} className="hover:bg-slate-800/50 transition-colors">
              <td className="font-medium text-slate-100">{item.user_name}</td>
              <td>{item.department}</td>
              <td>{item.total_active_roles}</td>
              <td>{item.unused_admin_roles.join(", ") || "-"}</td>
              <td>
                <div className="w-48">
                  <div className="mb-1 flex justify-between text-xs text-slate-500">
                    <span>{item.risk_score}</span>
                    <span>/100</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-slate-200">
                    <div
                      className={`h-2 rounded-full ${riskBar(item.risk_score)}`}
                      style={{ width: `${Math.min(item.risk_score, 100)}%` }}
                    />
                  </div>
                </div>
              </td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr>
              <td colSpan={5} className="text-center text-slate-500">
                No over-privileged users detected.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
