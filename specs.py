#!/usr/bin/env python3
import os
import sys
import platform
import subprocess
import re
from shutil import which

def run(cmd):
    """Run a command and return stdout (or '' on failure)."""
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=False)
        return (p.stdout or "").strip()
    except Exception:
        return ""

def bytes_to_gib(n):
    return n / (1024 ** 3)

def get_cpu_info():
    info = {
        "name": None,
        "physical_cores": None,
        "logical_cores": None,
        "arch": platform.machine(),
        "os": f"{platform.system()} {platform.release()}",
    }

    # Core counts (cross-platform)
    try:
        info["logical_cores"] = os.cpu_count()
    except Exception:
        pass

    # CPU brand/model by platform
    system = platform.system()

    if system == "Windows":
        out = run(["wmic", "cpu", "get", "Name,NumberOfCores,NumberOfLogicalProcessors", "/format:list"])
        # Example lines: Name=..., NumberOfCores=..., NumberOfLogicalProcessors=...
        for line in out.splitlines():
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip().lower()
            v = v.strip()
            if k == "name" and v:
                info["name"] = v
            elif k == "numberofcores" and v.isdigit():
                info["physical_cores"] = int(v)
            elif k == "numberoflogicalprocessors" and v.isdigit():
                info["logical_cores"] = int(v)

    elif system == "Darwin":
        name = run(["sysctl", "-n", "machdep.cpu.brand_string"])
        if name:
            info["name"] = name
        pc = run(["sysctl", "-n", "hw.physicalcpu"])
        lc = run(["sysctl", "-n", "hw.logicalcpu"])
        if pc.isdigit():
            info["physical_cores"] = int(pc)
        if lc.isdigit():
            info["logical_cores"] = int(lc)

    else:  # Linux/Unix
        # CPU model
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                txt = f.read()
            m = re.search(r"model name\s*:\s*(.+)", txt)
            if m:
                info["name"] = m.group(1).strip()
        except Exception:
            pass

        # Physical cores (best-effort)
        out = run(["bash", "-lc", "lscpu"])
        # lscpu often has: Core(s) per socket, Socket(s)
        cores_per_socket = None
        sockets = None
        for line in out.splitlines():
            if ":" not in line:
                continue
            k, v = [x.strip() for x in line.split(":", 1)]
            if k.lower().startswith("core(s) per socket") and v.isdigit():
                cores_per_socket = int(v)
            elif k.lower().startswith("socket(s)") and v.isdigit():
                sockets = int(v)
        if cores_per_socket and sockets:
            info["physical_cores"] = cores_per_socket * sockets

    return info

