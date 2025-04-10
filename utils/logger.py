# logger_config.py
import logging


def setup_logger():
    mapserver_logger = logging.getLogger("mapserver")

    if not mapserver_logger.handlers:
        # 로거 레벨 설정
        mapserver_logger.setLevel(logging.INFO)
        mapserver_logger.propagate = False  # 상위 로거로 전파 방지

        # 핸들러 생성 (콘솔 출력)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 포맷터 설정
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"
        )
        console_handler.setFormatter(formatter)

        # 로거에 핸들러 추가
        mapserver_logger.addHandler(console_handler)

    return mapserver_logger


# 로거 인스턴스 생성
mapserver_logger = setup_logger()
