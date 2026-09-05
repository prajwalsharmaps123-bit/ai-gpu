"use client";

import { useEffect, useState, useRef } from "react";
import { 
  Terminal, 
  Copy, 
  Check, 
  X, 
  Cpu, 
  Key, 
  Globe, 
  Laptop, 
  Send, 
  Sparkles, 
  ShieldCheck, 
  FolderSync, 
  Zap,
  Radio,
  CornerDownLeft
} from "lucide-react";
import { api, SSHConnectionInfo, WS_BASE } from "@/lib/api";

interface SSHConnectModalProps {
  gpuId: string;
  gpuName: string;
  onClose: () => void;
}

export default function SSHConnectModal({ gpuId, gpuName, onClose }: SSHConnectModalProps) {
  const [activeTab, setActiveTab] = useState<"cli" | "web_terminal" | "vscode" | "tunnel">("cli");
  const [sshInfo, setSshInfo] = useState<SSHConnectionInfo | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  // Web Terminal state
  const [terminalOutput, setTerminalOutput] = useState<string>("");
  const [inputCommand, setInputCommand] = useState<string>("");
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [sessionId] = useState<string>(() => "term_" + Math.random().toString(36).substring(2, 9));
  const wsRef = useRef<WebSocket | null>(null);
  const terminalEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    async function loadInfo() {
      try {
        const data = await api.getGPUSSHInfo(gpuId);
        setSshInfo(data);
      } catch (err) {
        console.error("Failed to load SSH info:", err);
      } finally {
        setLoading(false);
      }
    }
    loadInfo();
  }, [gpuId]);

  // Connect WebSocket when web_terminal tab is activated
  useEffect(() => {
    if (activeTab !== "web_terminal" || !gpuId) return;

    const wsUrl = `${WS_BASE}/ws/ssh/terminal/${gpuId}?session_id=${sessionId}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setTerminalOutput((prev) => prev + "\x1b[32m[Connected to AI-GPUShare Host Gateway]\x1b[0m\r\n");
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "SSH_OUTPUT" && msg.data) {
          setTerminalOutput((prev) => prev + msg.data);
        }
      } catch {
        setTerminalOutput((prev) => prev + event.data);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      setTerminalOutput((prev) => prev + "\r\n\x1b[31m[Host Connection Terminated]\x1b[0m\r\n");
    };

    ws.onerror = (err) => {
      console.error("SSH WS error:", err);
      setIsConnected(false);
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [activeTab, gpuId, sessionId]);

  // Auto-scroll terminal
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [terminalOutput]);

  const copyToClipboard = (text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const handleSendCommand = (cmdToSend?: string) => {
    const cmd = cmdToSend !== undefined ? cmdToSend : inputCommand;
    if (!cmd.trim() && cmdToSend === undefined) return;

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "SSH_INPUT",
        data: cmd + "\r\n"
      }));
      setInputCommand("");
    }
  };

  const stripAnsi = (text: string) => {
    return text.replace(/\x1b\[[0-9;]*[a-zA-Z]/g, "");
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-3xl bg-slate-900 border border-slate-700/80 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="bg-slate-950/90 px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <Terminal className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-white">SSH & Remote Host Access</h3>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  ONLINE
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono">
                Target Node: {gpuName} ({gpuId.slice(0, 8)})
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-800 bg-slate-950/50 px-6 pt-2 gap-2 text-xs font-semibold overflow-x-auto">
          <button
            onClick={() => setActiveTab("cli")}
            className={`pb-3 px-3.5 flex items-center gap-2 border-b-2 transition-all ${
              activeTab === "cli"
                ? "border-emerald-400 text-emerald-300"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Terminal className="h-4 w-4" />
            Direct SSH (CLI)
          </button>

          <button
            onClick={() => setActiveTab("web_terminal")}
            className={`pb-3 px-3.5 flex items-center gap-2 border-b-2 transition-all ${
              activeTab === "web_terminal"
                ? "border-emerald-400 text-emerald-300"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Radio className="h-4 w-4 text-emerald-400 animate-pulse" />
            Interactive Web Shell
          </button>

          <button
            onClick={() => setActiveTab("vscode")}
            className={`pb-3 px-3.5 flex items-center gap-2 border-b-2 transition-all ${
              activeTab === "vscode"
                ? "border-emerald-400 text-emerald-300"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Laptop className="h-4 w-4" />
            VS Code Remote
          </button>

          <button
            onClick={() => setActiveTab("tunnel")}
            className={`pb-3 px-3.5 flex items-center gap-2 border-b-2 transition-all ${
              activeTab === "tunnel"
                ? "border-emerald-400 text-emerald-300"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <FolderSync className="h-4 w-4" />
            Jupyter & Ports
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {loading ? (
            <div className="text-center py-12 text-slate-500 text-sm">
              <Zap className="h-6 w-6 text-emerald-400 animate-spin mx-auto mb-2" />
              Fetching host SSH credentials and gateway route...
            </div>
          ) : !sshInfo ? (
            <div className="text-center py-8 text-rose-400 text-sm">
              Failed to load SSH configuration.
            </div>
          ) : (
            <>
              {/* TAB 1: CLI Direct SSH */}
              {activeTab === "cli" && (
                <div className="space-y-5 animate-in fade-in duration-200">
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
                      <span>1-Click Terminal Connection Command</span>
                      <span className="text-[11px] text-slate-500">Run in PowerShell / Bash / CMD</span>
                    </label>
                    <div className="flex items-center justify-between bg-slate-950 px-4 py-3 rounded-2xl border border-slate-800 font-mono text-xs text-emerald-400">
                      <code>{sshInfo.ssh_cli_command}</code>
                      <button
                        onClick={() => copyToClipboard(sshInfo.ssh_cli_command, "cli")}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-semibold transition-colors"
                      >
                        {copiedField === "cli" ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                        {copiedField === "cli" ? "Copied!" : "Copy"}
                      </button>
                    </div>
                  </div>

                  {/* Credentials Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800 space-y-1">
                      <div className="text-[10px] text-slate-500 uppercase font-semibold">Host / IP</div>
                      <div className="text-xs font-mono font-bold text-slate-200 truncate">{sshInfo.ssh_host}</div>
                    </div>
                    <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800 space-y-1">
                      <div className="text-[10px] text-slate-500 uppercase font-semibold">Port</div>
                      <div className="text-xs font-mono font-bold text-cyan-300">{sshInfo.ssh_port}</div>
                    </div>
                    <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800 space-y-1">
                      <div className="text-[10px] text-slate-500 uppercase font-semibold">Username</div>
                      <div className="text-xs font-mono font-bold text-amber-300 truncate">{sshInfo.ssh_username}</div>
                    </div>
                    <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800 space-y-1">
                      <div className="text-[10px] text-slate-500 uppercase font-semibold">Password</div>
                      <div className="text-xs font-mono font-bold text-emerald-400 truncate">{sshInfo.ssh_password || "None (Key Auth)"}</div>
                    </div>
                  </div>

                  {/* SCP File Transfer Helper */}
                  <div className="space-y-2 pt-2 border-t border-slate-800/80">
                    <label className="text-xs font-semibold text-slate-300">
                      Copy Files / Models to Host (SCP)
                    </label>
                    <div className="flex items-center justify-between bg-slate-950 px-4 py-2.5 rounded-xl border border-slate-800 font-mono text-xs text-slate-300">
                      <code>{sshInfo.scp_upload_command}</code>
                      <button
                        onClick={() => copyToClipboard(sshInfo.scp_upload_command, "scp")}
                        className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-semibold transition-colors"
                      >
                        {copiedField === "scp" ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                        {copiedField === "scp" ? "Copied!" : "Copy"}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: Interactive Web Terminal */}
              {activeTab === "web_terminal" && (
                <div className="space-y-3 animate-in fade-in duration-200 flex flex-col">
                  {/* Quick Action Chips */}
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[11px] text-slate-500">Quick Commands:</span>
                    <button
                      onClick={() => handleSendCommand("nvidia-smi")}
                      className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-emerald-300 font-mono text-[11px] transition-colors"
                    >
                      nvidia-smi
                    </button>
                    <button
                      onClick={() => handleSendCommand("python --version")}
                      className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 font-mono text-[11px] transition-colors"
                    >
                      python --version
                    </button>
                    <button
                      onClick={() => handleSendCommand("whoami")}
                      className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-amber-300 font-mono text-[11px] transition-colors"
                    >
                      whoami
                    </button>
                    <button
                      onClick={() => handleSendCommand("dir")}
                      className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono text-[11px] transition-colors"
                    >
                      dir / ls
                    </button>
                  </div>

                  {/* Terminal Canvas */}
                  <div className="bg-slate-950 rounded-2xl p-4 border border-slate-800 font-mono text-xs text-emerald-400 h-64 overflow-y-auto space-y-1 shadow-inner selection:bg-emerald-500 selection:text-slate-950">
                    <pre className="whitespace-pre-wrap font-mono leading-relaxed">
                      {stripAnsi(terminalOutput) || "Connecting to remote GPU host shell session...\n"}
                    </pre>
                    <div ref={terminalEndRef} />
                  </div>

                  {/* Terminal Input Bar */}
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      handleSendCommand();
                    }}
                    className="flex items-center gap-2"
                  >
                    <div className="relative flex-1">
                      <input
                        ref={inputRef}
                        type="text"
                        placeholder="Type a command and press Enter (e.g. nvidia-smi)..."
                        value={inputCommand}
                        onChange={(e) => setInputCommand(e.target.value)}
                        className="w-full pl-4 pr-10 py-2.5 bg-slate-950 border border-slate-700 rounded-xl text-xs font-mono text-emerald-300 placeholder-slate-600 focus:outline-none focus:border-emerald-500/60"
                      />
                      <CornerDownLeft className="absolute right-3.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500" />
                    </div>
                    <button
                      type="submit"
                      disabled={!inputCommand.trim()}
                      className="px-4 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 font-bold text-xs flex items-center gap-1.5 transition-all shadow-md shadow-emerald-500/10"
                    >
                      <Send className="h-3.5 w-3.5" />
                      Send
                    </button>
                  </form>
                </div>
              )}

              {/* TAB 3: VS Code Remote SSH */}
              {activeTab === "vscode" && (
                <div className="space-y-4 animate-in fade-in duration-200">
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Attach VS Code to this remote GPU host to edit files, run remote debugging, and leverage CUDA directly within your editor. Add this snippet to your <code className="text-emerald-400 bg-slate-950 px-1.5 py-0.5 rounded">~/.ssh/config</code>:
                  </p>

                  <div className="relative bg-slate-950 p-4 rounded-2xl border border-slate-800 font-mono text-xs text-cyan-300">
                    <pre className="whitespace-pre-wrap">{sshInfo.vscode_config_snippet}</pre>
                    <button
                      onClick={() => copyToClipboard(sshInfo.vscode_config_snippet, "vscode")}
                      className="absolute top-3 right-3 flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-semibold transition-colors"
                    >
                      {copiedField === "vscode" ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                      {copiedField === "vscode" ? "Copied!" : "Copy Snippet"}
                    </button>
                  </div>
                </div>
              )}

              {/* TAB 4: Jupyter Tunneling */}
              {activeTab === "tunnel" && (
                <div className="space-y-4 animate-in fade-in duration-200">
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Forward remote ports (like Jupyter Lab on port 8888 or TensorBoard on 6006) directly to your local browser:
                  </p>

                  <div className="space-y-2">
                    <div className="text-xs font-semibold text-slate-300">Jupyter Lab Port Forwarding (8888)</div>
                    <div className="flex items-center justify-between bg-slate-950 px-4 py-3 rounded-2xl border border-slate-800 font-mono text-xs text-amber-300">
                      <code>{sshInfo.jupyter_tunnel_command}</code>
                      <button
                        onClick={() => copyToClipboard(sshInfo.jupyter_tunnel_command, "jupyter")}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-semibold transition-colors"
                      >
                        {copiedField === "jupyter" ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                        {copiedField === "jupyter" ? "Copied!" : "Copy"}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="bg-slate-950/80 px-6 py-3.5 border-t border-slate-800 flex items-center justify-between text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            <span>End-to-End Encrypted Tunnel</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
