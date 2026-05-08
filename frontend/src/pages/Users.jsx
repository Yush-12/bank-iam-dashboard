import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { getUsers } from "../api/client";
import ErrorCard from "../components/ErrorCard";
import LoadingSpinner from "../components/LoadingSpinner";
import { daysSince, relativeDays, titleCase } from "../utils/format";
import { statusPill } from "../utils/styles";

const statusOptions = [
  { label: "All", value: "" },
  { label: "Active", value: "active" },
  { label: "Terminated", value: "terminated" },
  { label: "On Leave", value: "on_leave" },
  { label: "Suspended", value: "suspended" },
];

export default function Users() {
  const navigate = useNavigate();
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");

  const usersQuery = useQuery({
    queryKey: ["users", status],
    queryFn: () => getUsers({ status, limit: 300, offset: 0 }),
  });

  const filteredItems = useMemo(() => {
    const items = usersQuery.data?.items || [];
    if (!search.trim()) return items;
    const text = search.trim().toLowerCase();
    return items.filter(
      (item) =>
        item.name.toLowerCase().includes(text) ||
        item.department.toLowerCase().includes(text) ||
        item.employee_id.toLowerCase().includes(text)
    );
  }, [usersQuery.data?.items, search]);

  if (usersQuery.isLoading) return <LoadingSpinner label="Loading users..." />;
  if (usersQuery.isError) return <ErrorCard message={usersQuery.error.message} />;

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-100">Users</h2>

      <div className="flex flex-wrap gap-3 rounded-xl border border-bankBorder bg-bankSurface p-3">
        <input
          type="text"
          placeholder="Search by name or department"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="min-w-[250px] flex-1 rounded-md border border-bankBorder bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-bankPrimary focus:ring-1 focus:ring-bankPrimary"
        />
        <select
          value={status}
          onChange={(event) => setStatus(event.target.value)}
          className="rounded-md border border-bankBorder bg-slate-900 px-3 py-2 text-sm text-slate-100 focus:border-bankPrimary focus:ring-1 focus:ring-bankPrimary"
        >
          {statusOptions.map((option) => (
            <option key={option.value || "all"} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <div className="table-shell">
        <table className="table-base">
          <thead>
            <tr>
              <th>Employee ID</th>
              <th>Name</th>
              <th>Department</th>
              <th>Status</th>
              <th>Last Login</th>
              <th>Roles</th>
              <th>Risk</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-bankBorder bg-bankSurface">
            {filteredItems.map((user) => {
              const staleDays = daysSince(user.last_login);
              const stale = staleDays !== null && staleDays > 90;
              const risk = deriveRisk(user, staleDays);
              return (
                <tr
                  key={user.id}
                  className="cursor-pointer hover:bg-slate-800/50 transition-colors"
                  onClick={() => navigate(`/users/${user.id}`)}
                >
                  <td>{user.employee_id}</td>
                  <td className="font-medium">{user.name}</td>
                  <td>{user.department}</td>
                  <td>
                    <span className={`rounded-full px-2 py-1 text-xs font-semibold ${statusPill(user.status)}`}>
                      {titleCase(user.status)}
                    </span>
                  </td>
                  <td className={stale ? "font-semibold text-red-400" : ""}>{relativeDays(user.last_login)}</td>
                  <td>{user.role_count}</td>
                  <td>{risk}</td>
                </tr>
              );
            })}
            {filteredItems.length === 0 && (
              <tr>
                <td colSpan={7} className="text-center text-slate-500">
                  No users match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function deriveRisk(user, staleDays) {
  if (user.status === "terminated" || user.status === "suspended") return "High";
  if (staleDays !== null && staleDays > 90) return "High";
  if (user.role_count >= 3) return "Medium";
  return "Low";
}
