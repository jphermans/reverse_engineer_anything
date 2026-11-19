"""On-demand RE tool installation planning (pure logic).

Maps tool names from the inventory to apt packages, validates requests
against a fixed whitelist and estimates download sizes through an
apt-get simulation. Nothing here installs anything: the runtime runner
(tool_install.py) performs real installs only after the user explicitly
approves the plan shown in the UI.
"""

# Inventory tool name -> apt packages.
APT_MAP = {
    "file": ["file"],
    "strings": ["binutils"],
    "xxd": ["xxd"],
    "nm": ["binutils"],
    "readelf": ["binutils"],
    "objdump": ["binutils"],
    "llvm-objdump": ["llvm"],
    "lldb": ["lldb"],
    "node": ["nodejs", "npm"],
    "npx": ["npm"],
    "jq": ["jq"],
    "jadx": ["jadx"],
    "apktool": ["apktool"],
    "binwalk": ["binwalk"],
    "unsquashfs": ["squashfs-tools"],
    "wasm2wat": ["wabt"],
    "wasm-objdump": ["wabt"],
    "sqlite3": ["sqlite3"],
    "tshark": ["tshark"],
    "go": ["golang"],
    "cargo": ["cargo"],
    "r2": ["radare2"],
    "analyzeHeadless": ["ghidra"],
}

# Tools that exist but are not installable through apt.
NON_APT = {
    "ilspycmd": "dotnet tool install -g ilspycmd",
    "prettier": "npm i -g prettier",
}

# Curated bundles (tool names, not packages).
BUNDLES = {
    "essentials": [
        "jadx", "apktool", "binwalk", "r2", "wasm2wat",
        "wasm-objdump", "sqlite3", "tshark", "unsquashfs",
    ],
    "dev": ["node", "npx", "jq"],
    "heavy": ["analyzeHeadless", "lldb", "llvm-objdump", "go"],
}


def bundle_tools(name: str):
    """Return the tool list of a bundle, or None for unknown names."""
    return BUNDLES.get(str(name or "").strip())


def plan(tools) -> dict:
    """Validate a tool request against the whitelist.

    Returns valid tool names, invalid ones, the deduplicated apt package
    set and any non-apt commands. The whitelist is fixed in this module;
    callers can never pass arbitrary package names.
    """
    valid = []
    invalid = []
    for tool in tools or []:
        name = str(tool or "").strip()
        if name in APT_MAP or name in NON_APT:
            if name not in valid:
                valid.append(name)
        elif name:
            invalid.append(name)
    packages = sorted({p for t in valid for p in APT_MAP.get(t, [])})
    non_apt = {t: NON_APT[t] for t in valid if t in NON_APT}
    return {
        "valid": valid,
        "invalid": invalid,
        "packages": packages,
        "non_apt": non_apt,
    }


def _parse_sim_output(text: str):
    """Extract (download_bytes, disk_bytes) from apt-get -s output."""
    import re

    download = 0
    disk = 0
    m = re.search(r"Need to get ([0-9,.]+) ([kMGT]?B) of archives", text)
    if m:
        download = _to_bytes(m.group(1), m.group(2))
    m = re.search(
        r"after this operation, ([0-9,.]+) ([kMGT]?B) of additional disk space",
        text,
    )
    if m:
        disk = _to_bytes(m.group(1), m.group(2))
    return download, disk


FACTORS = {"B": 1, "kB": 10**3, "MB": 10**6, "GB": 10**9, "TB": 10**12}


def _to_bytes(value: str, unit: str) -> int:
    """Parse an apt size like 12.3 kB (en) or 45,6 MB (nl)."""
    value = value.strip()
    if "," in value and "." in value:
        decimal = "," if value.rfind(",") > value.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        value = value.replace(thousands, "").replace(decimal, ".")
    elif "," in value:
        head, _, tail = value.rpartition(",")
        value = head.replace(",", "") + ("." + tail if len(tail) != 3 else tail)
    elif "." in value:
        head, _, tail = value.rpartition(".")
        value = head.replace(".", "") + ("." + tail if len(tail) != 3 else tail)
    return int(float(value) * FACTORS.get(unit, 1))


def _apt_simulate(packages) -> str:
    import subprocess

    cmd = ["apt-get", "install", "-s", "-y"] + list(packages)
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "Package size estimation timed out (45s); "
            "apt is probably busy with another operation. Try again later."
        ) from exc
    return (out.stdout or "") + "\n" + (out.stderr or "")


def estimate(packages, runner=None) -> dict:
    """Estimate download and disk cost via apt-get simulation.

    The runner is injectable so tests never need apt.
    """
    if not packages:
        return {"download_bytes": 0, "disk_bytes": 0}
    text = (runner or _apt_simulate)(list(packages))
    download, disk = _parse_sim_output(text)
    return {"download_bytes": download, "disk_bytes": disk}


def human_bytes(num: float) -> str:
    for unit in ("B", "kB", "MB", "GB", "TB"):
        if abs(num) < 1000 or unit == "TB":
            return ("%.1f %s" if unit != "B" else "%d %s") % (num, unit)
        num /= 1000.0
    return "%.1f TB" % num
