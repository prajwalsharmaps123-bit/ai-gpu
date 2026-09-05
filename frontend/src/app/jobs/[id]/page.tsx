"use client";

import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { 
  Terminal, 
  Cpu, 
  Activity, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  DollarSign, 
  ArrowLeft,
  RefreshCw,
  StopCircle,
  Zap,
  Sparkles
} from "lucide-react";
import { api, JobData, WS_BASE } from "@/lib/api";
import SSHConnectModal from "@/components/SSHConnectModal";

export default function JobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;

  const [job, setJob] = useState<JobData | null>(null);
  const [logs, setLogs] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [cancelling, setCancelling] = useState<boolean>(false);
  const [showSshModal, setShowSshModal] = useState<boolean>(false);
  const terminalBottomRef = useRef<HTMLDivElement>(null);

  const fetchJob = async () => {
    try {
      const data = await api.getJob(jobId);
      setJob(data);
      if (data.logs && !logs) {
        setLogs(data.logs);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJob();
    const interval = setInterval(fetchJob, 3000);
    return () => clearInterval(interval);
  }, [jobId]);

  // Connect WebSocket for live streaming logs
  useEffect(() => {
    if (!jobId) return;
    const wsUrl = `${WS_BASE}/ws/jobs/${jobId}/logs`;
    let ws: WebSocket | null = null;

    try {
      ws = new WebSocket(wsUrl);
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "JOB_LOG" && msg.data) {
            setLogs((prev) => prev + msg.data);
          }
        } catch {
          setLogs((prev) => prev + event.data);
        }
      };
    } catch (err) {
      console.error("WS error:", err);
    }

    return () => {
      if (ws) ws.close();
    };
  }, [jobId]);

  // Auto scroll terminal
  useEffect(() => {
    terminalBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const handleCancel = async () => {
    if (!confirm("Are you sure you want to cancel this workload execution?")) return;
    setCancelling(true);
    try {
      await api.cancelJob(jobId);
      await fetchJob();
    } catch (err: any) {
      alert(err.message || "Failed to cancel job.");
    } finally {
      setCancelling(false);
    }
  };

  if (loading && !job) {
    return (
      <div className="text-center py-20 text-slate-500 text-sm">
        <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2 text-emerald-400" />
        Loading workload execution stream...
      </div>
    );
  }

  if (!job) {
    return (
      <div className="glass-card rounded-2xl p-12 text-center space-y-4 max-w-lg mx-auto">
        <XCircle className="h-12 w-12 text-rose-500 mx-auto" />
        <h2 className="text-xl font-bold text-white">Workload Not Found</h2>
        <p className="text-xs text-slate-400">The requested job ID does not exist or has expired.</p>
        <Link href="/" className="inline-block px-4 py-2 rounded-xl bg-slate-800 text-slate-200 text-xs font-semibold">
          Back to Dashboard
        </Link>
      </div>
    );
  }

  const isTerminal = ["COMPLETED", "FAILED", "CANCELLED"].includes(job.status);

  return (
    <div className="space-y-6 animate-in fade-in duration-500 max-w-6xl mx-auto">
      {/* Back button & Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="space-y-1">
          <Link href="/" className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 mb-1">
            <ArrowLeft className="h-3.5 w-3.5" /> Back to Dashboard
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl sm:text-3xl font-black text-white">{job.title}</h1>
            <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-extrabold ${
              job.status === "RUNNING" ? "bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse" :
              job.status === "COMPLETED" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
              job.status === "FAILED" ? "bg-rose-500/10 text-rose-400 border border-rose-500/20" :
              job.status === "RESERVED" ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20" :
              "bg-slate-800 text-slate-400"
            }`}>
              <span className="h-2 w-2 rounded-full bg-current" />
              {job.status}
            </span>
          </div>
          <div className="text-xs text-slate-400 font-mono">
            Job ID: {job.id} • Submitted: {new Date(job.created_at).toLocaleTimeString()}
          </div>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          {job.gpu_id && (
            <button
              onClick={() => setShowSshModal(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-emerald-400 text-xs font-bold transition-all shadow-sm"
              title="Open Interactive SSH / Shell Terminal to GPU Host"
            >
              <Terminal className="h-4 w-4" />
              SSH / Shell Access
            </button>
          )}

          {!isTerminal && (
            <button
              onClick={handleCancel}
              disabled={cancelling}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 hover:bg-rose-500/20 text-xs font-bold transition-all"
            >
              <StopCircle className="h-4 w-4" />
              {cancelling ? "Terminating..." : "Cancel Job"}
            </button>
          )}
        </div>
      </div>

      {/* Execution Diagnostics Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="glass-card rounded-2xl p-4 border border-slate-800 space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <Cpu className="h-3.5 w-3.5 text-emerald-400" />
            Assigned GPU
          </div>
          <div className="text-base font-bold text-white truncate">
            {job.gpu_name || "Auto-Scheduled"}
          </div>
        </div>

        <div className="glass-card rounded-2xl p-4 border border-slate-800 space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <Zap className="h-3.5 w-3.5 text-cyan-400" />
            Scheduler Score
          </div>
          <div className="text-base font-bold font-mono text-cyan-300">
            {job.scheduler_score ? `${job.scheduler_score.toFixed(3)}` : "Optimal"}
          </div>
        </div>

        <div className="glass-card rounded-2xl p-4 border border-slate-800 space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 text-amber-400" />
            Actual Runtime
          </div>
          <div className="text-base font-bold font-mono text-slate-200">
            {job.actual_runtime_seconds > 0 ? `${job.actual_runtime_seconds.toFixed(1)}s` : (job.status === "RUNNING" ? "Executing..." : "-")}
          </div>
        </div>

        <div className="glass-card rounded-2xl p-4 border border-slate-800 space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <DollarSign className="h-3.5 w-3.5 text-emerald-400" />
            Billed Compute Cost
          </div>
          <div className="text-base font-bold font-mono text-emerald-400">
            ₹{job.cost_charged.toFixed(2)}
          </div>
        </div>
      </div>

      {/* Live Terminal & Logs Stream */}
      <div className="glass-card rounded-3xl overflow-hidden border border-slate-800 shadow-2xl">
        <div className="bg-slate-950/90 px-5 py-3.5 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5">
              <span className="h-3 w-3 rounded-full bg-rose-500/80 inline-block" />
              <span className="h-3 w-3 rounded-full bg-amber-500/80 inline-block" />
              <span className="h-3 w-3 rounded-full bg-emerald-500/80 inline-block" />
            </div>
            <span className="text-xs font-mono text-slate-400 ml-2 flex items-center gap-1.5">
              <Terminal className="h-3.5 w-3.5 text-slate-400" />
              container_stdout_stderr.log (Live WebSocket Stream)
            </span>
          </div>

          {job.status === "RUNNING" && (
            <div className="flex items-center gap-2 text-[11px] text-emerald-400 font-mono font-medium">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
              STREAMING
            </div>
          )}
        </div>

        <div className="bg-slate-950 p-6 min-h-[380px] max-h-[550px] overflow-y-auto font-mono text-xs text-emerald-400 space-y-1 leading-relaxed selection:bg-emerald-500 selection:text-slate-950">
          <pre className="whitespace-pre-wrap">
            {logs || "[AI-GPUShare Gateway] Connecting to remote GPU container log stream...\n"}
          </pre>
          <div ref={terminalBottomRef} />
        </div>
      </div>

      {/* SSH Connection Modal */}
      {showSshModal && job.gpu_id && (
        <SSHConnectModal
          gpuId={job.gpu_id}
          gpuName={job.gpu_name || "Assigned GPU Host"}
          onClose={() => setShowSshModal(false)}
        />
      )}
    </div>
  );
}
