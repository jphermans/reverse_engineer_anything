"""Background runner for explicitly approved RE tool installations.

Only one apt job runs at a time (apt holds a global lock anyway). Jobs are
tracked in memory: a replaced pod clears them naturally, and the approved
install state lives on the PVC via tool_state for the restore banner.
Nothing here runs without the API layer having checked user approval.
"""

import subprocess
import threading
import time
import uuid

from usr.plugins.reverse_engineer_anything.helpers import (
    activity,
    installer,
    job_markers,
    tool_state,
)

_jobs_lock = threading.Lock()
_apt_lock = threading.Lock()
_jobs = {}

ENV = {
    "DEBIAN_FRONTEND": "noninteractive",
    "DOTNET_ROOT": "/a0/usr/tools/dotnet",
    "HOME": "/root",
    # dotnet from the calculator work lives on the PVC; keep standard dirs.
    "PATH": "/a0/usr/tools/dotnet:/root/.dotnet/tools:/usr/local/sbin:"
            "/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
}


def _append(job, line):
    job["log"].append(str(line)[:300])
    if len(job["log"]) > 200:
        del job["log"][: len(job["log"]) - 200]


def get_job(job_id=None):
    """Return one job by id, or the latest job when job_id is empty."""
    with _jobs_lock:
        if job_id:
            return _jobs.get(str(job_id))
        if not _jobs:
            return None
        return sorted(_jobs.values(), key=lambda j: j["started"])[-1]


def busy():
    with _jobs_lock:
        return any(j["state"] == "running" for j in _jobs.values())


def start(root, tools, packages, non_apt):
    """Start one install job; returns the job dict or None when busy."""
    with _jobs_lock:
        if busy():
            return None
        steps = installer.build_step_plan(packages, non_apt)
        job = {
            "id": uuid.uuid4().hex[:12],
            "state": "running",
            "tools": list(tools or []),
            "packages": list(packages or []),
            "started": time.time(),
            "finished": 0,
            "error": "",
            "log": [],
            "steps": steps,
            "step_index": 0,
            "step_label": steps[0] if steps else "",
            "step_percent": installer.percent_for_step(0, len(steps)),
        }
        _jobs[job["id"]] = job
    # Persist a running-job marker so a pod replacement can be reported
    # as an interrupted install instead of silent data loss.
    job_markers.mark(root, tools, packages)
    # Sidebar indicator: show the whole job as busy from the first step.
    label = ", ".join(tools or []) or "(nothing)"
    activity.start(root, "tool_install", "Installing: " + label)
    thread = threading.Thread(
        target=_run,
        args=(root, job["id"], job["tools"], job["packages"], non_apt),
        daemon=True,
    )
    thread.start()
    return job


def _set_step(job, index):
    """Advance the phase-true progress (called when a step starts)."""
    steps = job.get("steps") or []
    job["step_index"] = min(index, len(steps))
    job["step_label"] = steps[index] if index < len(steps) else ""
    job["step_percent"] = installer.percent_for_step(index, len(steps))


def _run(root, job_id, tools, packages, non_apt):
    with _apt_lock:
        job = get_job(job_id)
        step = 0
        try:
            if packages:
                _set_step(job, step); step += 1
                _append(job, "$ apt-get update")
                _run_cmd(job, ["apt-get", "update", "-qq"], timeout=600)
                _set_step(job, step); step += 1
                _append(job, "$ apt-get install -y " + " ".join(packages))
                out = _run_cmd(
                    job,
                    ["apt-get", "install", "-y"] + list(packages),
                    timeout=1800,
                )
                _append(job, (out or "").strip().splitlines()[-1] if out else "")
            for tool, cmd in (non_apt or {}).items():
                _set_step(job, step); step += 1
                _append(job, "$ " + cmd)
                _run_cmd(job, cmd.split(), timeout=900)
            _set_step(job, step); step += 1
            for tool in tools:
                tool_state.record(root, "tool", tool)
            job["state"] = "done"
            job["step_percent"] = 100
            job["step_label"] = ""
            label = ", ".join(tools) or "(nothing)"
            activity.finish(root, "tool_install", "Installed: " + label)
            _append(job, "DONE: " + label)
        except Exception as exc:  # subprocess failure or timeout
            job["state"] = "error"
            job["error"] = str(exc)[:300]
            activity.finish(root, "tool_install", str(exc)[:200], ok=False)
            _append(job, "ERROR: " + str(exc)[:200])
        finally:
            job["finished"] = time.time()
            job_markers.clear(root)


def _run_cmd(job, cmd, timeout):
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=ENV,
    )
    for line in (proc.stdout or "").splitlines()[-15:]:
        _append(job, line)
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()
        detail = tail[-1] if tail else "exit code %d" % proc.returncode
        raise RuntimeError("Command failed (%s): %s" % (" ".join(cmd), detail))
    return proc.stdout or ""


def plan_payload(root, tools, runner=None):
    """Build the preflight payload the UI shows before approval."""
    planned = installer.plan(tools)
    est = installer.estimate(planned["packages"], runner=runner)
    return {
        "plan": planned,
        "download_bytes": est["download_bytes"],
        "disk_bytes": est["disk_bytes"],
        "download_human": installer.human_bytes(est["download_bytes"]),
        "disk_human": installer.human_bytes(est["disk_bytes"]),
        "command": (
            "apt-get install -y " + " ".join(planned["packages"])
            if planned["packages"]
            else ""
        ),
    }
