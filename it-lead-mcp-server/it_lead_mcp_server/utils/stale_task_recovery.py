"""Requeue tasks orphaned by an IT Lead restart.

Async result polling runs in in-memory threads; a server restart mid-task
leaves the task stuck in a processing status in PostgreSQL forever. On
startup, re-dispatch tasks that have been stale beyond the poll budget.
"""
import time
import threading
from datetime import datetime
from typing import Optional

STALE_STATUSES = ("submitted", "received", "pending_assignment", "assigned",
                  "requirements_collection", "in_progress", "rework_in_progress")
DEFAULT_MAX_AGE_SECONDS = 900  # exceeds the 720s main-path poll budget
DEFAULT_ABANDON_AFTER_SECONDS = 86400  # older than 24h: fail, don't resurrect


def _age_seconds(updated_at) -> Optional[float]:
    if updated_at is None:
        return None
    if isinstance(updated_at, str):
        try:
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "").split(".")[0])
        except ValueError:
            return None
    if not isinstance(updated_at, datetime):
        return None
    now = datetime.now(updated_at.tzinfo) if updated_at.tzinfo else datetime.now()
    return (now - updated_at).total_seconds()


def requeue_stale_tasks(assignment_manager, task_storage,
                        max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
                        abandon_after: int = DEFAULT_ABANDON_AFTER_SECONDS) -> dict:
    abandoned = []
    requeued, skipped, failed = [], [], []
    for status in STALE_STATUSES:
        try:
            tasks = task_storage.get_tasks_by_status(status)
        except Exception as e:
            print(f"⚠️ stale-task recovery: cannot list {status}: {e}")
            continue
        for task in tasks:
            task_id = task.get("task_id")
            age = _age_seconds(task.get("updated_at"))
            if age is None or age < max_age_seconds:
                skipped.append(task_id)
                continue
            if age > abandon_after:
                try:
                    task_storage.update_task_status_only(
                        task_id, "failed", "abandoned: stale beyond recovery window")
                    abandoned.append(task_id)
                    print(f"🗑️ Marked abandoned task {task_id} failed (age={int(age)}s)")
                except Exception as e:
                    print(f"⚠️ Could not abandon {task_id}: {e}")
                continue
            print(f"♻️ Requeuing stale task {task_id} (status={status}, age={int(age)}s)")
            try:
                assignment_manager.assign_and_forward_task(
                    task_id=task_id,
                    task_description=task.get("description", ""),
                    assignee=task.get("assigned_to"),
                    priority=task.get("priority", "medium"),
                    metadata={"requeued_after_restart": True, "source": "stale_task_recovery"},
                )
                requeued.append(task_id)
            except Exception as e:
                print(f"❌ Requeue failed for {task_id}: {e}")
                failed.append(task_id)
    return {"requeued": requeued, "skipped_fresh": skipped, "failed": failed,
            "abandoned": abandoned}


def schedule_startup_recovery(assignment_manager, task_storage,
                              delay_seconds: int = 20,
                              max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS):
    def _run():
        time.sleep(delay_seconds)
        try:
            summary = requeue_stale_tasks(assignment_manager, task_storage, max_age_seconds)
            print(f"♻️ Stale-task recovery done: {len(summary['requeued'])} requeued, "
                  f"{len(summary['skipped_fresh'])} fresh skipped, {len(summary['failed'])} failed, "
                  f"{len(summary['abandoned'])} abandoned")
        except Exception as e:
            print(f"⚠️ Stale-task recovery error: {e}")
    t = threading.Thread(target=_run, name="stale-task-recovery", daemon=True)
    t.start()
    return t
