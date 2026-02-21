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



# -----------------------------------------------------------------------------
# 5. Dependency Collection (Robust)
# -----------------------------------------------------------------------------
# Uvicorn/FastAPI 관련 모든 서브모듈/데이터 수집
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = [
    # 수동으로 추가할 hiddenimports (collect_all이 놓칠 수 있는 것들)
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'engineio.async_drivers.asgi', # socket.io 관련
]

# 패키지 통째로 수집
for package in ['uvicorn', 'fastapi', 'starlette', 'websockets', 'anyio', 'h11', 'click', 'bs4', 'chromadb', 'ollama']:
    try:
        tmp_ret = collect_all(package)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception:
        pass

# Agents / Tools 서브모듈 수집
hiddenimports += collect_submodules('agents')
hiddenimports += collect_submodules('tools')

# 기타 라이브러리 (명시적)
hiddenimports += [
    'ollama',
    'apscheduler',
    'watchdog',
    'faster_whisper',
    'pyttsx3',
    'sounddevice',
    'numpy', # often needed by pandas/chroma
]

# ── Analysis ──────────────────────────────────────────────────────────────────

a = Analysis(
    [os.path.join(SPECPATH, 'python_agent', 'main.py')],
    pathex=[_agent_dir],  # 절대 경로 사용
    binaries=binaries,    # collect_all 결과 병합
    datas=datas + [       # collect_all 결과 병합 + 사용자 정의 데이터
        (os.path.join(SPECPATH, 'Agent_Workspace', 'persona.yaml'), 'Agent_Workspace'),
    ],
    hiddenimports=hiddenimports,
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
