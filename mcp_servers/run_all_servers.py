from __future__ import annotations

from multiprocessing import Process
from typing import Callable, List, Tuple

from app.mcp_servers.ic_server import run as run_ic
from app.mcp_servers.ppn_server import run as run_ppn
from app.mcp_servers.of_server import run as run_of

ServerTarget = Tuple[str, Callable[[], None]]

SERVERS: List[ServerTarget] = [
    ("IC", run_ic),
    ("PPN", run_ppn),
    ("OF", run_of),
]


def main() -> None:
    processes: List[Process] = []
    try:
        for name, target in SERVERS:
            proc = Process(target=target, name=f"{name}-server", daemon=True)
            proc.start()
            processes.append(proc)
            print(f"[run_all_servers] Started {name} server (pid={proc.pid})")

        for proc in processes:
            proc.join()
    except KeyboardInterrupt:
        print("Stopping FastMCP servers...")
    finally:
        for proc in processes:
            if proc.is_alive():
                proc.terminate()


if __name__ == "__main__":
    main()

