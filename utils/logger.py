# logger.py - 로깅 설정 모듈
import logging

def setup_logger(log_dir=None):
    # 로거 생성
    mapserver_logger = logging.getLogger("mapserver")

    # 로거가 이미 설정되어 있지 않은 경우에만 설정
    if not mapserver_logger.handlers:
        # 로거 레벨 설정
        mapserver_logger.setLevel(logging.INFO)
        mapserver_logger.propagate = False  # 상위 로거로 전파 방지

        # 포맷터 설정 - 타임스탬프, 로그 레벨, 메시지 포함
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # 콘솔 핸들러 설정
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        mapserver_logger.addHandler(console_handler)

    return mapserver_logger


mapserver_logger = setup_logger(log_dir=None)