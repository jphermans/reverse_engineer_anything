"""Tool inventory for the leanrea method, grouped by target category.

The inventory mirrors the leanrea router: basic identification, native
binaries, Electron/JS, mobile, firmware, WASM, data/network, Go/Rust/.NET
and decompilers. Availability is checked with shutil.which at call time so
the result always reflects the current container.
"""

import shutil

CATEGORIES = [
    ("basic", "Basis", [
        ("file", "Bestandstype en magic bytes bepalen: startpunt van de router", "apt-get install file"),
        ("strings", "Strings lezen zonder grote of minified bestanden te openen", "apt-get install binutils"),
        ("xxd", "Hex-dumps en magic bytes inspecteren", "apt-get install xxd"),
    ]),
    ("native", "Native binaries (Mach-O/ELF/PE)", [
        ("nm", "Exports (nm -gU) en imports (nm -u): de capability-map", "apt-get install binutils"),
        ("readelf", "ELF-headers, dynamic secties en NEEDED-libraries", "apt-get install binutils"),
        ("objdump", "Disassembleren (objdump -d -M intel)", "apt-get install binutils"),
        ("llvm-objdump", "Disassembleren met bredere architectuurondersteuning", "apt-get install llvm"),
        ("lldb", "Runtime-analyse van draaiende processen", "apt-get install lldb"),
    ]),
    ("electron", "Electron en JavaScript", [
        ("node", "JS-analyse en npx-tooling draaien", "apt-get install nodejs npm"),
        ("npx", "app.asar uitpakken: npx -y @electron/asar extract", "apt-get install npm"),
        ("jq", "package.json en source maps lezen", "apt-get install jq"),
        ("prettier", "Minified JS leesbaar maken: npx -y prettier --parser babel", None),
    ]),
    ("mobile", "Mobiel (APK)", [
        ("jadx", "APK decompileren naar Java-bron", "apt-get install jadx"),
        ("apktool", "Resources en AndroidManifest uitpakken", "apt-get install apktool"),
    ]),
    ("firmware", "Firmware", [
        ("binwalk", "Firmware-images scannen en extraheren", "apt-get install binwalk"),
        ("unsquashfs", "SquashFS-images uitpakken", "apt-get install squashfs-tools"),
    ]),
    ("wasm", "WASM", [
        ("wasm2wat", "WASM naar leesbare WAT-tekst", "apt-get install wabt"),
        ("wasm-objdump", "WASM-secties inspecteren", "apt-get install wabt"),
    ]),
    ("data", "Data en netwerk", [
        ("sqlite3", "SQLite lezen in read-only mode: sqlite3 'file:C?mode=ro'", "apt-get install sqlite3"),
        ("tshark", "pcap-analyse: gesprekken, DNS, TLS SNI", "apt-get install tshark"),
    ]),
    ("compilers", "Go, Rust en .NET", [
        ("go", "go version -m: toolchain, module en deps in één call", "apt-get install golang"),
        ("cargo", "cargo audit bin: Rust-dependencies", "apt-get install cargo"),
        ("ilspycmd", ".NET-assemblies decompileren", "dotnet tool install -g ilspycmd"),
    ]),
    ("decompilers", "Decompilers", [
        ("r2", "radare2: r2 -qc 'aaa; pdc @ sym.X' voor pseudocode", "apt-get install radare2"),
        ("analyzeHeadless", "Ghidra headless decompilatie", "Ghidra-release downloaden en uitpakken"),
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