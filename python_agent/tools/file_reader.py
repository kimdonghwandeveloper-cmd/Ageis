import os
import platform
from pathlib import Path


# ── 시스템 경로 차단 목록 ────────────────────────────────────────────────────

_BLOCKED_WINDOWS = [
    "c:\\windows",
    "c:\\program files",
    "c:\\program files (x86)",
    "c:\\programdata\\microsoft",
]

_BLOCKED_UNIX = [
    "/etc", "/usr", "/bin", "/sbin",
    "/sys", "/proc", "/dev", "/boot", "/lib",
]


def _is_system_path(path: Path) -> bool:
    """OS 핵심 시스템 경로인지 확인합니다."""
    p = str(path).lower().replace("/", "\\") if platform.system() == "Windows" else str(path)
    blocked = _BLOCKED_WINDOWS if platform.system() == "Windows" else _BLOCKED_UNIX
    return any(p.startswith(b) for b in blocked)


def _resolve(requested_path: str) -> tuple:
    """
    요청 경로를 절대 경로로 변환하고 접근 허용 여부를 검증합니다.

    허용: 사용자 파일시스템 전체 (시스템 경로 제외)
    차단: OS 시스템 경로 (C:\\Windows, /etc 등)

    반환: (Path | None, 거부 사유 str)
    """
    raw = Path(requested_path)

    if raw.is_absolute():
        target = raw.resolve()
    else:
        # 상대 경로는 사용자 홈 디렉토리 기준으로 해석
        target = (Path.home() / raw).resolve()

    if _is_system_path(target):
        return None, f"DENIED: '{target}'은 보호된 시스템 경로입니다."

    return target, ""


# ── 도구 함수 ─────────────────────────────────────────────────────────────────

def read_file_tool(args: dict) -> str:
    """
    사용자 파일시스템의 파일을 읽고 내용을 반환합니다.
    시스템 경로(C:\\Windows, /etc 등)는 접근이 차단됩니다.

    Args:
        args: {"path": "파일 경로 (절대 경로 또는 홈 디렉토리 기준 상대 경로)"}

    예시:
        {"path": "C:/Users/karl3/Documents/report.pdf"}
        {"path": "Downloads/resume.pdf"}
    """
    path_str = args.get("path", "")
    if not path_str:
        return "ERROR: 'path' 인수가 필요합니다."

    target, reason = _resolve(path_str)
    if target is None:
        return f"ERROR: {reason}"

    if not target.exists():
        return f"ERROR: 파일을 찾을 수 없습니다 — '{target}'"
    if not target.is_file():
        return f"ERROR: 파일이 아닙니다 (디렉토리?) — '{target}'"

    try:
        text = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            text = target.read_text(encoding="cp949")  # Windows 한국어 인코딩 폴백
        except Exception as e:
            return f"ERROR: 파일 읽기 실패 (바이너리 파일?) — {e}"
    except Exception as e:
        return f"ERROR: 파일 읽기 실패 — {e}"

    # 토큰 과부하 방지: 10000자 초과 시 앞부분만 반환
    if len(text) > 10000:
        return text[:10000] + f"\n\n... (파일이 너무 큽니다. 앞 10000자만 표시, 전체 {len(text)}자)"
    return text


def write_file_tool(args: dict) -> str:
    """
    사용자 파일시스템에 파일을 씁니다. 중간 디렉토리가 없으면 자동 생성합니다.
    시스템 경로(C:\\Windows, /etc 등)에는 쓰기가 차단됩니다.

    Args:
        args: {"path": "파일 경로", "content": "저장할 내용"}

    예시:
        {"path": "C:/Users/karl3/Documents/summary.txt", "content": "요약 내용"}
        {"path": "Desktop/memo.txt", "content": "메모"}
    """
    path_str = args.get("path", "")
    content = args.get("content", "")

    if not path_str:
        return "ERROR: 'path' 인수가 필요합니다."
    if content is None:
        return "ERROR: 'content' 인수가 필요합니다."

    target, reason = _resolve(path_str)
    if target is None:
        return f"ERROR: {reason}"

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"SUCCESS: '{target}'에 저장했습니다."
    except Exception as e:
        return f"ERROR: 파일 쓰기 실패 — {e}"


def list_dir_tool(args: dict) -> str:
    """
    디렉토리 내 파일 목록을 반환합니다.

    Args:
        args: {"path": "디렉토리 경로", "pattern": "*.txt (선택사항)"}

    예시:
        {"path": "C:/Users/karl3/Documents"}
        {"path": "Downloads", "pattern": "*.pdf"}
    """
    path_str = args.get("path", "")
    pattern = args.get("pattern", "*")

    if not path_str:
        return "ERROR: 'path' 인수가 필요합니다."

    target, reason = _resolve(path_str)
    if target is None:
        return f"ERROR: {reason}"

    if not target.exists():
        return f"ERROR: 경로를 찾을 수 없습니다 — '{target}'"
    if not target.is_dir():
        return f"ERROR: 디렉토리가 아닙니다 — '{target}'"

    try:
        entries = sorted(target.glob(pattern))
        if not entries:
            return f"'{target}' 디렉토리가 비어 있습니다 (패턴: {pattern})"

        lines = [f"📁 {target}", ""]
        for entry in entries[:200]:  # 최대 200개
            icon = "📁" if entry.is_dir() else "📄"
            size = f"  ({entry.stat().st_size:,} bytes)" if entry.is_file() else ""
            lines.append(f"  {icon} {entry.name}{size}")
        if len(entries) > 200:
            lines.append(f"  ... 외 {len(entries) - 200}개")
        return "\n".join(lines)
    except Exception as e:
        return f"ERROR: 디렉토리 목록 조회 실패 — {e}"
