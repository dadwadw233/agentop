"""Process monitoring module."""

import re
import psutil
from datetime import datetime
from typing import List, Dict, Optional
from ..core.models import ProcessMetrics, ProcessStatus
from ..core.constants import AGENT_PATTERNS, AgentType


class ProcessMonitor:
    """Monitor system processes for agent tools."""

    def __init__(self):
        """Initialize process monitor."""
        self.patterns = AGENT_PATTERNS
        self._process_cache: Dict[int, psutil.Process] = {}

    def find_agent_processes(self, agent_type: AgentType) -> List[ProcessMetrics]:
        """
        Find all processes for a specific agent type.

        Args:
            agent_type: The type of agent to search for

        Returns:
            List of ProcessMetrics for matching processes
        """
        if agent_type not in self.patterns:
            return []

        pattern_config = self.patterns[agent_type]
        process_names = pattern_config["process_names"]
        cmdline_patterns = pattern_config["cmdline_patterns"]
        min_memory_mb = pattern_config["min_memory_mb"]

        matches = []

        for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time", "status"]):
            try:
                # Get cmdline for pattern matching
                cmdline_list = proc.info.get("cmdline", [])
                cmdline = " ".join(cmdline_list) if cmdline_list else ""

                # Check if process matches by name OR cmdline pattern
                name_match = any(
                    name.lower() in proc.info["name"].lower() for name in process_names
                )
                cmdline_match = self._matches_cmdline_patterns(cmdline, cmdline_patterns)

                # Skip if neither matches
                if not (name_match or cmdline_match):
                    continue

                pid = proc.info.get("pid")
                if pid is None:
                    continue

                cached = self._process_cache.get(pid)
                if cached is None or not cached.is_running():
                    self._process_cache[pid] = proc
                    cached = proc
                    is_new = True
                else:
                    is_new = False

                # Get full process info
                metrics = self._get_process_metrics(cached, is_new)

                # Memory threshold filter
                if metrics.memory_mb < min_memory_mb:
                    continue

                # Add to matches
                matches.append(metrics)

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        self._cleanup_cache()
        return matches

    def _get_process_metrics(self, proc: psutil.Process, is_new: bool) -> ProcessMetrics:
        """
        Extract metrics from a psutil Process.

        Args:
            proc: psutil.Process instance

        Returns:
            ProcessMetrics object
        """
        # Get process info
        with proc.oneshot():
            pid = proc.pid
            name = proc.name()
            cmdline = " ".join(proc.cmdline()) if proc.cmdline() else ""

            # CPU and memory
            if is_new:
                # Prime CPU counters so the next refresh has data.
                proc.cpu_percent(interval=None)
                cpu_percent = 0.0
            else:
                cpu_percent = proc.cpu_percent(interval=None)
            mem_info = proc.memory_info()
            memory_mb = mem_info.rss / (1024 * 1024)
            memory_percent = proc.memory_percent()

            # Threads and status
            num_threads = proc.num_threads()
            create_time = datetime.fromtimestamp(proc.create_time())
            status = self._map_status(proc.status())

        return ProcessMetrics(
            pid=pid,
            name=name,
            cmdline=cmdline,
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            memory_percent=memory_percent,
            num_threads=num_threads,
            create_time=create_time,
            status=status,
        )

    def _cleanup_cache(self) -> None:
        """Remove dead processes from cache."""
        stale = [pid for pid in self._process_cache if not psutil.pid_exists(pid)]
        for pid in stale:
            self._process_cache.pop(pid, None)

    def _matches_cmdline_patterns(self, cmdline: str, patterns: List[str]) -> bool:
        """
        Check if cmdline matches any of the patterns.

        Args:
            cmdline: Command line string
            patterns: List of regex patterns

        Returns:
            True if any pattern matches
        """
        for pattern in patterns:
            if re.search(pattern, cmdline):
                return True
        return False

    def _map_status(self, psutil_status: str) -> ProcessStatus:
        """
        Map psutil status to ProcessStatus enum.

        Args:
            psutil_status: Status string from psutil

        Returns:
            ProcessStatus enum value
        """
        status_map = {
            psutil.STATUS_RUNNING: ProcessStatus.RUNNING,
            psutil.STATUS_SLEEPING: ProcessStatus.SLEEPING,
            psutil.STATUS_DISK_SLEEP: ProcessStatus.SLEEPING,
            psutil.STATUS_IDLE: ProcessStatus.IDLE,
            psutil.STATUS_ZOMBIE: ProcessStatus.ZOMBIE,
            psutil.STATUS_STOPPED: ProcessStatus.STOPPED,
        }
        return status_map.get(psutil_status, ProcessStatus.IDLE)

    def get_process_by_pid(self, pid: int) -> Optional[ProcessMetrics]:
        """
        Get metrics for a specific PID.

        Args:
            pid: Process ID

        Returns:
            ProcessMetrics or None if not found
        """
        try:
            proc = self._process_cache.get(pid)
            if proc is None or not proc.is_running():
                proc = psutil.Process(pid)
                self._process_cache[pid] = proc
                is_new = True
            else:
                is_new = False
            return self._get_process_metrics(proc, is_new)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

    def is_process_alive(self, pid: int) -> bool:
        """
        Check if a process is still alive.

        Args:
            pid: Process ID

        Returns:
            True if process exists
        """
        return psutil.pid_exists(pid)
