import os
import redis
import maxminddb
import json
import sys
import threading
import time
import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from syslog_receiver import SyslogMonitor
from const import META, PORTMAP, COLORS
from utils.logger import mapserver_logger


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
        self.a = 0

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
        mapserver_logger.info(line)

        src_ip_clean = self.find_geodata(ip=line["src_ip"])
        dst_ip_clean = self.find_geodata(ip=line["dst_ip"])

        # geodata 누락 시 리턴
        if src_ip_clean is None or dst_ip_clean is None:
            return

        # general
        self.super_dict["event_time"] = line.get("time")
        self.super_dict["event_count"] = self.event_count
        if line.get("separator") == "ips":
            self.super_dict["color"] = COLORS.get("ips")
        if line.get("separator") == "fw":
            self.super_dict["color"] = COLORS.get("fw")
        if line.get("separator") == "ddos":
            self.super_dict["color"] = COLORS.get("ddos")

        # source IP
        self.super_dict["longitude"] = src_ip_clean.get("longitude")
        self.super_dict["latitude"] = src_ip_clean.get("latitude")
        self.super_dict["country"] = src_ip_clean.get("country")
        self.super_dict["continent"] = src_ip_clean.get("continent")
        self.super_dict["continent_code"] = src_ip_clean.get("continent_code")
        self.super_dict["iso_code"] = src_ip_clean.get("iso_code")
        self.super_dict["metro_code"] = src_ip_clean.get("metro_code")
        self.super_dict["src_ip"] = line.get("src_ip")
        self.super_dict["src_port"] = line.get("src_port")

        # destination IP
        self.super_dict["dst_long"] = dst_ip_clean.get("longitude")
        self.super_dict["dst_lat"] = dst_ip_clean.get("latitude")
        self.super_dict["dst_country"] = dst_ip_clean.get("country")
        self.super_dict["dst_iso_code"] = dst_ip_clean.get("iso_code")
        self.super_dict["dst_ip"] = line.get("dst_ip")
        self.super_dict["dst_port"] = line.get("dst_port")

        # 공격종류 실사용으로 바꿔야함
        self.super_dict["attack_type"] = line.get("attack_type")

        # 국가 테이블 데이터 갱신
        self.track_country_stats(
            country=src_ip_clean.get("country"), iso_code=src_ip_clean.get("iso_code")
        )

        # 공격 유형 테이블 데이터 갱신
        self.track_attack_type(attack_type=self.super_dict["attack_type"])

        # redis로 데이터 전송
        self.redis_instance.publish("attack-map-production", self.super_dict)

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


def main():
    tracker = AttackMapTracker()
    try:
        tracker.run()
    except KeyboardInterrupt:
        exit()


if __name__ == "__main__":
    main()