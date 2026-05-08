import { statusPill } from "../../utils/styles";

function daysColor(days) {
  if (days > 90) return "text-red-400 font-semibold";
  if (days > 30) return "text-orange-400 font-semibold";
  return "text-amber-400 font-semibold";
}

export default function OrphanAccountsTable({ items }) {
  return (
    <div className="table-shell">
      <table className="table-base">
        <thead>
          <tr>
            <th>Employee ID</th>
            <th>Name</th>
            <th>Dept</th>
            <th>Status</th>
            <th>Days Since Termination</th>
            <th>Active Systems</th>
            <th>Risk</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-bankBorder bg-bankSurface">
          {items.map((item) => (
            <tr key={item.user_id} className="hover:bg-slate-800/50 transition-colors">
              <td>{item.employee_id}</td>
              <td className="font-medium text-slate-100">{item.user_name}</td>
              <td>{item.department}</td>
              <td>
                <span className={`rounded-full px-2 py-1 text-xs font-semibold ${statusPill(item.user_status)}`}>
                  {item.user_status}
                </span>
              </td>
              <td className={daysColor(item.days_since_termination)}>{item.days_since_termination}</td>
              <td>{item.active_systems.join(", ")}</td>
              <td className="capitalize">{item.risk_level}</td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr>
              <td colSpan={7} className="text-center text-slate-500">
                No orphan accounts detected.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
