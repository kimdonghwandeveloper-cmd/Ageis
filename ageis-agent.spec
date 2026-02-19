# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_all

# ── sys.path 설정 ─────────────────────────────────────────────────────────────
# SPECPATH = 이 spec 파일이 있는 디렉터리 (Ageis/)
# collect_submodules('tools'), collect_submodules('agents')가 동작하려면
# python_agent/가 spec 평가 시점에 sys.path에 있어야 함
_agent_dir = os.path.join(SPECPATH, 'python_agent')
if _agent_dir not in sys.path:
    sys.path.insert(0, _agent_dir)

# ── 패키지 수집 ───────────────────────────────────────────────────────────────

# bs4: collect_all로 datas / binaries / hiddenimports 전부 수집
_bs4_datas, _bs4_bins, _bs4_hidden = collect_all('bs4')

# chromadb: config.py가 문자열로 동적 import → 서브모듈 전체 수집 필수
_chroma_hidden = collect_submodules('chromadb')
_chroma_datas  = collect_data_files('chromadb')

# tools / agents: sys.path에 추가된 후에 실행되므로 이제 올바르게 수집됨
_tools_hidden  = collect_submodules('tools')
_agents_hidden = collect_submodules('agents')

# ── Analysis ──────────────────────────────────────────────────────────────────

a = Analysis(
    [os.path.join(SPECPATH, 'python_agent', 'main.py')],
    pathex=[_agent_dir],  # 절대 경로 사용
    binaries=[
        *_bs4_bins,
    ],
    datas=[
        *_bs4_datas,
        *_chroma_datas,
        (os.path.join(SPECPATH, 'Agent_Workspace', 'persona.yaml'), 'Agent_Workspace'),
    ],
    hiddenimports=[
        # ── bs4 (collect_all 결과) ──────────────────────────────
        *_bs4_hidden,

        # ── chromadb (전체 서브모듈) ────────────────────────────
        *_chroma_hidden,

        # ── tools / agents 서브패키지 ───────────────────────────
        *_tools_hidden,
        *_agents_hidden,

        # ── gRPC ────────────────────────────────────────────────
        'grpc',
        'grpc._channel',
        'grpc._interceptor',
        'grpc._utilities',
        'grpc.experimental',

        # ── LLM ─────────────────────────────────────────────────
        'ollama',

        # ── onnxruntime ─────────────────────────────────────────
        'onnxruntime',

        # ── STT ─────────────────────────────────────────────────
        'faster_whisper',
        'ctranslate2',
        'av',

        # ── TTS ─────────────────────────────────────────────────
        'pyttsx3',
        'pyttsx3.drivers',
        'pyttsx3.drivers.sapi5',
        'pyttsx3.drivers.nsss',
        'pyttsx3.drivers.espeak',
        'win32com.client',
        'win32com.server',

        # ── 오디오 ──────────────────────────────────────────────
        'sounddevice',

        # ── 스케줄러 ────────────────────────────────────────────
        'apscheduler',
        'apscheduler.schedulers.asyncio',
        'apscheduler.triggers.cron',
        'apscheduler.triggers.date',
        'apscheduler.triggers.interval',
        'apscheduler.executors.asyncio',
        'apscheduler.executors.pool',
        'tzlocal',

        # ── 파일 감시 ───────────────────────────────────────────
        'watchdog',
        'watchdog.observers',
        'watchdog.observers.winapi',
        'watchdog.observers.inotify',
        'watchdog.observers.fsevents',
        'watchdog.events',

        # ── FastAPI / uvicorn ───────────────────────────────────
        'fastapi',
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.asyncio',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'starlette',
        'starlette.middleware',
        'starlette.middleware.cors',
        'anyio',
        'anyio._backends._asyncio',
        'websockets',
        'multipart',

        # ── YAML / HTTP ─────────────────────────────────────────
        'yaml',
        'httpx',
        'httpcore',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ageis-agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,   # UPX 비활성화: 일부 패키지가 압축 후 손상되는 케이스 방지
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
