from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.style import Style
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style as PromptStyle
from prompt_toolkit.history import FileHistory
import os

# Rich Console 초기화
console = Console()

# Prompt Toolkit 스타일 설정
prompt_style = PromptStyle.from_dict({
    'prompt': '#00aa00 bold',  # 녹색, 굵게
})

def print_banner():
    """시작 배너 출력"""
    banner_text = Text("Ageis Agent", style="bold cyan")
    banner_text.append("\nPhase 4: Expansion & UX", style="dim white")
    
    console.print(Panel(
        banner_text,
        title="🤖 System Online",
        subtitle="Type '/quit' to exit",
        border_style="cyan",
        padding=(1, 2)
    ))

def print_agent_response(response: str):
    """에이전트 응답을 예쁜 패널로 출력"""
    # 마크다운 렌더링 지원
    md_response = Markdown(response)
    
    console.print(Panel(
        md_response,
        title="[bold magenta]Ageis[/bold magenta]",
        border_style="magenta",
        padding=(1, 1)
    ))

def print_system_message(message: str, style: str = "dim"):
    """시스템 메시지 출력 (로그 등)"""
    console.print(f"[{style}]{message}[/{style}]")

def cli_main(agent):
    """CLI 대시보드 메인 루프"""
    print_banner()
    
    # 명령어 히스토리 파일 (재시작해도 기록 유지)
    history_file = os.path.expanduser("~/.ageis_history")
    session = PromptSession(history=FileHistory(history_file))

    from router import classify_intent
    from core_logic import handle_chat, handle_task

    while True:
        try:
            # 1. 사용자 입력 (Rich Prompt 사용)
            user_input = session.prompt([('class:prompt', 'You: ')], style=prompt_style).strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ("/quit", "/exit"):
                console.print("[yellow]System shutting down... Goodbye.[/yellow]")
                break
            
            # 2. 에이전트 처리 (Spinner 표시)
            with console.status("[bold green]Thinking...[/bold green]", spinner="dots"):
                # 의도 분류
                intent = classify_intent(user_input)
                # print_system_message(f"Detected Intent: {intent}", style="blue")
                
                # 라우팅 및 실행
                if intent == "CHAT":
                    response = handle_chat(user_input)
                elif intent in ["FILE", "WEB", "TASK"]:
                    # 복합 작업은 내부 로그가 많으므로, ReAct의 print 출력이 Spinner와 겹치지 않게 주의 필요
                    # 여기서는 일단 실행 (ReAct 내부 print는 콘솔에 직접 찍힘)
                    response = handle_task(user_input)
                elif intent == "PERSONA":
                    response = "persona.yaml 파일을 직접 수정한 후 재시작해 주세요."
                else:
                    response = handle_chat(user_input)

            # 3. 결과 출력
            print_agent_response(response)
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted.[/yellow]")
            break
        except Exception as e:
            console.print(Panel(f"Error: {e}", title="[bold red]System Error[/bold red]", border_style="red"))
