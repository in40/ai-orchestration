#!/usr/bin/env python3
"""Deployment warden: re-check health of running deployments periodically."""
import os
import subprocess

PSQL = ["psql", "-h", "127.0.0.1", "-U", "postgres", "-d", "mcp_registry", "-tAc"]


def q(sql, params=None):
    return subprocess.run(PSQL + [sql], capture_output=True, text=True,
                          env={**os.environ, "PGPASSWORD": os.environ.get("POSTGRES_PASSWORD", "postgres")})


def main():
    res = q("select task_id, container_id from task_deployments "
            "where status='running' and container_id is not null")
    for line in res.stdout.strip().splitlines():
        if "|" not in line:
            continue
        task_id, container = line.split("|", 1)
        st = subprocess.run(["docker", "inspect", "-f", "{{.State.Status}} {{.RestartCount}}",
                             container.strip()], capture_output=True, text=True)
        state = (st.stdout or "").strip()
        if st.returncode != 0 or "running" not in state:
            print(f"WARDEN: {container} for {task_id} unhealthy ({state or 'gone'})")
            q("update task_deployments set status='unhealthy', stopped_at=now() "
              f"where task_id='{task_id}' and status='running'")
        else:
            parts = state.split()
            if len(parts) > 1 and parts[1] != "0":
                print(f"WARDEN: {container} restarting (count {parts[1]}) for {task_id}")
                q("update task_deployments set status='unhealthy' "
                  f"where task_id='{task_id}' and status='running'")


if __name__ == "__main__":
    main()
