"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { 
  Cpu, 
  Activity, 
  Layers, 
  Zap, 
  Play, 
  TrendingUp, 
  CheckCircle2, 
  Clock, 
  ArrowRight,
  Shield,
  BarChart3,
  Server
} from "lucide-react";
import { api, GPUData, JobData, UserData, getStoredUser } from "@/lib/api";

export default function DashboardPage() {
  const [gpus, setGpus] = useState<GPUData[]>([]);
  const [jobs, setJobs] = useState<JobData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [user, setUser] = useState<UserData | null>(null);

  const fetchDashboardData = async () => {
    try {
      const [gpuList, jobList] = await Promise.all([
        api.listGPUs().catch(() => []),
        api.listJobs().catch(() => [])
      ]);
      setGpus(gpuList);
      setJobs(jobList);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setUser(getStoredUser());
    fetchDashboardData();
    // Poll telemetry every 4 seconds
    const interval = setInterval(fetchDashboardData, 4000);
    return () => clearInterval(interval);
  }, []);

  const onlineGpus = gpus.filter(g => g.status === "AVAILABLE" || g.status === "BUSY" || g.status === "RESERVED");
  const runningJobs = jobs.filter(j => j.status === "RUNNING" || j.status === "STARTING");
  const totalCompleted = jobs.filter(j => j.status === "COMPLETED").length;

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Hero / Platform Overview */}
      <div className="relative overflow-hidden rounded-3xl glass-card p-8 lg:p-10 border border-slate-800 bg-gradient-to-br from-slate-900/90 via-slate-950 to-slate-900">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute bottom-0 left-1/3 -mb-16 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="max-w-2xl space-y-3">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold">
              <Zap className="h-3.5 w-3.5" />
              <span>Intelligent Cost-Aware Scheduling Active</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-white">
              Distributed GPU Compute Mesh
            </h1>
            <p className="text-slate-400 text-sm leading-relaxed">
              Execute deep learning training, fine-tuning, and inference workloads across distributed provider GPUs with ML-predicted uptime & cost minimization.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/jobs/create"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 font-bold text-sm hover:brightness-110 shadow-lg shadow-emerald-500/20 transition-all"
            >
              <Play className="h-4 w-4 fill-current" />
              Deploy Workload
            </Link>
            <Link
              href="/marketplace"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-200 font-semibold text-sm transition-all"
            >
              <Cpu className="h-4 w-4 text-cyan-400" />
              Browse GPUs
            </Link>
          </div>
        </div>

        {/* Metric Quick Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-8 pt-8 border-t border-slate-800/80">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Server className="h-3.5 w-3.5 text-emerald-400" />
              <span>Online GPUs</span>
            </div>
            <div className="text-2xl font-black font-mono text-white">
              {onlineGpus.length} <span className="text-xs text-slate-500 font-normal">/ {gpus.length} Nodes</span>
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Activity className="h-3.5 w-3.5 text-cyan-400" />
              <span>Running Workloads</span>
            </div>
            <div className="text-2xl font-black font-mono text-cyan-300">
              {runningJobs.length}
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
              <span>Completed Jobs</span>
            </div>
            <div className="text-2xl font-black font-mono text-emerald-400">
              {totalCompleted}
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <TrendingUp className="h-3.5 w-3.5 text-blue-400" />
              <span>Availability Rate</span>
            </div>
            <div className="text-2xl font-black font-mono text-white">
              98.4%
            </div>
          </div>
        </div>
      </div>

      {/* Cluster GPUs Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Cpu className="h-5 w-5 text-emerald-400" />
              Active GPU Compute Nodes
            </h2>
            <p className="text-xs text-slate-400">Live telemetry updated in real-time via WebSocket agent daemons</p>
          </div>
          <Link href="/marketplace" className="text-xs text-emerald-400 hover:text-emerald-300 flex items-center gap-1 font-semibold">
            View Marketplace <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        {loading && gpus.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-sm">Discovering GPU cluster telemetry...</div>
        ) : gpus.length === 0 ? (
          <div className="glass-card rounded-2xl p-8 text-center space-y-3">
            <Cpu className="h-10 w-10 text-slate-600 mx-auto" />
            <p className="text-slate-300 font-medium text-sm">No GPU nodes currently connected</p>
            <p className="text-xs text-slate-500">Run the GPU Provider Agent on your computer to connect your NVIDIA GPU to this mesh.</p>
            <Link href="/provider" className="inline-block px-4 py-2 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-semibold">
              Connect Your GPU Node
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {gpus.map((gpu) => {
              const metric = gpu.latest_metric;
              const isOnline = gpu.status !== "OFFLINE";
              const util = metric?.gpu_utilization ?? 0;
              const temp = metric?.temperature_c ?? 0;
              const memUsed = metric?.memory_used_mb ? (metric.memory_used_mb / 1024).toFixed(1) : "0.0";
              const memTotal = gpu.vram_gb.toFixed(1);

              return (
                <div key={gpu.id} className="glass-card rounded-2xl p-5 border border-slate-800 hover:border-slate-700 transition-all space-y-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className={`h-2.5 w-2.5 rounded-full ${
                          gpu.status === "AVAILABLE" ? "bg-emerald-400 animate-pulse" :
                          gpu.status === "BUSY" ? "bg-amber-400 animate-pulse" :
                          gpu.status === "RESERVED" ? "bg-cyan-400 animate-pulse" : "bg-slate-600"
                        }`} />
                        <h3 className="font-bold text-white text-base">{gpu.gpu_name}</h3>
                      </div>
                      <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                        {gpu.vram_gb} GB VRAM • CUDA {gpu.cuda_version || "12.x"}
                      </p>
                    </div>
                    <div className="text-right">
                      <div className="text-base font-black font-mono text-emerald-400">
                        ₹{gpu.price_per_hour.toFixed(0)}<span className="text-[10px] text-slate-500 font-normal">/hr</span>
                      </div>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        gpu.status === "AVAILABLE" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                        gpu.status === "BUSY" ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" :
                        gpu.status === "RESERVED" ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20" :
                        "bg-slate-800 text-slate-400"
                      }`}>
                        {gpu.status}
                      </span>
                    </div>
                  </div>

                  {/* Telemetry Bars */}
                  <div className="space-y-2.5 pt-2 border-t border-slate-800/80">
                    <div className="space-y-1">
                      <div className="flex justify-between text-[11px]">
                        <span className="text-slate-400">GPU Core Load</span>
                        <span className="font-mono text-slate-200">{util}%</span>
                      </div>
                      <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-emerald-500 to-cyan-400 transition-all duration-500"
                          style={{ width: `${Math.min(util, 100)}%` }}
                        />
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="flex justify-between text-[11px]">
                        <span className="text-slate-400">VRAM Allocation</span>
                        <span className="font-mono text-slate-200">{memUsed} / {memTotal} GB</span>
                      </div>
                      <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-cyan-500 transition-all duration-500"
                          style={{ width: `${Math.min((parseFloat(memUsed) / gpu.vram_gb) * 100, 100)}%` }}
                        />
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-[11px] pt-1 text-slate-400">
                      <span>Thermal: <strong className="text-slate-200 font-mono">{temp}°C</strong></span>
                      <span>Power: <strong className="text-slate-200 font-mono">{metric?.power_draw_w ? `${metric.power_draw_w.toFixed(0)}W` : "35W"}</strong></span>
                      <span>Rel: <strong className="text-emerald-400 font-mono">{(gpu.reliability_score * 100).toFixed(0)}%</strong></span>
                    </div>
                  </div>

                  <Link
                    href={`/jobs/create?gpu=${gpu.id}`}
                    className={`block w-full text-center py-2 rounded-xl text-xs font-bold transition-all ${
                      gpu.status === "AVAILABLE"
                        ? "bg-slate-800 hover:bg-emerald-500 hover:text-slate-950 text-slate-200 border border-slate-700 shadow-sm"
                        : "bg-slate-900 text-slate-500 cursor-not-allowed border border-slate-800"
                    }`}
                  >
                    {gpu.status === "AVAILABLE" ? "Deploy on this GPU" : "Currently In Use"}
                  </Link>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Recent Workload Jobs Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Layers className="h-5 w-5 text-cyan-400" />
              Workload Execution History
            </h2>
            <p className="text-xs text-slate-400">All submitted distributed training & inference jobs</p>
          </div>
        </div>

        {jobs.length === 0 ? (
          <div className="glass-card rounded-2xl p-8 text-center space-y-2">
            <p className="text-slate-400 text-sm">No workloads submitted yet.</p>
            <Link href="/jobs/create" className="text-xs text-emerald-400 font-semibold hover:underline">
              Submit your first job &rarr;
            </Link>
          </div>
        ) : (
          <div className="glass-card rounded-2xl overflow-hidden border border-slate-800">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/80 text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-800">
                  <tr>
                    <th className="py-3.5 px-4">Job Title & Spec</th>
                    <th className="py-3.5 px-4">Assigned GPU</th>
                    <th className="py-3.5 px-4">Scheduler Strategy</th>
                    <th className="py-3.5 px-4">Status</th>
                    <th className="py-3.5 px-4">Runtime</th>
                    <th className="py-3.5 px-4">Cost Charged</th>
                    <th className="py-3.5 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-medium">
                  {jobs.map((job) => (
                    <tr key={job.id} className="hover:bg-slate-900/40 transition-colors">
                      <td className="py-3.5 px-4">
                        <div className="font-bold text-slate-200">{job.title}</div>
                        <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                          {job.framework} • {job.workload_type}
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-slate-300">
                        {job.gpu_name || "Auto-Selected"}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="px-2 py-0.5 rounded-md bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-mono text-[10px]">
                          {job.scheduling_strategy}
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold ${
                          job.status === "RUNNING" ? "bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse" :
                          job.status === "COMPLETED" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                          job.status === "FAILED" ? "bg-rose-500/10 text-rose-400 border border-rose-500/20" :
                          job.status === "RESERVED" ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20" :
                          "bg-slate-800 text-slate-400"
                        }`}>
                          {job.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-300">
                        {job.actual_runtime_seconds > 0 ? `${job.actual_runtime_seconds.toFixed(1)}s` : "-"}
                      </td>
                      <td className="py-3.5 px-4 font-mono font-bold text-emerald-400">
                        {job.cost_charged > 0 ? `₹${job.cost_charged.toFixed(2)}` : "₹0.00"}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <Link
                          href={`/jobs/${job.id}`}
                          className="inline-flex items-center gap-1 px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-[11px] font-semibold transition-colors"
                        >
                          Logs & Monitor
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
