"""
scheduler.py — Phase 7-A: 시간 기반 자율 스케줄러

APScheduler AsyncIOScheduler를 사용해 cron 기반 태스크를 실행합니다.
스케줄 규칙은 Agent_Workspace/schedules.yaml에 영구 저장합니다.
"""
import asyncio
import uuid
from datetime import datetime
from pathlib import Path

import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

_SCHEDULES_FILE = Path(__file__).resolve().parent.parent / "Agent_Workspace" / "schedules.yaml"


class AgentScheduler:
    def __init__(self, task_runner):
        """
        task_runner: handle_task(user_input: str) -> str 형태의 동기 함수
        스케줄 실행 시 run_in_executor를 통해 블로킹 없이 호출됩니다.
        """
        self.scheduler = AsyncIOScheduler()
        self.task_runner = task_runner
        self._rules: list[dict] = []

    # ── YAML 영속성 ──────────────────────────────────────────────────────────

    def _load_rules(self) -> list[dict]:
        if _SCHEDULES_FILE.exists():
            with _SCHEDULES_FILE.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return data.get("schedules", [])
        return []

    def _save_rules(self):
        _SCHEDULES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with _SCHEDULES_FILE.open("w", encoding="utf-8") as f:
            yaml.dump(
                {"schedules": self._rules},
                f,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            )

    # ── 내부 유틸 ────────────────────────────────────────────────────────────

    def _make_job_func(self, task: str):
        """스케줄러가 실행할 async 래퍼를 반환합니다."""
        task_runner = self.task_runner

        async def _job():
            print(f"[Scheduler] Executing: {task!r}")
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, task_runner, task)
                print(f"[Scheduler] Done: {str(result)[:120]}")
            except Exception as e:
                print(f"[Scheduler] Task failed: {e}")

        return _job

    def _register_job(self, rule: dict):
        try:
            self.scheduler.add_job(
                self._make_job_func(rule["task"]),
                CronTrigger.from_crontab(rule["cron"]),
                id=rule["id"],
                replace_existing=True,
            )
        except Exception as e:
            print(f"[Scheduler] Failed to register job {rule['id']}: {e}")

    # ── 라이프사이클 ─────────────────────────────────────────────────────────

    def start(self):
        """스케줄러 시작 — FastAPI lifespan startup에서 호출합니다."""
        self._rules = self._load_rules()
        for rule in self._rules:
            if rule.get("enabled", True):
                self._register_job(rule)
        self.scheduler.start()
        print(f"[Scheduler] Started with {len(self._rules)} rule(s).")

    def stop(self):
        """스케줄러 종료 — FastAPI lifespan shutdown에서 호출합니다."""
        self.scheduler.shutdown(wait=False)
        print("[Scheduler] Stopped.")

    # ── 공개 CRUD API ────────────────────────────────────────────────────────

    def add_schedule(self, cron: str, task: str) -> dict:
        """새 스케줄을 추가하고 YAML에 저장합니다."""
        rule = {
            "id": str(uuid.uuid4()),
            "cron": cron,
            "task": task,
            "enabled": True,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        self._rules.append(rule)
        self._save_rules()
        self._register_job(rule)
        print(f"[Scheduler] Added: id={rule['id']} cron={cron!r} task={task!r}")
        return rule

    def list_schedules(self) -> list[dict]:
        return list(self._rules)

    def delete_schedule(self, schedule_id: str) -> bool:
        """스케줄을 삭제하고 YAML을 갱신합니다. 존재하면 True 반환."""
        before = len(self._rules)
        self._rules = [r for r in self._rules if r["id"] != schedule_id]
        if len(self._rules) < before:
            self._save_rules()
            try:
                self.scheduler.remove_job(schedule_id)
            except Exception:
                pass
            print(f"[Scheduler] Deleted: id={schedule_id}")
            return True
        return False
