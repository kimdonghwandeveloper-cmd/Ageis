from grpc_client import AgentGrpcClient

def read_file_tool(args: dict) -> str:
    """
    Agent_Workspace 내 파일 읽기 (Rust 샌드박스 통과)
    
    Args:
        args: {"path": "읽을_파일_경로"} 형태의 딕셔너리
    """
    path = args.get("path", "")
    if not path:
        return "ERROR: 'path' argument is required."

    try:
        # 매번 연결을 맺고 끊는 것이 안전함 (장기 실행 시 연결 끊김 방지)
        with AgentGrpcClient() as client:
            return client.read_file(path)
    except Exception as e:
        return f"ERROR: RPC failure - {e}"

def write_file_tool(args: dict) -> str:
    """
    Agent_Workspace 내 파일 쓰기
    
    Args:
        args: {"path": "경로", "content": "내용"}
    """
    path = args.get("path", "")
    content = args.get("content", "")
    
    if not path or content is None:
        return "ERROR: 'path' and 'content' arguments are required."

    try:
        with AgentGrpcClient() as client:
            result = client.write_file(path, content)
            if result['success']:
                return f"SUCCESS: {result['message']}"
            else:
                return f"FAILURE: {result['message']}"
            
    except Exception as e:
        return f"ERROR: RPC failure - {e}"
