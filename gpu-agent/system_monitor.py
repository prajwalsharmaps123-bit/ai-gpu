import psutil
from typing import Dict, Any

class SystemMonitor:
    def __init__(self):
        # Initial sample to prime CPU percent
        psutil.cpu_percent(interval=None)

    def get_system_telemetry(self) -> Dict[str, Any]:
        cpu_pct = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        net = psutil.net_io_counters()

        return {
            "cpu_utilization": float(cpu_pct),
            "ram_used_mb": round(float(mem.used) / (1024 * 1024), 1),
            "ram_total_mb": round(float(mem.total) / (1024 * 1024), 1),
            "ram_percent": float(mem.percent),
            "disk_percent": float(disk.percent),
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv
        }
