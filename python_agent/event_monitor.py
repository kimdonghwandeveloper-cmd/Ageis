"""
event_monitor.py — Phase 7-B: 파일시스템 이벤트 기반 자율 실행

watchdog으로 Agent_Workspace 하위 경로를 감시합니다.
이벤트 발생 시 asyncio.run_coroutine_threadsafe()로 이벤트 루프에 태스크를 전달합니다.
감시 규칙은 Agent_Workspace/watch_rules.yaml에 영구 저장합니다.
"""
import asyncio
import fnmatch
import uuid
from datetime import datetime
from pathlib import Path

import yaml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

_WATCH_RULES_FILE = Path(__file__).resolve().parent.parent / "Agent_Workspace" / "watch_rules.yaml"


class _AgentEventHandler(FileSystemEventHandler):
    """watchdog 이벤트 핸들러 — 규칙 매칭 후 asyncio 루프에 태스크 디스패치."""

    def __init__(self, rules: list[dict], task_runner, loop: asyncio.AbstractEventLoop):
        super().__init__()
        self.rules = rules
        self.task_runner = task_runner
        self.loop = loop

    def _dispatch(self, event_type: str, src_path: str):
        path = Path(src_path)
        for rule in self.rules:
            if not rule.get("enabled", True):
                continue
            if rule.get("event") != event_type:
                continue

            watch_path = Path(rule["path"]).resolve()
            try:
                path.relative_to(watch_path)
            except ValueError:
                continue

            if not fnmatch.fnmatch(path.name, rule.get("pattern", "*")):
                continue

            # {file} 플레이스홀더를 실제 경로로 치환
            task = rule["task"].replace("{file}", str(path))
            print(f"[EventMonitor] Triggered rule={rule['id']} event={event_type} file={path.name!r}")
            asyncio.run_coroutine_threadsafe(self._run(task), self.loop)

    async def _run(self, task: str):
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.task_runner, task)
            print(f"[EventMonitor] Done: {str(result)[:120]}")
        except Exception as e:
            print(f"[EventMonitor] Task failed: {e}")

    def on_created(self, event):
        if not event.is_directory:
            self._dispatch("created", event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._dispatch("modified", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._dispatch("deleted", event.src_path)


class EventMonitor:
    def __init__(self, task_runner):
        """
        task_runner: handle_task(user_input: str) -> str 형태의 동기 함수
        """
        self.task_runner = task_runner
        self._rules: list[dict] = []
        self._observer: Observer | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    # ── YAML 영속성 ──────────────────────────────────────────────────────────

    def _load_rules(self) -> list[dict]:
        if _WATCH_RULES_FILE.exists():
            with _WATCH_RULES_FILE.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return data.get("watches", [])
        return []

    def _save_rules(self):
        _WATCH_RULES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with _WATCH_RULES_FILE.open("w", encoding="utf-8") as f:
            yaml.dump(
                {"watches": self._rules},
                f,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            )

    # ── Observer 관리 ─────────────────────────────────────────────────────────

    def _restart_observer(self):
        """Observer를 재시작하여 최신 규칙을 반영합니다."""
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join()

        self._observer = Observer()
        handler = _AgentEventHandler(self._rules, self.task_runner, self._loop)

        watched: set[str] = set()
        for rule in self._rules:
            if not rule.get("enabled", True):
                continue
            watch_path = Path(rule["path"])
            watch_path.mkdir(parents=True, exist_ok=True)
            resolved = str(watch_path.resolve())
            if resolved not in watched:
                self._observer.schedule(handler, resolved, recursive=True)
                watched.add(resolved)

        self._observer.start()

    # ── 라이프사이클 ─────────────────────────────────────────────────────────

    def start(self, loop: asyncio.AbstractEventLoop):
        """감시 시작 — FastAPI lifespan startup에서 호출합니다."""
        self._loop = loop
        self._rules = self._load_rules()
        self._restart_observer()
        print(f"[EventMonitor] Started with {len(self._rules)} rule(s).")

    def stop(self):
        """감시 종료 — FastAPI lifespan shutdown에서 호출합니다."""
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join()
        print("[EventMonitor] Stopped.")

    # ── 공개 CRUD API ────────────────────────────────────────────────────────

    def add_watch(self, path: str, pattern: str, event: str, task: str) -> dict:
        """감시 규칙을 추가하고 YAML에 저장합니다."""
        rule = {
            "id": str(uuid.uuid4()),
            "path": str(Path(path)),
            "pattern": pattern,
            "event": event,      # "created" | "modified" | "deleted"
            "task": task,
            "enabled": True,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        self._rules.append(rule)
        self._save_rules()
        if self._loop:
            self._restart_observer()
        print(f"[EventMonitor] Added watch: {path!r} {pattern!r} on {event}")
        return rule

    def list_watches(self) -> list[dict]:
        return list(self._rules)

    def delete_watch(self, watch_id: str) -> bool:
        """감시 규칙을 삭제하고 YAML을 갱신합니다. 존재하면 True 반환."""
        before = len(self._rules)
        self._rules = [r for r in self._rules if r["id"] != watch_id]
        if len(self._rules) < before:
            self._save_rules()
            if self._loop:
                self._restart_observer()
            print(f"[EventMonitor] Deleted watch: id={watch_id}")
            return True
        return False