def get_ram_total_bytes():
    # Prefer psutil if present (most reliable)
    try:
        import psutil  # type: ignore
        return int(psutil.virtual_memory().total)
    except Exception:
        pass

    system = platform.system()
    if system == "Windows":
        out = run(["wmic", "computersystem", "get", "TotalPhysicalMemory", "/format:list"])
        for line in out.splitlines():
            if line.lower().startswith("totalphysicalmemory="):
                v = line.split("=", 1)[1].strip()
                if v.isdigit():
                    return int(v)

    elif system == "Darwin":
        out = run(["sysctl", "-n", "hw.memsize"])
        if out.isdigit():
            return int(out)

    else:  # Linux
        try:
            with open("/proc/meminfo", "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        # e.g. MemTotal:       32726528 kB
                        parts = line.split()
                        if len(parts) >= 2 and parts[1].isdigit():
                            kb = int(parts[1])
                            return kb * 1024
        except Exception:
            pass

    return None

def parse_nvidia_smi():
    if not which("nvidia-smi"):
        return []

    # Query name and total memory for each GPU
    out = run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"])
    gpus = []
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2:
            name = parts[0]
            mem = parts[1]  # e.g. "8192 MiB"
            gpus.append({"name": name, "vram": mem})
    return gpus

def parse_windows_gpu():
    # Windows: use wmic path win32_VideoController
    out = run(["wmic", "path", "win32_VideoController", "get", "Name,AdapterRAM", "/format:list"])
    gpus = []
    cur = {}
    for line in out.splitlines():
        line = line.strip()
        if not line:
            if cur.get("name"):
                gpus.append(cur)
            cur = {}
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip().lower()
        v = v.strip()
        if k == "name" and v:
            cur["name"] = v
        elif k == "adapterram" and v.isdigit():
            cur["vram"] = f"{bytes_to_gib(int(v)):.2f} GiB"
    if cur.get("name"):
        gpus.append(cur)
    return gpus

def parse_macos_gpu():
    # macOS: system_profiler SPDisplaysDataType
    out = run(["system_profiler", "SPDisplaysDataType"])
    gpus = []
    if not out:
        return gpus

    # Look for "Chipset Model:" and "VRAM"
    cur_name = None
    cur_vram = None
    for line in out.splitlines():
        line_stripped = line.strip()
        if line_stripped.startswith("Chipset Model:"):
            # Flush previous
            if cur_name:
                gpus.append({"name": cur_name, "vram": cur_vram})
            cur_name = line_stripped.split(":", 1)[1].strip()
            cur_vram = None
        elif line_stripped.startswith("VRAM") or line_stripped.startswith("VRAM (Dynamic, Max):"):
            # "VRAM (Total): 8 GB" or similar
            cur_vram = line_stripped.split(":", 1)[1].strip()

    if cur_name:
        gpus.append({"name": cur_name, "vram": cur_vram})
    return gpus

def parse_linux_gpu():
    gpus = []

    # Try lspci for names
    if which("lspci"):
        out = run(["bash", "-lc", "lspci -nn | egrep -i 'vga|3d|display'"])
        for line in out.splitlines():
            # Example: 01:00.0 VGA compatible controller: NVIDIA Corporation ...
            gpus.append({"name": line.strip(), "vram": None})

    # Try AMD ROCm tool if present (VRAM sometimes available)
    if which("rocm-smi"):
        out = run(["bash", "-lc", "rocm-smi --showproductname --showmeminfo vram"])
        # Keep raw summary; parsing varies by version
        if out:
            gpus.append({"name": "AMD GPU(s) detected via rocm-smi", "vram": "See rocm-smi output"})
            gpus.append({"name": out.replace("\n", " | "), "vram": None})

    # Intel iGPU VRAM is usually shared; not reliably reported on Linux.
    return gpus

def get_gpu_info():
    # Prefer NVIDIA-specific if present (best VRAM accuracy)
    gpus = parse_nvidia_smi()
    if gpus:
        return gpus

    system = platform.system()
    if system == "Windows":
        return parse_windows_gpu()
    elif system == "Darwin":
        return parse_macos_gpu()
    else:
        return parse_linux_gpu()

def main():
    cpu = get_cpu_info()
    ram_bytes = get_ram_total_bytes()
    gpus = get_gpu_info()

    print("=== Hardware Specs ===")
    print(f"OS:   {cpu.get('os')}")
    print(f"Arch: {cpu.get('arch')}")
    print("")
    print("CPU:")
    print(f"  Name:           {cpu.get('name') or 'Unknown'}")
    print(f"  Physical cores: {cpu.get('physical_cores') or 'Unknown'}")
    print(f"  Logical cores:  {cpu.get('logical_cores') or 'Unknown'}")
    print("")
    print("RAM:")
    if ram_bytes is None:
        print("  Total:          Unknown")
    else:
        print(f"  Total:          {bytes_to_gib(ram_bytes):.2f} GiB")
    print("")
    print("GPU:")
    if not gpus:
        print("  No GPU info found (or required tools not installed).")
        print("  Tip: NVIDIA -> install drivers so `nvidia-smi` is available for exact VRAM.")
    else:
        for i, g in enumerate(gpus, 1):
            name = g.get("name") or "Unknown GPU"
            vram = g.get("vram") or "Unknown/Shared"
            print(f"  [{i}] {name}")
            print(f"      VRAM: {vram}")

if __name__ == "__main__":
    main()
