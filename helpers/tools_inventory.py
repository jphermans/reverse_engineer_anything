"""Tool inventory for the leanrea method, grouped by target category.

The inventory mirrors the leanrea router: basic identification, native
binaries, Electron/JS, mobile, firmware, WASM, data/network, Go/Rust/.NET
and decompilers. Availability is checked with shutil.which at call time so
the result always reflects the current container.
"""

import shutil

CATEGORIES = [
    ("basic", "Basic", [
        ("file", "Identify file type and magic bytes: the router entry point", "apt-get install file"),
        ("strings", "Read strings without opening large or minified files", "apt-get install binutils"),
        ("xxd", "Inspect hex dumps and magic bytes", "apt-get install xxd"),
    ]),
    ("native", "Native binaries (Mach-O/ELF/PE)", [
        ("nm", "Exports (nm -gU) and imports (nm -u): the capability map", "apt-get install binutils"),
        ("readelf", "ELF headers, dynamic sections and NEEDED libraries", "apt-get install binutils"),
        ("objdump", "Disassemble (objdump -d -M intel)", "apt-get install binutils"),
        ("llvm-objdump", "Disassemble with wider architecture support", "apt-get install llvm"),
        ("lldb", "Runtime analysis of running processes", "apt-get install lldb"),
    ]),
    ("electron", "Electron en JavaScript", [
        ("node", "Run JS analysis and npx tooling", "apt-get install nodejs npm"),
        ("npx", "app.asar uitpakken: npx -y @electron/asar extract", "apt-get install npm"),
        ("jq", "Read package.json and source maps", "apt-get install jq"),
        ("prettier", "Make minified JS readable: npx -y prettier --parser babel", None),
    ]),
    ("mobile", "Mobile (APK)", [
        ("jadx", "Decompile APK to Java source", "apt-get install jadx"),
        ("apktool", "Extract resources and AndroidManifest", "apt-get install apktool"),
    ]),
    ("firmware", "Firmware", [
        ("binwalk", "Scan and extract firmware images", "apt-get install binwalk"),
        ("unsquashfs", "Extract SquashFS images", "apt-get install squashfs-tools"),
    ]),
    ("wasm", "WASM", [
        ("wasm2wat", "WASM to readable WAT text", "apt-get install wabt"),
        ("wasm-objdump", "Inspect WASM sections", "apt-get install wabt"),
    ]),
    ("data", "Data and network", [
        ("sqlite3", "Read SQLite in read-only mode: sqlite3 'file:C?mode=ro'", "apt-get install sqlite3"),
        ("tshark", "pcap analysis: conversations, DNS, TLS SNI", "apt-get install tshark"),
    ]),
    ("compilers", "Go, Rust and .NET", [
        ("go", "go version -m: toolchain, module and deps in one call", "apt-get install golang"),
        ("cargo", "cargo audit bin: Rust dependencies", "apt-get install cargo"),
        ("ilspycmd", "Decompile .NET assemblies", "dotnet tool install -g ilspycmd"),
    ]),
    ("decompilers", "Decompilers", [
        ("r2", "radare2: r2 -qc 'aaa; pdc @ sym.X' for pseudocode", "apt-get install radare2"),
        ("analyzeHeadless", "Ghidra headless decompilation", "apt-get install ghidra (large download)"),
    ]),
]


def build_inventory() -> dict:
    """Check every tool and return the categorized inventory with a summary."""
    total = 0
    available = 0
    categories = []
    for key, label, tools in CATEGORIES:
        entries = []
        for name, note, hint in tools:
            total += 1
            ok = shutil.which(name) is not None
            if ok:
                available += 1
            entries.append({"name": name, "available": ok, "note": note, "hint": hint})
        categories.append({"key": key, "label": label, "tools": entries})
    missing = [
        entry["name"]
        for cat in categories
        for entry in cat["tools"]
        if not entry["available"]
    ]
    return {
        "categories": categories,
        "summary": {"available": available, "total": total, "missing": missing},
    }