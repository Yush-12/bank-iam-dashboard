import { Fragment, useState } from "react";
import { severityPill } from "../../utils/styles";

export default function SodViolationsTable({ items, onRemediate, updatingId }) {
  const [expandedId, setExpandedId] = useState(null);

  return (
    <div className="table-shell">
      <table className="table-base">
        <thead>
          <tr>
            <th>Employee</th>
            <th>Department</th>
            <th>Conflicting Roles</th>
            <th>Severity</th>
            <th>Regulatory Ref</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-bankBorder bg-bankSurface">
          {items.map((item) => {
            const expanded = expandedId === item.violation_id;
            return (
              <Fragment key={item.violation_id}>
                <tr
                  className="cursor-pointer hover:bg-slate-800/50 transition-colors"
                  onClick={() => setExpandedId(expanded ? null : item.violation_id)}
                >
                  <td className="font-medium">{item.user_name}</td>
                  <td>{item.department}</td>
                  <td>{`${item.role_a_name || "-"} + ${item.role_b_name || "-"}`}</td>
                  <td>
                    <span className={`rounded-full px-2 py-1 text-xs font-semibold ${severityPill(item.severity)}`}>
                      {item.severity}
                    </span>
                  </td>
                  <td className="max-w-[220px]">{item.regulatory_reference}</td>
                  <td>
                    {item.status !== "remediated" ? (
                      <button
                        type="button"
                        className="rounded-md bg-green-600 px-3 py-1 text-xs font-semibold text-white disabled:opacity-60"
                        onClick={(event) => {
                          event.stopPropagation();
                          onRemediate(item.violation_id);
                        }}
                        disabled={updatingId === item.violation_id}
                      >
                        {updatingId === item.violation_id ? "Saving..." : "Mark Remediated"}
                      </button>
                    ) : (
                      <span className="rounded-full bg-green-500/10 px-2 py-1 text-xs font-semibold text-green-400 border border-green-500/20">
                        Remediated
                      </span>
                    )}
                  </td>
                </tr>
                {expanded && (
                  <tr>
                    <td colSpan={6} className="bg-slate-900/50 p-4 text-xs text-slate-400 border-t border-bankBorder">
                      <div className="grid gap-2">
                        <p><strong>Rule:</strong> {item.rule_description}</p>
                        <p><strong>Permissions:</strong> {item.permission_a} / {item.permission_b}</p>
                        <p><strong>Status:</strong> {item.status}</p>
                        <p><strong>Recommended Action:</strong> {item.recommended_action}</p>
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
          {items.length === 0 && (
            <tr>
              <td colSpan={6} className="text-center text-slate-500">
                No SoD violations found for the selected filters.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
