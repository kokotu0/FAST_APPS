import inspect
import logging

def dprint(*args):
    """디버그용 print 함수"""
    current_frame = inspect.currentframe()
    if current_frame and current_frame.f_back:
        frame = current_frame.f_back
        log_message = f"[{frame.f_code.co_filename}:{frame.f_lineno}] {'\n'.join(map(str, args))}"
        import pprint
        # 터미널에 출력 - 색상과 스타일 적용
        print("\033[1;36m" + "DEBUG" + "\033[0m", "\033[1;33m" + log_message + "\033[0m")
        # # 로그 파일에 저장
        # with open("debug.log", "a", encoding="utf-8") as f:
        #     f.write(f"{log_message}\n")
    else:
        print("디버그 정보를 출력할 수 없습니다.")

# 사용 예시
logger = logging.getLogger(__name__)
