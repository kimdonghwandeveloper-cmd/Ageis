
import sys
import os

# Ensure we can import from python_agent
sys.path.append(os.path.join(os.getcwd(), 'python_agent'))

try:
    from core_logic import handle_society
    
    print(">>> Testing handle_society with '최신 AI 트렌드 조사해줘'...")
    try:
        result = handle_society("최신 AI 트렌드 조사해줘")
        print("\n>>> RESULT:")
        print(result)
    except Exception as e:
        print(f"\n>>> ERROR in handle_society: {e}")
        import traceback
        traceback.print_exc()

except ImportError as e:
    print(f"ImportError: {e}")
    print("sys.path:", sys.path)
except Exception as e:
    print(f"Setup Error: {e}")
