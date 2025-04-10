import os
import redis
import maxminddb
import json
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from syslog_receiver import SyslogMonitor
from const import META
from utils.logger import mapserver_logger

class AttackMapTracker:
    def __init__(self):
        # .env loading
        load_dotenv()

        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(script_dir, "../DB/GeoLite2-City.mmdb")
        self.stats_path = os.path.join(script_dir, "../DB/stats.txt")
        self.event_count = 0
        self.redis_instance = self.connect_redis()
        self.super_dict = {}
        self.flags_dict = {}
        self.stats_list = []
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
        src_ip_clean = self.find_geodata(ip=line["src_ip"])
        dst_ip_clean = self.find_geodata(ip=line["dst_ip"])

        # geodata 누락 시 리턴
        if src_ip_clean is None or dst_ip_clean is None:
            return

        self.event_count += 1

        # general
        self.super_dict["event_time"] = line.get("time")

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

        # 컬러 실사용으로 바꿔야함
        import random
        colors = ["#B81FFF", "#FF1D25", "#FFB72D"]
        selected_color = random.choice(colors)
        self.super_dict["color"] = selected_color
        
        # 국가 테이블 데이터 갱신
        self.track_country_stats(country=src_ip_clean.get("country"),iso_code=src_ip_clean.get("iso_code"))
        
        # redis로 데이터 전송
        self.redis_instance.publish("attack-map-production", self.super_dict)

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
        if not os.path.exists(self.stats_path):
            open(self.stats_path, 'w').close()
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
        with open(self.stats_path, "w", encoding="utf-8") as f:
            json.dump(self.stats_list, f, ensure_ascii=False, indent="\t")
        return

    def check_permissions(self):
        if os.getuid() != 0:
            mapserver_logger.info("Please run this script as root")
            mapserver_logger.info("SHUTTING DOWN")
            return False
        return True

    def run(self):
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
