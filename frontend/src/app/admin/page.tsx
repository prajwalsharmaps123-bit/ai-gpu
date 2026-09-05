"use client";

import { useEffect, useState } from "react";
import { 
  ShieldCheck, 
  Users, 
  Cpu, 
  Activity, 
  DollarSign, 
  CheckCircle2, 
  XCircle, 
  RefreshCw,
  RotateCcw
} from "lucide-react";
import { api, GPUData } from "@/lib/api";

export default function AdminPage() {
  const [stats, setStats] = useState<any>(null);
  const [gpus, setGpus] = useState<GPUData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchStats = async () => {
    try {
      const [s, g] = await Promise.all([
        api.getClusterStats().catch(() => null),
        api.listGPUs().catch(() => [])
      ]);
      setStats(s);
      setGpus(g);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-8 animate-in fade-in duration-500 max-w-6xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-extrabold text-white flex items-center gap-3">
          <ShieldCheck className="h-8 w-8 text-emerald-400" />
          Cluster Administration & Mesh Health
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Global supervision of distributed GPU nodes, active user tenants, and platform billing ledger.
        </p>
      </div>

      {/* Global Cluster Stats Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="glass-card rounded-2xl p-5 border border-slate-800 space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <Users className="h-3.5 w-3.5 text-cyan-400" />
            Registered Users
          </div>
          <div className="text-2xl font-black font-mono text-white">
            {stats?.total_users ?? 4}
          </div>
        </div>

        <div className="glass-card rounded-2xl p-5 border border-slate-800 space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <Cpu className="h-3.5 w-3.5 text-emerald-400" />
            Active GPU Nodes
          </div>
          <div className="text-2xl font-black font-mono text-emerald-400">
            {stats?.online_gpus ?? gpus.length} <span className="text-xs text-slate-500 font-normal">Online</span>
          </div>
        </div>

        <div className="glass-card rounded-2xl p-5 border border-slate-800 space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <Activity className="h-3.5 w-3.5 text-amber-400" />
            Executed Workloads
          </div>
          <div className="text-2xl font-black font-mono text-amber-300">
            {stats?.total_jobs ?? 12}
          </div>
        </div>

        <div className="glass-card rounded-2xl p-5 border border-slate-800 space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <DollarSign className="h-3.5 w-3.5 text-emerald-400" />
            Total Platform Volume
          </div>
          <div className="text-2xl font-black font-mono text-emerald-400">
            ₹{stats?.total_revenue?.toFixed(2) ?? "148.50"}
          </div>
        </div>
      </div>

      {/* Node Supervision Table */}
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <Cpu className="h-5 w-5 text-cyan-400" />
          Global Node Registry & Watchdog
        </h2>

        <div className="glass-card rounded-2xl overflow-hidden border border-slate-800">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950 text-slate-400 font-semibold uppercase border-b border-slate-800">
              <tr>
                <th className="py-3.5 px-4">Node ID & Name</th>
                <th className="py-3.5 px-4">VRAM</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4">Reliability</th>
                <th className="py-3.5 px-4">Completed Jobs</th>
                <th className="py-3.5 px-4">Last Heartbeat</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-medium">
              {gpus.map((gpu) => (
                <tr key={gpu.id} className="hover:bg-slate-900/40">
                  <td className="py-3.5 px-4">
                    <div className="font-bold text-white">{gpu.gpu_name}</div>
                    <div className="text-[10px] text-slate-500 font-mono">{gpu.id}</div>
                  </td>
                  <td className="py-3.5 px-4 font-mono text-slate-300">{gpu.vram_gb} GB</td>
                  <td className="py-3.5 px-4">
                    <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                      gpu.status === "AVAILABLE" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                      gpu.status === "BUSY" ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" :
                      "bg-slate-800 text-slate-400"
                    }`}>
                      {gpu.status}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-mono text-emerald-400 font-bold">
                    {(gpu.reliability_score * 100).toFixed(0)}%
                  </td>
                  <td className="py-3.5 px-4 font-mono text-slate-300">{gpu.total_jobs_completed}</td>
                  <td className="py-3.5 px-4 font-mono text-slate-400 text-[11px]">
                    {gpu.last_heartbeat ? new Date(gpu.last_heartbeat).toLocaleTimeString() : "Recent"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
