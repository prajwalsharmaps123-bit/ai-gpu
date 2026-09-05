"use client";

import { useEffect, useState } from "react";
import { 
  Server, 
  Cpu, 
  Wallet, 
  TrendingUp, 
  Terminal, 
  Copy, 
  Check, 
  Zap, 
  ShieldCheck,
  RefreshCw,
  Plus
} from "lucide-react";
import { api, getStoredUser, UserData } from "@/lib/api";

export default function ProviderPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [copied, setCopied] = useState<boolean>(false);
  const [user, setUser] = useState<UserData | null>(null);

  const fetchProviderData = async () => {
    try {
      const res = await api.getProviderDashboard();
      setData(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setUser(getStoredUser());
    fetchProviderData();
    const interval = setInterval(fetchProviderData, 4000);
    return () => clearInterval(interval);
  }, []);

  const agentCommand = `python gpu-agent/agent.py --server http://127.0.0.1:8000`;

  const copyToClipboard = () => {
    navigator.clipboard.writeText(agentCommand);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-white flex items-center gap-3">
            <Server className="h-8 w-8 text-cyan-400" />
            GPU Provider Hub
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Monetize idle GPU compute. Install the Python Agent to connect and earn automatically.
          </p>
        </div>

        {/* Quick Earnings */}
        <div className="flex items-center gap-4 bg-slate-900/90 border border-emerald-500/30 rounded-2xl px-5 py-3 shadow-inner">
          <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400">
            <Wallet className="h-6 w-6" />
          </div>
          <div>
            <div className="text-[11px] text-slate-400 font-semibold uppercase">Total Payout Balance</div>
            <div className="text-2xl font-black font-mono text-emerald-400">
              ₹{data?.wallet_balance?.toFixed(2) || "0.00"}
            </div>
          </div>
        </div>
      </div>

      {/* Provider Quick Install Agent Box */}
      <div className="glass-card rounded-3xl p-6 sm:p-8 border border-slate-800 bg-gradient-to-r from-slate-900/90 to-slate-950 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-white font-bold text-base">
            <Terminal className="h-5 w-5 text-emerald-400" />
            Connect Your GPU Provider Agent
          </div>
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-mono">
            PyNVML + WebSocket
          </span>
        </div>
        <p className="text-xs text-slate-400 leading-relaxed">
          Run the lightweight GPU agent daemon on your machine. It queries real NVIDIA VRAM, temperature, power, and utilization via PyNVML, securely listens for container workloads, and deposits compute earnings into your wallet.
        </p>

        <div className="flex items-center justify-between bg-slate-950 px-4 py-3 rounded-2xl border border-slate-800 font-mono text-xs text-emerald-300">
          <code>{agentCommand}</code>
          <button
            onClick={copyToClipboard}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-semibold transition-colors"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? "Copied!" : "Copy"}
          </button>
        </div>
      </div>

      {/* Provider Nodes List */}
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <Cpu className="h-5 w-5 text-emerald-400" />
          My Registered Compute Nodes ({data?.gpus?.length || 0})
        </h2>

        {!data || data.gpus?.length === 0 ? (
          <div className="glass-card rounded-2xl p-10 text-center space-y-2">
            <Cpu className="h-10 w-10 text-slate-600 mx-auto" />
            <p className="text-slate-300 font-medium">No GPU nodes currently registered to your account.</p>
            <p className="text-xs text-slate-500">Run the agent command above to auto-register your hardware!</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {data.gpus.map((gpu: any) => {
              const metric = gpu.latest_metric;
              const isOnline = gpu.status !== "OFFLINE";
              return (
                <div key={gpu.id} className="glass-card rounded-2xl p-6 border border-slate-800 space-y-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className={`h-2.5 w-2.5 rounded-full ${
                          gpu.status === "AVAILABLE" ? "bg-emerald-400 animate-pulse" :
                          gpu.status === "BUSY" ? "bg-amber-400 animate-pulse" : "bg-slate-600"
                        }`} />
                        <h3 className="font-extrabold text-white text-base">{gpu.gpu_name}</h3>
                      </div>
                      <div className="text-xs text-slate-400 font-mono mt-0.5">
                        {gpu.vram_gb} GB VRAM • Price: ₹{gpu.price_per_hour}/hr
                      </div>
                    </div>
                    <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${
                      gpu.status === "AVAILABLE" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                      gpu.status === "BUSY" ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" :
                      "bg-slate-800 text-slate-400"
                    }`}>
                      {gpu.status}
                    </span>
                  </div>

                  {/* Telemetry */}
                  <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-800 text-center">
                    <div className="bg-slate-900/80 p-2.5 rounded-xl border border-slate-800">
                      <div className="text-[10px] text-slate-500">Utilization</div>
                      <div className="text-xs font-mono font-bold text-slate-200">
                        {metric?.gpu_utilization ? `${metric.gpu_utilization.toFixed(1)}%` : "0.0%"}
                      </div>
                    </div>
                    <div className="bg-slate-900/80 p-2.5 rounded-xl border border-slate-800">
                      <div className="text-[10px] text-slate-500">Temperature</div>
                      <div className="text-xs font-mono font-bold text-slate-200">
                        {metric?.temperature_c ? `${metric.temperature_c.toFixed(0)}°C` : "45°C"}
                      </div>
                    </div>
                    <div className="bg-slate-900/80 p-2.5 rounded-xl border border-slate-800">
                      <div className="text-[10px] text-slate-500">Reliability</div>
                      <div className="text-xs font-mono font-bold text-emerald-400">
                        {(gpu.reliability_score * 100).toFixed(0)}%
                      </div>
                    </div>
                  </div>

                  {/* SSH Connectivity Status */}
                  <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800/80 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <Terminal className="h-4 w-4 text-cyan-400" />
                      <div>
                        <div className="text-slate-300 font-semibold">SSH Remote Gateway</div>
                        <div className="text-[11px] font-mono text-slate-400">
                          {gpu.ssh_username || "gpuuser"}@{gpu.ssh_host || "127.0.0.1"}:{gpu.ssh_port || 22}
                        </div>
                      </div>
                    </div>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                      Active
                    </span>
                  </div>

                  <div className="text-[11px] text-slate-500 font-mono truncate">
                    Agent Key: {gpu.agent_auth_key || "Auto-Provisioned"}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Payout & Earnings Ledger */}
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-emerald-400" />
          Recent Provider Compute Earnings
        </h2>

        {(!data?.recent_earnings || data.recent_earnings.length === 0) ? (
          <div className="glass-card rounded-2xl p-6 text-center text-xs text-slate-500">
            No earnings transactions yet. When users execute workloads on your GPU, 90% of compute fees will appear here.
          </div>
        ) : (
          <div className="glass-card rounded-2xl overflow-hidden border border-slate-800">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 uppercase font-semibold border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Transaction Description</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4 text-right">Earning</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium">
                {data.recent_earnings.map((tx: any) => (
                  <tr key={tx.id} className="hover:bg-slate-900/40">
                    <td className="py-3 px-4 text-slate-200">{tx.description}</td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-mono text-[10px]">
                        {tx.type}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-400 font-mono">{new Date(tx.timestamp).toLocaleString()}</td>
                    <td className="py-3 px-4 font-mono font-bold text-emerald-400 text-right">+₹{tx.amount.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
