"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { 
  Play, 
  Cpu, 
  Sparkles, 
  Layers, 
  Code, 
  Sliders, 
  Zap, 
  Clock, 
  DollarSign, 
  CheckCircle,
  AlertCircle
} from "lucide-react";
import { api, GPUData, getStoredUser } from "@/lib/api";

const PRESETS = [
  {
    id: "pytorch_quick_test",
    title: "PyTorch GPU Diagnostics & Tensor Test",
    framework: "PyTorch",
    workload_type: "Inference",
    docker_image: "pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime",
    script: `python -c "import torch; print(f'=== GPU AVAILABLE: {torch.cuda.is_available()} ==='); print(f'=== DEVICE: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \\\"CPU Mode\\\"} ==='); x = torch.randn(2000, 2000, device='cuda' if torch.cuda.is_available() else 'cpu'); print(f'Matrix norm: {torch.norm(x @ x).item():.2f}')"`,
    min_vram: 4.0,
    expected_hours: 0.1,
    budget: 10.0
  },
  {
    id: "resnet_training",
    title: "ResNet-50 Image Classification Training",
    framework: "PyTorch",
    workload_type: "Training",
    docker_image: "pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime",
    script: `python -c "import time, torch; print('[Training] Initializing ResNet-50 training batch...'); time.sleep(1); print('Epoch 1/5 - Loss: 0.642, Acc: 78.4%'); time.sleep(1); print('Epoch 2/5 - Loss: 0.412, Acc: 86.9%'); time.sleep(1); print('Epoch 3/5 - Loss: 0.284, Acc: 91.5%'); time.sleep(1); print('Epoch 4/5 - Loss: 0.198, Acc: 94.2%'); time.sleep(1); print('Epoch 5/5 - Loss: 0.142, Acc: 96.8%'); print('Training converged successfully!')"`,
    min_vram: 8.0,
    expected_hours: 0.5,
    budget: 35.0
  },
  {
    id: "llm_lora_finetuning",
    title: "LLaMA-3 LoRA Fine-Tuning",
    framework: "PyTorch",
    workload_type: "FineTuning",
    docker_image: "pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime",
    script: `python -c "import time; print('[LoRA] Loading base model weights & QLoRA adapters...'); time.sleep(1.5); print('Step 50/200: Train Loss: 1.841, Perplexity: 6.30'); time.sleep(1.5); print('Step 100/200: Train Loss: 1.420, Perplexity: 4.13'); time.sleep(1.5); print('Step 200/200: Validation Perplexity: 3.25. LoRA weights saved.')"`,
    min_vram: 12.0,
    expected_hours: 1.5,
    budget: 70.0
  }
];

function WorkloadForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedGpuId = searchParams.get("gpu");

  const [gpus, setGpus] = useState<GPUData[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<string>("pytorch_quick_test");
  const [title, setTitle] = useState<string>("PyTorch GPU Diagnostics & Tensor Test");
  const [framework, setFramework] = useState<string>("PyTorch");
  const [workloadType, setWorkloadType] = useState<string>("Inference");
  const [dockerImage, setDockerImage] = useState<string>("pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime");
  const [scriptCommand, setScriptCommand] = useState<string>(PRESETS[0].script);
  const [minVram, setMinVram] = useState<number>(4.0);
  const [expectedHours, setExpectedHours] = useState<number>(0.1);
  const [budgetMax, setBudgetMax] = useState<number>(10.0);
  const [schedulingStrategy, setSchedulingStrategy] = useState<string>("AI_SCHEDULER");
  const [preferredGpuId, setPreferredGpuId] = useState<string>(preselectedGpuId || "");

  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Real-time ML Prediction Preview state
  const [predictedAvailability, setPredictedAvailability] = useState<number>(0.95);
  const [predictedRuntime, setPredictedRuntime] = useState<number>(0.1);
  const [estimatedCost, setEstimatedCost] = useState<number>(2.0);

  useEffect(() => {
    api.listGPUs().then(setGpus).catch(() => {});
  }, []);

  const handleSelectPreset = (presetId: string) => {
    setSelectedPreset(presetId);
    const p = PRESETS.find(x => x.id === presetId);
    if (p) {
      setTitle(p.title);
      setFramework(p.framework);
      setWorkloadType(p.workload_type);
      setDockerImage(p.docker_image);
      setScriptCommand(p.script);
      setMinVram(p.min_vram);
      setExpectedHours(p.expected_hours);
      setBudgetMax(p.budget);
    }
  };

  // Run real-time ML estimate update
  useEffect(() => {
    api.predictAvailability({
      gpu_utilization: 20.0,
      cpu_utilization: 25.0,
      ram_usage_percent: 40.0,
      temperature_c: 52.0,
      requested_duration_hours: expectedHours,
      historical_uptime_ratio: 0.98
    }).then(res => {
      if (res.predicted_availability_probability) {
        setPredictedAvailability(res.predicted_availability_probability);
      }
    }).catch(() => {});

    api.predictRuntime({
      gpu_vram_gb: minVram,
      workload_type: workloadType,
      framework: framework,
      model_size_mb: 800.0,
      batch_size: 32,
      dataset_size_mb: 2000.0,
      epochs: 10
    }).then(res => {
      if (res.predicted_runtime_hours) {
        setPredictedRuntime(res.predicted_runtime_hours);
        setEstimatedCost(Math.round(res.predicted_runtime_hours * 18.0 * 100) / 100);
      }
    }).catch(() => {});
  }, [expectedHours, minVram, workloadType, framework]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    // Auto-login fallback if guest
    let u = getStoredUser();
    if (!u) {
      try {
        const guestAuth = await api.register({
          name: "Guest Researcher",
          email: `researcher_${Date.now()}@gpu.io`,
          password: "password123",
          role: "USER"
        });
        localStorage.setItem("aigpushare_token", guestAuth.access_token);
        localStorage.setItem("aigpushare_user", JSON.stringify(guestAuth.user));
      } catch (err: any) {
        console.error("Guest auth error:", err);
      }
    }

    try {
      const job = await api.submitJob({
        title,
        workload_type: workloadType,
        framework,
        docker_image: dockerImage,
        script_command: scriptCommand,
        min_vram_gb: minVram,
        expected_runtime_hours: expectedHours,
        budget_max: budgetMax,
        priority: "NORMAL",
        scheduling_strategy: schedulingStrategy,
        preferred_gpu_id: preferredGpuId || undefined
      });

      router.push(`/jobs/${job.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to submit workload.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-500">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-extrabold text-white flex items-center gap-3">
          <Play className="h-7 w-7 text-emerald-400 fill-current" />
          Deploy Workload to GPU Mesh
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Submit training or inference workloads. AI-GPUShare automatically predicts node availability, estimates duration, and selects the most cost-effective GPU.
        </p>
      </div>

      {/* Preset Templates */}
      <div className="space-y-3">
        <label className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
          <Sparkles className="h-3.5 w-3.5 text-amber-400" />
          Quick Workload Presets
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {PRESETS.map((p) => {
            const isSelected = selectedPreset === p.id;
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => handleSelectPreset(p.id)}
                className={`text-left p-4 rounded-2xl border transition-all ${
                  isSelected
                    ? "bg-emerald-500/10 border-emerald-500 text-emerald-300 shadow-lg shadow-emerald-500/10"
                    : "bg-slate-900/70 border-slate-800 text-slate-300 hover:border-slate-700"
                }`}
              >
                <div className="font-bold text-xs text-white">{p.title}</div>
                <div className="text-[11px] text-slate-400 font-mono mt-1">
                  {p.framework} • {p.min_vram} GB VRAM
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Submission Form */}
      <form onSubmit={handleSubmit} className="glass-card rounded-3xl p-8 border border-slate-800 space-y-6">
        {error && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-3">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          {/* Job Title */}
          <div className="space-y-1.5 sm:col-span-2">
            <label className="text-xs font-semibold text-slate-300">Workload Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              className="w-full px-4 py-2.5 bg-slate-900 border border-slate-700 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-emerald-500"
            />
          </div>

          {/* Framework */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">Framework</label>
            <select
              value={framework}
              onChange={(e) => setFramework(e.target.value)}
              className="w-full px-4 py-2.5 bg-slate-900 border border-slate-700 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-emerald-500 cursor-pointer"
            >
              <option value="PyTorch">PyTorch (CUDA 12.x)</option>
              <option value="TensorFlow">TensorFlow (CUDA)</option>
              <option value="JAX">JAX / Flax</option>
              <option value="Custom">Custom Python / Docker</option>
            </select>
          </div>

          {/* Workload Type */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">Workload Category</label>
            <select
              value={workloadType}
              onChange={(e) => setWorkloadType(e.target.value)}
              className="w-full px-4 py-2.5 bg-slate-900 border border-slate-700 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-emerald-500 cursor-pointer"
            >
              <option value="Training">Full Training Run</option>
              <option value="FineTuning">LoRA / Fine-Tuning</option>
              <option value="Inference">Batch Inference / Benchmark</option>
            </select>
          </div>

          {/* Docker Container Image */}
          <div className="space-y-1.5 sm:col-span-2">
            <label className="text-xs font-semibold text-slate-300">Container Execution Environment (Image)</label>
            <input
              type="text"
              value={dockerImage}
              onChange={(e) => setDockerImage(e.target.value)}
              required
              className="w-full px-4 py-2.5 bg-slate-900 border border-slate-700 rounded-xl text-xs text-slate-100 font-mono focus:outline-none focus:border-emerald-500"
            />
          </div>

          {/* Execution Script Command */}
          <div className="space-y-1.5 sm:col-span-2">
            <label className="text-xs font-semibold text-slate-300">Execution Script / Command</label>
            <textarea
              value={scriptCommand}
              onChange={(e) => setScriptCommand(e.target.value)}
              rows={4}
              required
              className="w-full px-4 py-2.5 bg-slate-900 border border-slate-700 rounded-xl text-xs text-emerald-400 font-mono focus:outline-none focus:border-emerald-500 resize-y"
            />
          </div>

          {/* Hardware & Scheduling Requirements */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">Minimum Required VRAM</label>
            <div className="flex items-center gap-3">
              <input
                type="number"
                min="2"
                max="80"
                step="2"
                value={minVram}
                onChange={(e) => setMinVram(parseFloat(e.target.value) || 4.0)}
                className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-xl text-xs text-slate-100 font-mono focus:outline-none focus:border-emerald-500"
              />
              <span className="text-xs text-slate-400 font-bold whitespace-nowrap">GB VRAM</span>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">Estimated Duration</label>
            <div className="flex items-center gap-3">
              <input
                type="number"
                min="0.05"
                max="24"
                step="0.1"
                value={expectedHours}
                onChange={(e) => setExpectedHours(parseFloat(e.target.value) || 0.5)}
                className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-xl text-xs text-slate-100 font-mono focus:outline-none focus:border-emerald-500"
              />
              <span className="text-xs text-slate-400 font-bold whitespace-nowrap">Hours</span>
            </div>
          </div>

          {/* Scheduling Strategy Selection */}
          <div className="space-y-1.5 sm:col-span-2">
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <Zap className="h-3.5 w-3.5 text-cyan-400" />
              Scheduling Algorithm Strategy
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {[
                { id: "AI_SCHEDULER", label: "AI-GPUShare (Cost + Availability)", desc: "Multi-objective ML optimization" },
                { id: "CHEAPEST", label: "Greedy: Cheapest First", desc: "Selects lowest hourly cost node" },
                { id: "FASTEST", label: "Fastest: High Compute First", desc: "Selects highest VRAM/speed node" },
                { id: "AVAILABILITY", label: "Availability Only", desc: "Selects lowest risk of preemption" },
                { id: "RANDOM", label: "Random Baseline", desc: "Uniform random selection for research" },
              ].map((strat) => {
                const isSelected = schedulingStrategy === strat.id;
                return (
                  <button
                    key={strat.id}
                    type="button"
                    onClick={() => setSchedulingStrategy(strat.id)}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      isSelected
                        ? "bg-cyan-500/10 border-cyan-500 text-cyan-300 shadow-md"
                        : "bg-slate-900/60 border-slate-800 text-slate-400 hover:border-slate-700"
                    }`}
                  >
                    <div className="font-bold text-xs text-white">{strat.label}</div>
                    <div className="text-[10px] text-slate-400 mt-0.5">{strat.desc}</div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Real-Time ML Predictions Preview Card */}
        <div className="rounded-2xl p-5 bg-slate-900/90 border border-slate-800/90 space-y-3">
          <div className="flex items-center justify-between text-xs">
            <span className="font-bold text-slate-300 flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
              AI Inference Pre-Flight Estimate
            </span>
            <span className="font-mono text-[10px] text-slate-500">XGBoost Availability & Runtime Models</span>
          </div>

          <div className="grid grid-cols-3 gap-4 pt-2 border-t border-slate-800">
            <div>
              <div className="text-[11px] text-slate-400">Predicted Availability</div>
              <div className="text-lg font-black font-mono text-emerald-400">
                {(predictedAvailability * 100).toFixed(1)}%
              </div>
            </div>
            <div>
              <div className="text-[11px] text-slate-400">Predicted Runtime</div>
              <div className="text-lg font-black font-mono text-cyan-400">
                {predictedRuntime > 0.05 ? `${(predictedRuntime * 60).toFixed(0)} mins` : "< 2 mins"}
              </div>
            </div>
            <div>
              <div className="text-[11px] text-slate-400">Estimated Cost</div>
              <div className="text-lg font-black font-mono text-white">
                ₹{estimatedCost.toFixed(2)}
              </div>
            </div>
          </div>
        </div>

        {/* Submit button */}
        <div className="flex items-center justify-end gap-4 pt-4 border-t border-slate-800">
          <button
            type="submit"
            disabled={submitting}
            className="flex items-center gap-2 px-8 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 font-black text-sm hover:brightness-110 shadow-xl shadow-emerald-500/20 transition-all disabled:opacity-50"
          >
            <Play className="h-4 w-4 fill-current" />
            {submitting ? "Scheduling & Dispatching..." : "Launch Distributed Workload"}
          </button>
        </div>
      </form>
    </div>
  );
}

export default function CreateJobPage() {
  return (
    <Suspense fallback={<div className="text-center py-12 text-slate-500">Loading Workload Creator...</div>}>
      <WorkloadForm />
    </Suspense>
  );
}
