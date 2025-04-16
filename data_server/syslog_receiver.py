# syslog_receiver.py 파일 수정
import os
import re
import json
from scapy.all import sniff, IP, TCP, Raw
from dotenv import load_dotenv

# .env 로딩
load_dotenv()

class SyslogMonitor:
    def __init__(self, source_ip, source_port, print_log=False, callback=None):
        self.source_ip = source_ip
        self.source_port = int(source_port)
        self.print_log = print_log
        self.callback = callback  # 콜백 함수 추가
        
    def start_monitoring(self):
        filter_rule = f"port {self.source_port} and src host {self.source_ip}"
        sniff(filter=filter_rule, prn=self._packet_handler, store=0)
        
    def _packet_handler(self, packet):
        if IP in packet and TCP in packet:
            if packet[TCP].dport == self.source_port or packet[TCP].sport == self.source_port:
                if Raw in packet:
                    self._parse_payload(packet[Raw].load)
    
    def _parse_payload(self, raw_payload):
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
            print(e)
            return None

    def _process_log_entry(self, entry):
        match = re.match(r'<(\d+)>(.*)', entry)
        if match:
            json_data = match.group(2)
            log_obj = json.loads(json_data)
            return self._handle_log_object(log_obj)
        
        
    def _handle_log_object(self, log_obj):
        if self.print_log:
            print(log_obj)
        
        # 콜백 함수가 있으면 실행
        if self.callback and callable(self.callback):
            self.callback(log_obj)
            
        return log_obj


if __name__ == "__main__":
    source_ip = os.getenv("SYSLOG_SOURCE_IP")
    source_port = os.getenv("SYSLOG_SOURCE_PORT")
    print("run")
    
    if source_ip and source_port:
        monitor = SyslogMonitor(source_ip, source_port, print_log=True)
        monitor.start_monitoring()
    else:
        print("변수설정 누락")