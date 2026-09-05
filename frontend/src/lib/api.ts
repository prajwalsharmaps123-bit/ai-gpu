const apiHost = process.env.NEXT_PUBLIC_API_HOST;
export const API_BASE = process.env.NEXT_PUBLIC_API_URL 
  ? process.env.NEXT_PUBLIC_API_URL 
  : apiHost 
    ? (apiHost.startsWith("http") ? `${apiHost}/api/v1` : `https://${apiHost}/api/v1`)
    : "http://127.0.0.1:8000/api/v1";

export const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || API_BASE.replace(/^http/, "ws");

export interface GPUData {
  id: string;
  provider_id: string;
  gpu_name: string;
  vram_gb: number;
  driver_version?: string;
  cuda_version?: string;
  price_per_hour: number;
  status: "AVAILABLE" | "RESERVED" | "BUSY" | "OFFLINE" | "MAINTENANCE";
  reliability_score: number;
  total_jobs_completed: number;
  total_uptime_hours: number;
  last_heartbeat?: string;
  agent_auth_key?: string;
  is_simulated: boolean;
  ssh_enabled?: boolean;
  ssh_host?: string;
  ssh_port?: number;
  ssh_username?: string;
  ssh_auth_type?: string;
  ssh_active_sessions?: number;
  latest_metric?: {
    gpu_utilization: number;
    memory_used_mb: number;
    memory_total_mb: number;
    temperature_c: number;
    power_draw_w: number;
    cpu_utilization: number;
    ram_used_mb: number;
    ram_total_mb: number;
  };
}

export interface SSHConnectionInfo {
  gpu_id: string;
  gpu_name: string;
  status: string;
  ssh_enabled: boolean;
  ssh_host: string;
  ssh_port: number;
  ssh_username: string;
  ssh_password?: string;
  ssh_auth_type: string;
  ssh_cli_command: string;
  vscode_config_snippet: string;
  jupyter_tunnel_command: string;
  scp_upload_command: string;
  interactive_ws_url: string;
}

export interface JobData {
  id: string;
  user_id: string;
  gpu_id?: string;
  gpu_name?: string;
  title: string;
  workload_type: string;
  framework: string;
  docker_image: string;
  script_command: string;
  min_vram_gb: number;
  expected_runtime_hours: number;
  budget_max: number;
  priority: string;
  scheduling_strategy: string;
  predicted_availability?: number;
  predicted_runtime_hours?: number;
  predicted_cost?: number;
  scheduler_score?: number;
  status: "CREATED" | "QUEUED" | "SCHEDULING" | "RESERVED" | "STARTING" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED";
  actual_start_time?: string;
  actual_end_time?: string;
  actual_runtime_seconds: number;
  cost_charged: number;
  provider_earned: number;
  logs?: string;
  exit_code?: number;
  created_at: string;
  ssh_command?: string;
}

export interface UserData {
  id: string;
  name: string;
  email: string;
  role: string;
  wallet_balance: number;
}

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("aigpushare_token");
}

export function setAuthSession(token: string, user: UserData) {
  if (typeof window === "undefined") return;
  localStorage.setItem("aigpushare_token", token);
  localStorage.setItem("aigpushare_user", JSON.stringify(user));
}

export function getStoredUser(): UserData | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("aigpushare_user");
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function clearAuthSession() {
  if (typeof window === "undefined") return;
  localStorage.removeItem("aigpushare_token");
  localStorage.removeItem("aigpushare_user");
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let errMessage = `Request failed: ${res.statusText}`;
    try {
      const body = await res.json();
      if (body.detail) errMessage = body.detail;
    } catch {}
    throw new Error(errMessage);
  }

  return res.json();
}

export const api = {
  // Auth
  register: (data: any) => request<{ access_token: string; user: UserData }>("/auth/register", { method: "POST", body: JSON.stringify(data) }),
  login: (data: any) => request<{ access_token: string; user: UserData }>("/auth/login", { method: "POST", body: JSON.stringify(data) }),
  me: () => request<UserData>("/auth/me"),

  // GPUs
  listGPUs: () => request<GPUData[]>("/gpus"),
  getGPU: (id: string) => request<GPUData>(`/gpus/${id}`),
  getGPUSSHInfo: (id: string) => request<SSHConnectionInfo>(`/gpus/${id}/ssh-info`),
  updateGPUSSHConfig: (id: string, data: any) => request<GPUData>(`/gpus/${id}/ssh-config`, { method: "PUT", body: JSON.stringify(data) }),
  registerGPU: (data: any) => request<GPUData>("/gpus/register", { method: "POST", body: JSON.stringify(data) }),

  // Jobs
  submitJob: (data: any) => request<JobData>("/jobs", { method: "POST", body: JSON.stringify(data) }),
  listJobs: () => request<JobData[]>("/jobs"),
  getJob: (id: string) => request<JobData>(`/jobs/${id}`),
  cancelJob: (id: string) => request<{ message: string }>(`/jobs/${id}/cancel`, { method: "POST" }),

  // Provider
  getProviderDashboard: () => request<any>("/provider/dashboard"),

  // ML Services
  predictAvailability: (data: any) => request<any>("/ml/predict-availability", { method: "POST", body: JSON.stringify(data) }),
  predictRuntime: (data: any) => request<any>("/ml/predict-runtime", { method: "POST", body: JSON.stringify(data) }),
  getModelMetrics: () => request<any>("/ml/metrics"),

  // Admin
  getClusterStats: () => request<any>("/admin/stats"),
};
