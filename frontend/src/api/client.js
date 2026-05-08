import axios from "axios";

export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

const client = axios.create({
  baseURL: API_URL,
  timeout: 20000,
});

client.interceptors.request.use((config) => {
  const nextConfig = { ...config };
  nextConfig.headers = nextConfig.headers || {};
  if (!nextConfig.headers["Content-Type"]) {
    nextConfig.headers["Content-Type"] = "application/json";
  }
  return nextConfig;
});

client.interceptors.response.use(
  (response) => {
    if (response.config.responseType === "blob") {
      return response;
    }

    const payload = response.data;
    if (payload && typeof payload === "object" && "success" in payload) {
      if (payload.success) {
        return payload.data;
      }
      const message = payload.error || "Request failed";
      const error = new Error(message);
      error.code = payload.code || response.status;
      throw error;
    }

    return payload;
  },
  (error) => {
    const message =
      error?.response?.data?.error ||
      error?.message ||
      "Unable to complete the request.";
    const wrapped = new Error(message);
    wrapped.code = error?.response?.data?.code || error?.response?.status || 500;
    return Promise.reject(wrapped);
  }
);

const withPaging = (filters = {}) => ({
  limit: filters.limit ?? 50,
  offset: filters.offset ?? 0,
});

export const getDashboardSummary = async () => client.get("/api/dashboard/summary");

export const getSoDViolations = async (filters = {}) =>
  client.get("/api/violations/sod", {
    params: {
      ...withPaging(filters),
      severity: filters.severity || undefined,
      status: filters.status || undefined,
    },
  });

export const getOrphanAccounts = async (filters = {}) =>
  client.get("/api/violations/orphans", { params: withPaging(filters) });

export const getOverPrivilegedUsers = async (filters = {}) =>
  client.get("/api/violations/overprivileged", { params: withPaging(filters) });

export const updateViolationStatus = async (violationId, status) => {
  try {
    return await client.patch(`/api/violations/${violationId}/status`, { status });
  } catch (error) {
    if (error.code === 405) {
      return client.post(`/api/violations/${violationId}/status`, { status });
    }
    throw error;
  }
};

export const getUsers = async (filters = {}) =>
  client.get("/api/users", {
    params: {
      ...withPaging(filters),
      department: filters.department || undefined,
      status: filters.status || undefined,
    },
  });

export const getUserDetail = async (id) => client.get(`/api/users/${id}`);

export const getRoles = async (filters = {}) =>
  client.get("/api/roles", { params: withPaging(filters) });

export const getConsolidationSuggestions = async (filters = {}) =>
  client.get("/api/rbac/consolidation", { params: withPaging(filters) });

export const getRbacHealth = async () => client.get("/api/rbac/health");

export const runAnalysis = async () => client.post("/api/analysis/run");

export const randomizeData = async () => client.post("/api/settings/randomize");

export const uploadCustomData = async (file) => {
  const formData = new FormData();
  formData.append("file", file);
  return client.post("/api/settings/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};
export const generateReport = async () => {
  const response = await client.get("/api/report/generate", {
    responseType: "blob",
  });
  const disposition = response.headers["content-disposition"] || "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match ? match[1] : "access_certification_report.pdf";
  return { blob: response.data, filename };
};

export async function warmupBackend() {
  try {
    await client.get("/api/health", { timeout: 35000 });
  } catch (e) {
    /* ignore */
  }
}
