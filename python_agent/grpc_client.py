"""
grpc_client.py — Rust 코어 데몬과 통신하는 gRPC 클라이언트

역할: Python 에이전트가 Rust 코어 데몬에 요청을 보내는 통합 인터페이스.
모든 파일 I/O와 명령 실행은 이 클라이언트를 통해 Rust 게이트웨이를 경유한다.
직접 os.open(), subprocess.run() 등을 호출하지 않고 반드시 이 모듈을 사용한다.

사용 예:
    client = AgentGrpcClient("localhost:50051")
    content = client.read_file("Agent_Workspace/test.txt")
"""

import grpc  # gRPC 파이썬 런타임 라이브러리

# protoc가 자동 생성한 파일들 (generate_proto.py 실행 후 존재)
import agent_pb2       # 메시지 클래스 (FileRequest, ChatMessage 등)
import agent_pb2_grpc  # gRPC 스텁 클래스 (AgentBrokerStub)


class AgentGrpcClient:
    """Rust 코어 데몬에 연결하는 gRPC 클라이언트 래퍼"""

    def __init__(self, server_address: str = "localhost:50051"):
        """
        클라이언트 초기화 및 gRPC 채널 연결

        Args:
            server_address: Rust gRPC 서버 주소 (기본값: localhost:50051)
        """
        # insecure_channel: TLS 없이 평문 통신 (로컬 전용이므로 OK)
        # 프로덕션에서는 secure_channel + 인증서 사용 필요
        self.channel = grpc.insecure_channel(server_address)
        # AgentBrokerStub: proto에서 정의한 서비스의 클라이언트 측 프록시
        # 이 stub의 메서드를 호출하면 네트워크를 통해 Rust 서버에 RPC 요청이 전송된다
        self.stub = agent_pb2_grpc.AgentBrokerStub(self.channel)

    def read_file(self, path: str) -> str:
        """
        Rust 샌드박스를 통해 파일을 읽는다.

        Args:
            path: 읽을 파일 경로 (Agent_Workspace 기준)

        Returns:
            파일 내용 문자열 (거부 시 "ERROR: ..." 형태)
        """
        # FileRequest 메시지 생성 후 RPC 호출
        request = agent_pb2.FileRequest(path=path)
        response = self.stub.RequestFileRead(request)

        # 샌드박스 검증 결과 확인
        if response.allowed:
            # 바이트 → UTF-8 문자열 디코딩
            return response.content.decode("utf-8")
        # 거부된 경우 에러 메시지 반환
        return f"ERROR: {response.error}"

    def write_file(self, path: str, content: str) -> dict:
        """
        Rust 샌드박스를 통해 파일을 쓴다.

        Args:
            path: 쓸 파일 경로 (Agent_Workspace 기준)
            content: 기록할 텍스트 내용

        Returns:
            {"success": bool, "message": str} 결과 딕셔너리
        """
        # 문자열을 UTF-8 바이트로 인코딩하여 전송
        request = agent_pb2.FileWriteRequest(
            path=path,
            content=content.encode("utf-8"),
        )
        response = self.stub.RequestFileWrite(request)
        # 응답을 Python 딕셔너리로 변환하여 반환
        return {"success": response.success, "message": response.message}

    def execute_command(self, command: str, args: list[str] = None) -> dict:
        """
        Rust를 통해 시스템 명령어를 실행한다. (화이트리스트 기반)

        Args:
            command: 실행할 명령어 이름 (예: "echo", "ls")
            args: 명령어 인자 리스트 (예: ["-la", "/tmp"])

        Returns:
            {"exit_code": int, "stdout": str, "stderr": str} 결과 딕셔너리
        """
        # args가 None이면 빈 리스트로 초기화
        if args is None:
            args = []
        request = agent_pb2.CommandRequest(command=command, args=args)
        response = self.stub.ExecuteCommand(request)
        return {
            "exit_code": response.exit_code,
            "stdout": response.stdout,
            "stderr": response.stderr,
        }

    def close(self):
        """gRPC 채널을 명시적으로 닫는다. (리소스 정리)"""
        self.channel.close()

    # with 문을 사용할 수 있도록 컨텍스트 매니저 프로토콜 구현
    def __enter__(self):
        """with AgentGrpcClient() as client: 형태 지원"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """with 블록 종료 시 자동으로 채널 닫기"""
        self.close()
