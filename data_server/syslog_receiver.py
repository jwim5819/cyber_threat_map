# syslog_receiver.py 파일 수정
import os
import re
import json
import logging
from scapy.all import sniff, IP, TCP, Raw
from dotenv import load_dotenv
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import mapserver_logger

# .env 로딩
load_dotenv()

class SyslogMonitor:
    """
    시스로그 모니터링 클래스
    특정 IP와 포트에서 들어오는 시스로그 메시지를 처리합니다.
    """
    def __init__(self, source_ip, source_port, print_log=False, callback=None):
        """
        초기화 함수
        
        Args:
            source_ip (str): 소스 IP 주소
            source_port (int/str): 소스 포트 번호
            print_log (bool): 로그 출력 여부
            callback (function): 로그 처리 콜백 함수
        """
        self.source_ip = source_ip
        self.source_port = int(source_port)
        self.print_log = print_log
        self.callback = callback  # 콜백 함수 추가
        mapserver_logger.info(f"SyslogMonitor initialized for {source_ip}:{source_port}")
        
    def start_monitoring(self):
        """시스로그 모니터링 시작"""
        filter_rule = f"port {self.source_port} and src host {self.source_ip}"
        mapserver_logger.info(f"Starting syslog monitoring with filter: {filter_rule}")
        try:
            sniff(filter=filter_rule, prn=self._packet_handler, store=0)
        except Exception as e:
            mapserver_logger.error(f"Error in syslog monitoring: {e}")
        
    def _packet_handler(self, packet):
        """
        패킷 핸들러
        
        Args:
            packet: 수신된 패킷
        """
        try:
            if IP in packet and TCP in packet:
                if packet[TCP].dport == self.source_port or packet[TCP].sport == self.source_port:
                    if Raw in packet:
                        self._parse_payload(packet[Raw].load)
        except Exception as e:
            mapserver_logger.error(f"Error handling packet: {e}")
    
    def _parse_payload(self, raw_payload):
        """
        원시 페이로드 파싱
        
        Args:
            raw_payload: 원시 패킷 데이터
            
        Returns:
            list: 처리된 로그 항목 목록
        """
        try:
            payload = raw_payload.decode('utf-8')
            log_entries = payload.strip().split('\n')
            
            results = []
            for entry in log_entries:
                result = self._process_log_entry(entry)
                if result:
                    results.append(result)
            return results
        
        except Exception as e:
            mapserver_logger.error(f"Error parsing payload: {e}")
            return None

    def _process_log_entry(self, entry):
        """
        로그 항목 처리
        
        Args:
            entry: 로그 항목 문자열
            
        Returns:
            dict: 처리된 로그 객체
        """
        try:
            match = re.match(r'<(\d+)>(.*)', entry)
            if match:
                json_data = match.group(2)
                log_obj = json.loads(json_data)
                return self._handle_log_object(log_obj)
            return None
        except Exception as e:
            mapserver_logger.error(f"Error processing log entry: {e}")
            return None
        
    def _handle_log_object(self, log_obj):
        """
        로그 객체 처리
        
        Args:
            log_obj: 처리된 로그 객체
            
        Returns:
            dict: 처리된 로그 객체
        """
        if self.print_log:
            mapserver_logger.debug(f"Received log: {log_obj}")
        
        # 콜백 함수가 있으면 실행
        try:
            if self.callback and callable(self.callback):
                self.callback(log_obj)
        except Exception as e:
            mapserver_logger.error(f"Error in callback function: {e}")
            
        return log_obj


if __name__ == "__main__":
    source_ip = os.getenv("SYSLOG_SOURCE_IP")
    source_port = os.getenv("SYSLOG_SOURCE_PORT")
    mapserver_logger.info("SyslogMonitor starting as main module")
    
    if source_ip and source_port:
        monitor = SyslogMonitor(source_ip, source_port, print_log=True)
        monitor.start_monitoring()
    else:
        mapserver_logger.error("필수 환경 변수 누락: SYSLOG_SOURCE_IP 또는 SYSLOG_SOURCE_PORT")