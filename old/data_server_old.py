import json
import maxminddb
import redis
import io
import os

from const import META, PORTMAP
from sys import exit
from dotenv import load_dotenv
from time import localtime, sleep, strftime


class AttackMapTracker:
    def __init__(self, hq_ip="106.247.87.230", syslog_path="/var/log/syslog", db_path="../DB/GeoLite2-City.mmdb"):
        # Configuration
        self.hq_ip = hq_ip
        self.syslog_path = syslog_path
        self.db_path = db_path
        
        # Stats tracking
        self.server_start_time = strftime("%d-%m-%Y %H:%M:%S", localtime())  # local time
        self.event_count = 0
        self.continents_tracked = {}
        self.countries_tracked = {}
        self.country_to_code = {}
        self.dst_country_to_code = {}
        self.ip_to_code = {}
        self.ips_tracked = {}
        self.unknowns = {}
        
        # Initialize components
        load_dotenv()
        self.redis_instance = self.connect_redis()
        self.hq_dict = self.find_hq_lat_long()
    
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
    
    def connect_redis(self):
        print("try to connect redis")
        try:
            if os.getenv("ENV") == "LOCAL":
                r = redis.StrictRedis(host="127.0.0.1", port=6379, db=0)
            else:
                r = redis.StrictRedis(host=os.getenv("REDIS_HOST"), port=6379, db=0)
            print("redis connected")
            return r
        except:
            print("redis failed")
            return None
    
    def get_msg_type(self):
        return "Traffic"
    
    def get_tcp_udp_proto(self, src_port, dst_port):
        src_port = int(src_port)
        dst_port = int(dst_port)

        if src_port in PORTMAP:
            return PORTMAP[src_port]
        if dst_port in PORTMAP:
            return PORTMAP[dst_port]

        return "OTHER"
    
    def find_hq_lat_long(self):
        hq_ip_db_unclean = self.parse_maxminddb(self.hq_ip)
        if hq_ip_db_unclean:
            hq_ip_db_clean = self.clean_db(hq_ip_db_unclean)
            dst_lat = hq_ip_db_clean["latitude"]
            dst_long = hq_ip_db_clean["longitude"]
            dst_country = hq_ip_db_clean["country"]
            hq_dict = {"dst_lat": dst_lat, "dst_long": dst_long, "dst_country": dst_country}
            return hq_dict
        else:
            print("Please provide a valid IP address for headquarters")
            exit()
    
    def parse_maxminddb(self, ip):
        try:
            reader = maxminddb.open_database(self.db_path)
            response = reader.get(ip)
            reader.close()
            return response
        except FileNotFoundError:
            print("DB not found")
            print("SHUTTING DOWN")
            exit()
        except ValueError:
            return False
    
    def parse_syslog(self, line):
        line = line.split()
        data = line[-1]
        data = data.split(",")

        if len(data) != 6:
            print("NOT A VALID LOG")
            return False
        else:
            src_ip = data[0]
            dst_ip = data[1]
            src_port = data[2]
            dst_port = data[3]
            type_attack = data[4]
            cve_attack = data[5]
            data_dict = {
                "src_ip": src_ip,
                "dst_ip": dst_ip,
                "src_port": src_port,
                "dst_port": dst_port,
                "type_attack": type_attack,
                "cve_attack": cve_attack,
            }
            return data_dict
    
    def shutdown_and_report_stats(self):
        print("\nSHUTTING DOWN")
        print("\nREPORTING STATS...")
        print("\nEvent Count: {}".format(self.event_count))  # report event count
        print("\nContinent Stats...")  # report continents stats
        for key in self.continents_tracked:
            print("{}: {}".format(key, self.continents_tracked[key]))
        print("\nCountry Stats...")  # report country stats
        for country in self.countries_tracked:
            print("{}: {}".format(country, self.countries_tracked[country]))
        print("\nCountries to iso_codes...")
        for key in self.country_to_code:
            print("{}: {}".format(key, self.country_to_code[key]))
        print("\nIP Stats...")  # report IP stats
        for ip in self.ips_tracked:
            print("{}: {}".format(ip, self.ips_tracked[ip]))
        print("\nIPs to iso_codes...")
        for key in self.ip_to_code:
            print("{}: {}".format(key, self.ip_to_code[key]))
        print("\nUnknowns...")
        for key in self.unknowns:
            print("{}: {}".format(key, self.unknowns[key]))
        exit()
    
    def merge_dicts(self, *args):
        super_dict = {}
        for arg in args:
            super_dict.update(arg)
        return super_dict
    
    def track_flags(self, super_dict, tracking_dict, key1, key2):
        if key1 in super_dict and key2 in super_dict:
            if key1 not in tracking_dict:
                # 50개 넘어가면 밀어내기로 제거
                if len(tracking_dict) >= 50:
                    oldest_key = next(iter(tracking_dict))
                    tracking_dict.pop(oldest_key)
                tracking_dict[super_dict[key1]] = super_dict[key2]
        return tracking_dict
    
    def track_stats(self, super_dict, tracking_dict, key):
        if key in super_dict:
            node = super_dict[key]

            # 노드가 이미 tracking_dict에 있으면 증가
            if node in tracking_dict:
                tracking_dict[node] += 1
            else:
                # tracking_dict가 꽉 찼는지 확인
                if len(tracking_dict) >= 50:
                    # 가장 낮은 빈도의 항목 찾기
                    min_key = min(tracking_dict, key=tracking_dict.get)
                    # 가장 낮은 빈도의 항목 제거
                    del tracking_dict[min_key]
                # 새 항목 추가
                tracking_dict[node] = 1
        else:
            if key in self.unknowns:
                self.unknowns[key] += 1
            else:
                self.unknowns[key] = 1
    
    def process_log_entry(self, line):
        syslog_data_dict = self.parse_syslog(line)
        if not syslog_data_dict:
            return
            
        ip_db_unclean = self.parse_maxminddb(syslog_data_dict["src_ip"])
        if not ip_db_unclean:
            return
            
        self.event_count += 1
        ip_db_clean = self.clean_db(ip_db_unclean)
        hq_ip_db_unclean = self.parse_maxminddb(self.hq_ip)
        hq_ip_db_clean = self.clean_db(hq_ip_db_unclean)
        
        # 중복 제거 및 키값 변경
        hq_ip_db_clean = {
            "dst_country": hq_ip_db_clean.get("country"),
            "dst_iso_code": hq_ip_db_clean.get("iso_code"),
        }

        msg_type = {"msg_type": self.get_msg_type()}
        msg_type2 = {"msg_type2": syslog_data_dict["type_attack"]}
        msg_type3 = {"msg_type3": syslog_data_dict["cve_attack"]}

        proto = {
            "protocol": self.get_tcp_udp_proto(
                syslog_data_dict["src_port"],
                syslog_data_dict["dst_port"],
            )
        }
        
        super_dict = self.merge_dicts(
            self.hq_dict,
            ip_db_clean,
            hq_ip_db_clean,
            msg_type,
            msg_type2,
            msg_type3,
            proto,
            syslog_data_dict,
        )

        # Track Stats
        self.track_stats(super_dict, self.continents_tracked, "continent")
        self.track_stats(super_dict, self.countries_tracked, "country")
        self.track_stats(super_dict, self.ips_tracked, "src_ip")
        
        event_time = strftime("%d-%m-%Y %H:%M:%S", localtime())  # local time
        
        self.track_flags(super_dict, self.country_to_code, "country", "iso_code")
        self.track_flags(super_dict, self.dst_country_to_code, "dst_country", "dst_iso_code")
        self.track_flags(super_dict, self.ip_to_code, "src_ip", "iso_code")

        # Append stats to super_dict
        super_dict["event_count"] = self.event_count
        super_dict["continents_tracked"] = self.continents_tracked
        super_dict["countries_tracked"] = self.countries_tracked
        super_dict["ips_tracked"] = self.ips_tracked
        super_dict["unknowns"] = self.unknowns
        super_dict["event_time"] = event_time
        super_dict["country_to_code"] = self.country_to_code
        super_dict["dst_country_to_code"] = self.dst_country_to_code
        super_dict["ip_to_code"] = self.ip_to_code

        json_data = json.dumps(super_dict)
        self.redis_instance.publish("attack-map-production", json_data)

        print("Event Count: {}".format(self.event_count))
        print("------------------------")
    
    def check_permissions(self):
        if os.getuid() != 0:
            print("Please run this script as root")
            print("SHUTTING DOWN")
            return False
        return True
    
    def run(self):
        if not self.check_permissions():
            exit()
            
        with io.open(self.syslog_path, "r", encoding="ISO-8859-1") as syslog_file:
            print(f"syslog_path = {self.syslog_path}")
            syslog_file.readlines()  # Skip to the end of the file
            while True:
                where = syslog_file.tell()
                line = syslog_file.readline()
                if not line:
                    sleep(0.1)
                    syslog_file.seek(where)
                else:
                    self.process_log_entry(line)


def main():
    tracker = AttackMapTracker()
    try:
        tracker.run()
    except KeyboardInterrupt:
        tracker.shutdown_and_report_stats()


if __name__ == "__main__":
    main()