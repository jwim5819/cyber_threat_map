import os
import redis
import maxminddb
import json
import sys
import threading
import time
import datetime
import collections

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from syslog_receiver import SyslogMonitor
from const import META, COLORS
from utils.logger import mapserver_logger
from country_coordinates import get_country_coordinates


class AttackMapTracker:
    def __init__(self):
        # .env loading
        load_dotenv()

        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(script_dir, "../DB/GeoLite2-City.mmdb")
        self.country_stats_path = os.path.join(script_dir, "../DB/country_stats.json")
        self.attack_stats_path = os.path.join(script_dir, "../DB/attack_stats.json")
        self.event_count = 0
        self.redis_instance = self.connect_redis()
        self.super_dict = {}
        self.flags_dict = {}
        self.stats_list = []
        self.attack_list = []

        # 너무 복잡해지는 것 방지 최대 1분에 70개만 화면에 뿌리기 위함
        self.publish_limit_per_minute = 200
        self.last_minute_reset = time.time()
        
        # 발행 간격 제어 (밀리초)
        self.min_publish_interval = (60 * 1000) / self.publish_limit_per_minute
        self.last_publish_time = time.time() * 1000
        
        # 장비별 카운터 초기화
        self.device_counters = {
            "fw": 0,
            "ips": 0,
            "ddos": 0
        }
        self.total_published_this_minute = 0
        
        # 발행 잠금 (동시성 제어)
        self.publish_lock = threading.Lock()
        
        # 장비별 큐 (실시간 처리용)
        self.device_queues = {
            "fw": collections.deque(maxlen=500),  
            "ips": collections.deque(maxlen=500),
            "ddos": collections.deque(maxlen=500)
        }
        
        # 할당량 설정 (1:1:1)
        self.allocation_ratio = {
            "fw": 1,
            "ips": 1,
            "ddos": 1
        }
        
        # 장비 타입 목록
        self.device_types = ["fw", "ips", "ddos"]
        
        # 발행 스레드 시작
        self.stop_event = threading.Event()
        
        # 이벤트 발행 스레드 시작
        self.publisher_thread = threading.Thread(target=self.publish_events_worker, daemon=True)
        self.publisher_thread.start()
        mapserver_logger.info("Events publisher thread started")
        
        # 통계 발행 스레드 시작
        self.stats_publisher_thread = threading.Thread(target=self.stats_publisher_worker, daemon=True)
        self.stats_publisher_thread.start()
        mapserver_logger.info("Stats publisher thread started")
        
        mapserver_logger.info("AttackMapTracker initialized with publish limit: %d per minute (interval: %.2f ms)", 
                             self.publish_limit_per_minute, self.min_publish_interval)

    def connect_redis(self):
        try:
            if os.getenv("ENV") == "LOCAL":
                mapserver_logger.info("try to connect local redis")
                r = redis.StrictRedis(host="127.0.0.1", port=6379, db=0)
            else:
                mapserver_logger.info("try to connect redis")
                r = redis.StrictRedis(host=os.getenv("REDIS_HOST"), port=6379, db=0)
            mapserver_logger.info("redis connected")
            return r
        except:
            mapserver_logger.error("redis failed")
            return None

    def parse_syslog(self, line):
        """
        syslog 처리하는 callback 함수
        """
        # 총 카운트
        self.event_count += 1

        # GeoIP 정보 조회
        src_ip_clean = self.find_geodata(ip=line["src_ip"])
        dst_ip_clean = self.find_geodata(ip=line["dst_ip"])

        # geodata 누락 시 리턴
        if src_ip_clean is None or dst_ip_clean is None:
            return

        # 장비 타입 확인 및 이벤트 생성
        device_type = self._get_device_type(line)
        event_data = self._create_event_data(line, src_ip_clean, dst_ip_clean, device_type)
        
        # 통계 업데이트
        self._update_statistics(event_data)
        
        # 이벤트 큐에 추가
        self._queue_event(event_data, device_type)

    def _get_device_type(self, line):
        """
        로그 라인에서 장비 타입 추출
        """
        device_type = line.get("separator", "fw")  # 기본값은 fw
        if device_type not in self.device_types:
            device_type = "fw"  # 유효하지 않은 타입은 fw로 처리
        return device_type
    
    def _create_event_data(self, line, src_ip_clean, dst_ip_clean, device_type):
        """
        이벤트 데이터 생성
        """
        event_data = {}
        
        # general
        event_data["event_time"] = line.get("time")
        event_data["event_count"] = self.event_count
        
        # 장비 타입에 따른 색상 설정
        event_data["color"] = COLORS.get(device_type)

        # 국가 이름 가져오기
        src_country = src_ip_clean.get("country")
        dst_country = dst_ip_clean.get("country")
        
        # 소스 IP 좌표 설정
        self._set_source_coordinates(event_data, src_ip_clean, src_country)
        
        # 소스 IP 관련 정보 설정
        event_data["country"] = src_country
        event_data["continent"] = src_ip_clean.get("continent")
        event_data["continent_code"] = src_ip_clean.get("continent_code")
        event_data["iso_code"] = src_ip_clean.get("iso_code")
        event_data["metro_code"] = src_ip_clean.get("metro_code")
        event_data["src_ip"] = line.get("src_ip")
        event_data["src_port"] = line.get("src_port")

        # 목적지 IP 좌표 설정
        self._set_destination_coordinates(event_data, dst_ip_clean, dst_country)
        
        # 목적지 IP 관련 정보 설정
        event_data["dst_country"] = dst_country
        event_data["dst_iso_code"] = dst_ip_clean.get("iso_code")
        event_data["dst_ip"] = line.get("dst_ip")
        event_data["dst_port"] = line.get("dst_port")

        # 공격종류
        event_data["attack_type"] = line.get("attack_type")
        
        return event_data
    
    def _set_source_coordinates(self, event_data, src_ip_clean, src_country):
        """소스 IP 좌표 설정"""
        src_coords = get_country_coordinates(src_country)
        if src_coords:
            # 국가 중심 좌표 사용
            event_data["latitude"] = src_coords[0]
            event_data["longitude"] = src_coords[1]
        else:
            # 기존 IP 좌표 사용 (fallback)
            event_data["latitude"] = src_ip_clean.get("latitude")
            event_data["longitude"] = src_ip_clean.get("longitude")
    
    def _set_destination_coordinates(self, event_data, dst_ip_clean, dst_country):
        """목적지 IP 좌표 설정"""
        dst_coords = get_country_coordinates(dst_country)
        if dst_coords:
            # 국가 중심 좌표 사용
            event_data["dst_lat"] = dst_coords[0]
            event_data["dst_long"] = dst_coords[1]
        else:
            # 기존 IP 좌표 사용 (fallback)
            event_data["dst_lat"] = dst_ip_clean.get("latitude")
            event_data["dst_long"] = dst_ip_clean.get("longitude")
    
    def _update_statistics(self, event_data):
        """통계 데이터 업데이트"""
        # 국가 테이블 데이터 갱신 (모든 로그 기준으로 통계 유지)
        self.track_country_stats(
            country=event_data.get("country"), 
            iso_code=event_data.get("iso_code")
        )

        # 공격 유형 테이블 데이터 갱신 (모든 로그 기준으로 통계 유지)
        self.track_attack_type(attack_type=event_data.get("attack_type"))
        mapserver_logger.info(event_data)
    
    def _queue_event(self, event_data, device_type):
        """이벤트를 큐에 추가"""
        with self.publish_lock:
            self.device_queues[device_type].append(event_data)

    def publish_events_worker(self):
        """별도 스레드에서 실행되는 이벤트 발행 워커"""
        while not self.stop_event.is_set():
            try:
                # 발행 속도 제어
                current_time_ms = time.time() * 1000
                time_since_last_publish = current_time_ms - self.last_publish_time
                
                # 마지막 발행 후 최소 간격이 지나지 않았으면 대기
                if time_since_last_publish < self.min_publish_interval:
                    time.sleep((self.min_publish_interval - time_since_last_publish) / 1000)
                
                # 1분이 지났으면 카운터 초기화
                current_time = time.time()
                if current_time - self.last_minute_reset >= 60:
                    self.reset_minute_counters()
                
                # 현재 분에 발행 한도에 도달했는지 확인
                with self.publish_lock:
                    if self.total_published_this_minute >= self.publish_limit_per_minute:
                        # 다음 분까지 대기 (최대 1초씩)
                        time.sleep(1)
                        continue
                    
                    # 발행 처리
                    self.process_and_publish_event()
                
            except Exception as e:
                mapserver_logger.error(f"Error in publish worker: {str(e)}")
                time.sleep(1)  # 에러 발생 시 잠시 대기

    def process_and_publish_event(self):
        """적절한 이벤트를 선택하여 발행"""
        # 장비별 할당량 계산
        total_ratio = sum(self.allocation_ratio.values())
        device_allocations = {
            d: int(self.publish_limit_per_minute * (self.allocation_ratio[d] / total_ratio))
            for d in self.device_types
        }
        
        # 반올림 오차로 인한 총합 조정
        remaining = self.publish_limit_per_minute - sum(device_allocations.values())
        if remaining > 0:
            device_allocations[self.device_types[0]] += remaining
        
        # 이벤트 발행 로직
        target_device = None
        
        # 할당량이 남아있고 큐에 데이터가 있는 장비 찾기
        devices_with_allocation = [d for d in self.device_types 
                               if self.device_counters[d] < device_allocations[d] 
                               and self.device_queues[d]]
        
        if devices_with_allocation:
            # 가장 할당량이 많이 남은 장비 선택
            target_device = max(devices_with_allocation, 
                               key=lambda d: device_allocations[d] - self.device_counters[d])
        else:
            # 모든 장비가 할당량을 채웠지만 총 발행량이 제한에 도달하지 않은 경우
            devices_with_data = [d for d in self.device_types if self.device_queues[d]]
            if devices_with_data and self.total_published_this_minute < self.publish_limit_per_minute:
                # 데이터가 가장 많은 큐 선택
                target_device = max(devices_with_data, key=lambda d: len(self.device_queues[d]))
        
        # 발행할 장비가 선택되었고 큐에 데이터가 있는 경우
        if target_device and self.device_queues[target_device]:
            event_to_publish = self.device_queues[target_device].popleft()
            # 실제 발행
            self.redis_instance.publish("attack-map-production", event_to_publish)
            
            # 카운터 증가
            self.device_counters[target_device] += 1
            self.total_published_this_minute += 1
            
            # 발행 시간 업데이트
            self.last_publish_time = time.time() * 1000
            
            # 로깅 (10개 단위로)
            if self.total_published_this_minute % 10 == 0 or self.total_published_this_minute == 1:
                mapserver_logger.info(
                    f"Published {self.total_published_this_minute}/{self.publish_limit_per_minute} events. "
                    f"Device counts: {self.device_counters}. "
                    f"Queue sizes: fw={len(self.device_queues['fw'])}, "
                    f"ips={len(self.device_queues['ips'])}, "
                    f"ddos={len(self.device_queues['ddos'])}"
                )
            
            return True
        return False

    def reset_minute_counters(self):
        """분당 카운터 초기화"""
        with self.publish_lock:
            self.last_minute_reset = time.time()
            self.total_published_this_minute = 0
            for device in self.device_types:
                self.device_counters[device] = 0
            
            mapserver_logger.info("Reset minute counters for publishing limit")

    def load_stats(self):
        if os.path.exists(self.country_stats_path):
            with open(self.country_stats_path, "r", encoding="utf-8") as f:
                country_data = json.load(f)
            for entry in country_data:
                # 총 Attack 수 갱신
                if entry["count"] is not None:
                    self.event_count += entry["count"]
            # 국가 카운팅 갱신
            self.stats_list = country_data
        if os.path.exists(self.attack_stats_path):
            with open(self.attack_stats_path, "r", encoding="utf-8") as f:
                attack_data = json.load(f)
            self.attack_list = attack_data

    def publish_stats(self):
        """통계데이터 발행"""
        if self.redis_instance is None:
            mapserver_logger.error("Redis instance is None, cannot publish stats")
            return
        try:
            attack_stats = {
                "source": "attack-stats-production",
                "data": self.attack_list[:3]
            }
            country_stats = {
                "source": "country-stats-production",
                "data": self.stats_list[:5]
            }
            self.redis_instance.publish("attack-map-production", attack_stats)
            self.redis_instance.publish("attack-map-production", country_stats)
            mapserver_logger.debug("Stats published successfully")
        except Exception as e:
            mapserver_logger.error(f"Error publishing stats: {str(e)}")

    def find_geodata(self, ip):
        db_unclean = self.parse_geoip(ip)
        if db_unclean:
            db_clean = self.clean_db(db_unclean)
            return db_clean
        else:
            pass

    def parse_geoip(self, ip):
        try:
            reader = maxminddb.open_database(self.db_path)
            response = reader.get(ip)
            reader.close
            return response
        except FileNotFoundError:
            mapserver_logger.error("DB not found")
            mapserver_logger.error("SHUTTING DOWN")
            exit()
        except ValueError:
            return False

    def clean_db(self, unclean):
        selected = {}
        for tag in META:
            head = None
            if tag["tag"] in unclean:
                head = unclean[tag["tag"]]
                for node in tag["path"]:
                    if node in head:
                        head = head[node]
                    else:
                        head = None
                        break
                selected[tag["lookup"]] = head
        return selected

    def merge_dicts(self, *args):
        super_dict = {}
        for arg in args:
            super_dict.update(arg)
        return super_dict

    def track_country_stats(self, country, iso_code):
        if not os.path.exists(self.country_stats_path):
            open(self.country_stats_path, "w").close()
        country_found = False

        for entry in self.stats_list:
            # 기존 국가 통계 갱신
            if entry["iso_code"] == iso_code:
                entry["count"] += 1
                country_found = True
                break
        # 새로운 국가일 경우 추가
        if not country_found:
            self.stats_list.append(
                {"country": country, "iso_code": iso_code, "count": 1}
            )
        # 정렬
        self.stats_list.sort(key=lambda x: x["count"], reverse=True)
        # 파일에 데이터 저장
        with open(self.country_stats_path, "w", encoding="utf-8") as f:
            json.dump(self.stats_list, f, ensure_ascii=False, indent="\t")
        return

    def track_attack_type(self, attack_type):
        if not os.path.exists(self.attack_stats_path):
            open(self.attack_stats_path, "w").close()
        attack_found = False
        for entry in self.attack_list:
            # 기존 공격유형형 통계 갱신
            if entry["attack_type"] == attack_type:
                entry["count"] += 1
                attack_found = True
                break
        # 새로운 공격유형일일 경우 추가
        if not attack_found:
            self.attack_list.append({"attack_type": attack_type, "count": 1})
        # 정렬
        self.attack_list.sort(key=lambda x: x["count"], reverse=True)
        # 파일에 데이터 저장
        with open(self.attack_stats_path, "w", encoding="utf-8") as f:
            json.dump(self.attack_list, f, ensure_ascii=False, indent="\t")
        return

    def check_permissions(self):
        if os.getuid() != 0:
            mapserver_logger.info("Please run this script as root")
            mapserver_logger.info("SHUTTING DOWN")
            return False
        return True

    def reset_stats(self):
        """통계 데이터 초기화"""
        self.event_count = 0
        self.stats_list = []
        self.attack_list = []

        # 초기화된 빈 데이터 파일 저장
        with open(self.country_stats_path, "w", encoding="utf-8") as f:
            json.dump(self.stats_list, f, ensure_ascii=False, indent="\t")
        with open(self.attack_stats_path, "w", encoding="utf-8") as f:
            json.dump(self.attack_list, f, ensure_ascii=False, indent="\t")

        mapserver_logger.info(
            "Stats reset at %s", datetime.datetime.now().strftime("%Y-%m-%d %H:00:00")
        )

    def schedule_stats_reset(self):
        """자정마다 통계 초기화 스케줄링"""
        now = datetime.datetime.now()
        # 다음 자정 시간 계산
        next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
        # 다음 자정까지 대기할 시간(초)
        wait_seconds = (next_midnight - now).total_seconds()

        # 타이머 설정
        timer = threading.Timer(wait_seconds, self._reset_and_reschedule)
        timer.daemon = True  # 메인 스레드 종료 시 함께 종료되도록 설정
        timer.start()
        mapserver_logger.info(
            "Stats reset scheduled for %s", next_midnight.strftime("%Y-%m-%d 00:00:00")
        )

    def _reset_and_reschedule(self):
        """통계 초기화 후 다음 작업 예약"""
        self.reset_stats()
        self.schedule_stats_reset()  # 다음 정각을 위한 재스케줄링

    def stats_publisher_worker(self):
        """별도 스레드에서 실행되는 통계 발행 워커"""
        mapserver_logger.info("Stats publisher worker thread started")
        
        while not self.stop_event.is_set():
            try:
                # 통계 데이터 발행
                self.publish_stats()
                # 1초 대기
                time.sleep(1)
            except Exception as e:
                mapserver_logger.error(f"Error in stats publisher worker: {str(e)}")
                time.sleep(1)  # 에러 발생 시 잠시 대기

    def run(self):
        self.load_stats()
        self.schedule_stats_reset()

        mapserver_logger.info("RUN data_server")
        if not self.check_permissions():
            exit()

        source_ip = os.getenv("SYSLOG_SOURCE_IP")
        source_port = os.getenv("SYSLOG_SOURCE_PORT")
        monitor = SyslogMonitor(
            source_ip, source_port, print_log=False, callback=self.parse_syslog
        )
        monitor.start_monitoring()

    def stop(self):
        """스레드 종료 및 정리"""
        self.stop_event.set()
        if self.publisher_thread.is_alive():
            self.publisher_thread.join(timeout=2)
        if self.stats_publisher_thread.is_alive():
            self.stats_publisher_thread.join(timeout=2)


def main():
    tracker = AttackMapTracker()
    try:
        tracker.run()
    except KeyboardInterrupt:
        tracker.stop()
        exit()


if __name__ == "__main__":
    main()