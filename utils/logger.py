# logger.py - 로깅 설정 모듈
import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logger(log_dir=None):
    """
    애플리케이션 로거를 설정합니다.
    
    Args:
        log_dir (str, optional): 로그 파일 저장 디렉토리. 기본값은 None으로 파일 로깅하지 않음.
        
    Returns:
        logging.Logger: 설정된 로거 인스턴스
    """
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
        
        # 파일 로깅 설정 (선택적)
        if log_dir:
            # 로그 디렉토리가 없으면 생성
            os.makedirs(log_dir, exist_ok=True)
            
            # 로테이팅 파일 핸들러 설정 (10MB 크기, 최대 5개 파일)
            log_file_path = os.path.join(log_dir, "mapserver.log")
            file_handler = RotatingFileHandler(
                log_file_path, 
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            mapserver_logger.addHandler(file_handler)
            
            mapserver_logger.info(f"File logging enabled: {log_file_path}")

    return mapserver_logger


# 기본 로그 디렉토리 설정 (현재 디렉토리의 logs 폴더)
default_log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")

# 로거 인스턴스 생성
mapserver_logger = setup_logger(log_dir=default_log_dir)