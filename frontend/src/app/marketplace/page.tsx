"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { 
  Cpu, 
  Search, 
  SlidersHorizontal, 
  ShieldCheck, 
  Zap, 
  CheckCircle, 
  AlertCircle,
  TrendingUp,
  DollarSign,
  Gauge,
  Terminal
} from "lucide-react";
import { api, GPUData } from "@/lib/api";
import SSHConnectModal from "@/components/SSHConnectModal";

export default function MarketplacePage() {
  const [gpus, setGpus] = useState<GPUData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [minVram, setMinVram] = useState<number>(0);
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");
  const [sortBy, setSortBy] = useState<string>("RELIABILITY");
  const [selectedSshGpu, setSelectedSshGpu] = useState<GPUData | null>(null);

  const fetchGPUs = async () => {
    try {
      const data = await api.listGPUs();
      setGpus(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGPUs();
    const interval = setInterval(fetchGPUs, 4000);
    return () => clearInterval(interval);
  }, []);

  const filteredGPUs = gpus.filter((gpu) => {
    const matchesSearch = gpu.gpu_name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesVram = gpu.vram_gb >= minVram;
    const matchesStatus = selectedStatus === "ALL" || gpu.status === selectedStatus;
    return matchesSearch && matchesVram && matchesStatus;
  }).sort((a, b) => {
    if (sortBy === "PRICE_ASC") return a.price_per_hour - b.price_per_hour;
    if (sortBy === "PRICE_DESC") return b.price_per_hour - a.price_per_hour;
    if (sortBy === "VRAM") return b.vram_gb - a.vram_gb;
    return b.reliability_score - a.reliability_score;
  });

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-white flex items-center gap-3">
            <Cpu className="h-8 w-8 text-emerald-400" />
            GPU Marketplace & Nodes
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Discover and reserve distributed GPU compute verified by PyNVML hardware telemetry.
          </p>
        </div>

        <Link
          href="/jobs/create"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 font-bold text-sm hover:brightness-110 shadow-lg shadow-emerald-500/20 transition-all self-start md:self-auto"
        >
          <Zap className="h-4 w-4 fill-current" />
          Deploy via AI Scheduler
        </Link>
      </div>

      {/* Filter & Search Bar */}
      <div className="glass-card rounded-2xl p-5 border border-slate-800 space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Search Input */}
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by GPU model (e.g. RTX 3060)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-slate-900/90 border border-slate-700/80 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500/50"
            />
          </div>

          {/* VRAM Filter */}
          <div className="flex items-center gap-3 px-3.5 py-2 bg-slate-900/90 border border-slate-700/80 rounded-xl text-xs">
            <span className="text-slate-400 whitespace-nowrap">Min VRAM:</span>
            <input
              type="range"
              min="0"
              max="48"
              step="2"
              value={minVram}
              onChange={(e) => setMinVram(Number(e.target.value))}
              className="w-full accent-emerald-400"
            />
            <span className="font-mono font-bold text-emerald-300 whitespace-nowrap">{minVram} GB</span>
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-2 px-3.5 py-2 bg-slate-900/90 border border-slate-700/80 rounded-xl text-xs">
            <span className="text-slate-400">Status:</span>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="bg-transparent text-slate-200 font-semibold focus:outline-none w-full cursor-pointer"
            >
              <option value="ALL" className="bg-slate-900">All Statuses</option>
              <option value="AVAILABLE" className="bg-slate-900">Available Only</option>
              <option value="BUSY" className="bg-slate-900">In Use / Busy</option>
              <option value="RESERVED" className="bg-slate-900">Reserved</option>
            </select>
          </div>

          {/* Sort By */}
          <div className="flex items-center gap-2 px-3.5 py-2 bg-slate-900/90 border border-slate-700/80 rounded-xl text-xs">
            <span className="text-slate-400">Sort:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="bg-transparent text-slate-200 font-semibold focus:outline-none w-full cursor-pointer"
            >
              <option value="RELIABILITY" className="bg-slate-900">Highest Reliability</option>
              <option value="PRICE_ASC" className="bg-slate-900">Price: Low to High</option>
              <option value="PRICE_DESC" className="bg-slate-900">Price: High to Low</option>
              <option value="VRAM" className="bg-slate-900">Largest VRAM</option>
            </select>
          </div>
        </div>
      </div>

      {/* GPU Catalogue Grid */}
      {loading ? (
        <div className="text-center py-16 text-slate-500 text-sm">Querying GPU marketplace nodes...</div>
      ) : filteredGPUs.length === 0 ? (
        <div className="glass-card rounded-2xl p-12 text-center space-y-3">
          <AlertCircle className="h-10 w-10 text-slate-600 mx-auto" />
          <p className="text-slate-300 font-medium">No GPU nodes matched your search filter criteria.</p>
          <button
            onClick={() => { setSearchQuery(""); setMinVram(0); setSelectedStatus("ALL"); }}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
          >
            Reset Filters
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredGPUs.map((gpu) => {
            const metric = gpu.latest_metric;
            const util = metric?.gpu_utilization ?? 0;
            const temp = metric?.temperature_c ?? 0;
            const memUsedMb = metric?.memory_used_mb ?? 0;
            const memTotalMb = gpu.vram_gb * 1024;
            const vramPct = Math.min((memUsedMb / maxNumber(memTotalMb, 1)) * 100, 100);

            return (
              <div
                key={gpu.id}
                className="glass-card rounded-2xl p-6 border border-slate-800 hover:border-emerald-500/30 transition-all flex flex-col justify-between space-y-5"
              >
                <div className="space-y-4">
                  {/* Top row */}
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className={`h-2.5 w-2.5 rounded-full ${
                          gpu.status === "AVAILABLE" ? "bg-emerald-400 animate-pulse" :
                          gpu.status === "BUSY" ? "bg-amber-400" :
                          gpu.status === "RESERVED" ? "bg-cyan-400" : "bg-slate-600"
                        }`} />
                        <h3 className="font-extrabold text-white text-lg tracking-tight">{gpu.gpu_name}</h3>
                      </div>
                      <div className="text-xs text-slate-400 font-mono mt-0.5 flex items-center gap-2">
                        <span>{gpu.vram_gb} GB VRAM • Driver {gpu.driver_version || "NVIDIA 550+"}</span>
                        {gpu.ssh_enabled !== false && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 flex items-center gap-1">
                            <Terminal className="h-2.5 w-2.5" /> SSH Ready
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="text-xl font-black font-mono text-emerald-400">
                        ₹{gpu.price_per_hour.toFixed(0)}<span className="text-xs text-slate-500 font-normal">/hr</span>
                      </div>
                      <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${
                        gpu.status === "AVAILABLE" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                        gpu.status === "BUSY" ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" :
                        gpu.status === "RESERVED" ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20" :
                        "bg-slate-800 text-slate-400"
                      }`}>
                        {gpu.status}
                      </span>
                    </div>
                  </div>

                  {/* Hardware Telemetry Progress Indicators */}
                  <div className="space-y-3 pt-3 border-t border-slate-800">
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-400">GPU Core Compute</span>
                        <span className="font-mono font-bold text-slate-200">{util.toFixed(1)}%</span>
                      </div>
                      <div className="h-2 w-full bg-slate-800/80 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-emerald-500 to-cyan-400 transition-all duration-500"
                          style={{ width: `${util}%` }}
                        />
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-400">VRAM Allocation</span>
                        <span className="font-mono font-bold text-slate-200">
                          {(memUsedMb / 1024).toFixed(1)} / {gpu.vram_gb.toFixed(1)} GB ({vramPct.toFixed(0)}%)
                        </span>
                      </div>
                      <div className="h-2 w-full bg-slate-800/80 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-cyan-500 transition-all duration-500"
                          style={{ width: `${vramPct}%` }}
                        />
                      </div>
                    </div>

                    {/* Sensor Badges */}
                    <div className="grid grid-cols-3 gap-2 pt-2">
                      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-2 text-center">
                        <div className="text-[10px] text-slate-500 uppercase">Thermal</div>
                        <div className="text-xs font-mono font-bold text-slate-200">{temp.toFixed(0)}°C</div>
                      </div>
                      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-2 text-center">
                        <div className="text-[10px] text-slate-500 uppercase">Power</div>
                        <div className="text-xs font-mono font-bold text-slate-200">{metric?.power_draw_w ? `${metric.power_draw_w.toFixed(0)}W` : "35W"}</div>
                      </div>
                      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-2 text-center">
                        <div className="text-[10px] text-slate-500 uppercase">Reliability</div>
                        <div className="text-xs font-mono font-bold text-emerald-400">{(gpu.reliability_score * 100).toFixed(0)}%</div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-800 flex items-center gap-2">
                  <Link
                    href={`/jobs/create?gpu=${gpu.id}`}
                    className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs font-bold transition-all shadow-md ${
                      gpu.status === "AVAILABLE"
                        ? "bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 hover:brightness-110 shadow-emerald-500/10"
                        : "bg-slate-900 text-slate-500 cursor-not-allowed border border-slate-800"
                    }`}
                  >
                    <Zap className="h-3.5 w-3.5 fill-current" />
                    {gpu.status === "AVAILABLE" ? "Launch Job" : "Occupied"}
                  </Link>

                  <button
                    onClick={() => setSelectedSshGpu(gpu)}
                    className="px-3 py-2.5 rounded-xl bg-slate-900/90 hover:bg-slate-800 border border-slate-700 text-emerald-400 text-xs font-bold flex items-center gap-1.5 transition-colors shadow-sm"
                    title="Connect to Host Computer via SSH or Web Shell"
                  >
                    <Terminal className="h-3.5 w-3.5" />
                    SSH Connect
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* SSH Connection Modal */}
      {selectedSshGpu && (
        <SSHConnectModal
          gpuId={selectedSshGpu.id}
          gpuName={selectedSshGpu.gpu_name}
          onClose={() => setSelectedSshGpu(null)}
        />
      )}
    </div>
  );
}

function maxNumber(a: number, b: number) {
  return a > b ? a : b;
}
