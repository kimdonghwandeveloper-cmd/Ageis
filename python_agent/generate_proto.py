"""
generate_proto.py — Proto 파일에서 Python gRPC 코드를 자동 생성하는 스크립트

역할: proto/agent.proto 파일을 읽어서 2개의 Python 파일을 생성한다.
  - agent_pb2.py       : 메시지 클래스 (FileRequest, FileResponse 등)
  - agent_pb2_grpc.py  : gRPC 스텁/서비스 클래스 (AgentBrokerStub 등)

실행 방법: cd python_agent && uv run python generate_proto.py
"""

from grpc_tools import protoc  # grpcio-tools에 포함된 protoc 파이썬 래퍼
import sys  # 프로그램 종료 코드 제어

# grpc_tools.protoc.main()에 protoc CLI 인자를 직접 전달
# 이 방식으로 시스템에 protoc가 별도 설치되지 않아도 Python 패키지 내장 protoc를 사용할 수 있다
result = protoc.main([
    "grpc_tools.protoc",              # argv[0]: 프로그램 이름 (관례상 지정)
    "--proto_path=../proto",          # .proto 파일을 찾을 디렉토리 경로
    "--python_out=.",                 # _pb2.py (메시지 클래스) 출력 디렉토리
    "--grpc_python_out=.",            # _pb2_grpc.py (gRPC 스텁) 출력 디렉토리
    "../proto/agent.proto",           # 컴파일할 .proto 파일 경로
])

# protoc 실행 결과 확인
if result == 0:
    print("[OK] agent_pb2.py, agent_pb2_grpc.py 생성 완료")
else:
    print(f"[ERROR] protoc 실행 실패 (exit code: {result})")
    sys.exit(result)  # 에러 코드 전파
