"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Cpu, Server, Activity, BarChart2, ShieldCheck, Wallet, LogOut, User as UserIcon, Plus } from "lucide-react";
import { getStoredUser, clearAuthSession, UserData, api } from "@/lib/api";

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<UserData | null>(null);
  const [onlineCount, setOnlineCount] = useState<number>(1);

  useEffect(() => {
    const u = getStoredUser();
    setUser(u);
    if (u) {
      api.me().then(setUser).catch(() => {});
    }
    // Check cluster health
    api.listGPUs().then((gpus) => {
      const active = gpus.filter(g => g.status === "AVAILABLE" || g.status === "BUSY").length;
      setOnlineCount(active);
    }).catch(() => {});
  }, [pathname]);

  const handleLogout = () => {
    clearAuthSession();
    setUser(null);
    router.push("/login");
  };

  const navLinks = [
    { href: "/", label: "Dashboard", icon: Activity },
    { href: "/marketplace", label: "GPU Marketplace", icon: Cpu },
    { href: "/jobs/create", label: "Deploy Workload", icon: Plus },
    { href: "/provider", label: "Provider Hub", icon: Server },
    { href: "/benchmarks", label: "AI Benchmarks", icon: BarChart2 },
    { href: "/admin", label: "Cluster Health", icon: ShieldCheck },
  ];

  return (
    <header className="sticky top-0 z-50 backdrop-blur-xl bg-slate-950/80 border-b border-slate-800/80 shadow-2xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-cyan-500 p-0.5 shadow-lg shadow-emerald-500/20 group-hover:scale-105 transition-all duration-300">
              <div className="h-full w-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <Cpu className="h-5 w-5 text-emerald-400 group-hover:text-cyan-400 transition-colors" />
              </div>
            </div>
            <div>
              <span className="text-lg font-extrabold bg-gradient-to-r from-emerald-400 via-cyan-300 to-blue-400 bg-clip-text text-transparent">
                AI-GPUShare
              </span>
              <div className="flex items-center gap-1.5 -mt-1">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span className="text-[10px] text-slate-400 font-mono font-medium">Distributed ML Mesh</span>
              </div>
            </div>
          </Link>

          {/* Cluster Status Pill */}
          <div className="hidden lg:flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs">
            <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
            <span className="text-slate-300 font-medium">{onlineCount} GPU{onlineCount !== 1 ? "s" : ""} Online</span>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="hidden md:flex items-center gap-1">
          {navLinks.map((link) => {
            const Icon = link.icon;
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${
                  isActive
                    ? "bg-gradient-to-r from-emerald-500/20 to-cyan-500/20 text-emerald-300 border border-emerald-500/30 shadow-sm"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
                }`}
              >
                <Icon className={`h-4 w-4 ${isActive ? "text-emerald-400" : "text-slate-400"}`} />
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* User / Wallet / Auth */}
        <div className="flex items-center gap-3">
          {user ? (
            <>
              {/* Wallet Pill */}
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900/90 border border-emerald-500/30 text-xs shadow-inner">
                <Wallet className="h-3.5 w-3.5 text-emerald-400" />
                <span className="text-slate-400">Credits:</span>
                <span className="font-bold font-mono text-emerald-300">₹{user.wallet_balance.toFixed(2)}</span>
              </div>

              {/* User Dropdown / Profile */}
              <div className="flex items-center gap-2 pl-2">
                <div className="h-8 w-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-bold text-slate-200">
                  {user.name.charAt(0).toUpperCase()}
                </div>
                <button
                  onClick={handleLogout}
                  title="Log out"
                  className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            </>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                href="/login"
                className="px-3.5 py-1.5 rounded-lg text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-900 transition-colors"
              >
                Sign In
              </Link>
              <Link
                href="/register"
                className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 font-bold hover:brightness-110 shadow-lg shadow-emerald-500/20 transition-all"
              >
                Get Started
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
