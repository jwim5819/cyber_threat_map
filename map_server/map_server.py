import json
import redis
import tornadoredis
import subprocess

import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.autoreload

from dotenv import load_dotenv
import os
from sys import exit


# Look up service colors
service_rgb = {
    "FTP": "#FF1D25",
    "SSH": "#FF1D25",
    "TELNET": "#FF1D25",
    "EMAIL": "#FF1D25",
    "WHOIS": "#FF1D25",
    "DNS": "#B81FFF",
    "HTTP": "#B81FFF",
    "HTTPS": "#B81FFF",
    "SQL": "#B81FFF",
    "SNMP": "#B81FFF",
    "SMB": "#FFB72D",
    "AUTH": "#FFB72D",
    "RDP": "#FFB72D",
    "DoS": "#FFB72D",
    "ICMP": "#FFB72D",
    "OTHER": "#FFB72D",
}


# Load environment variables from .env file
load_dotenv()


class IndexHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(request):
        request.render("index.html",
                       HOST=os.getenv("WEB_SERVER_HOST"),
                       PORT=os.getenv("DOCKER_PORT"))


class WebSocketChatHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        super(WebSocketChatHandler, self).__init__(*args, **kwargs)
        self.listen()

    def check_origin(self, origin):
        return True

    @tornado.gen.engine
    def listen(self):
        print("[*] WebSocketChatHandler opened")

        try:
            # This is the IP address of the DataServer
            self.client = tornadoredis.Client(os.getenv("REDIS_HOST"))
            self.client.connect()
            print("[*] Connected to Redis server")
            yield tornado.gen.Task(self.client.subscribe, "attack-map-production")
            self.client.listen(self.on_message)
        except Exception as ex:
            print("[*] Could not connect to Redis server.")
            print("[*] {}".format(str(ex)))

    def on_close(self):
        print("[*] Closing connection.")

    # This function is called everytime a Redis message is received
    def on_message(self, msg):
        if len(msg) == 0:
            print("msg == 0\n")
            return None

        if "ip_blocked" in msg:
            ip = re.split(":", msg)
            # fp = open('/mnt/map_attack_blk/LOG4.log','a')
            # fp.write(ip[1]+"\n")
            # fp.close()

        try:
            json_data = json.loads(msg.body)
        except Exception as ex:
            return None

        if "msg_type" in json_data:
            msg_type = json_data["msg_type"]
        else:
            msg_type = None
        if "msg_type2" in json_data:
            msg_type2 = json_data["msg_type2"]
        else:
            msg_type2 = None
        if "msg_type3" in json_data:
            msg_type3 = json_data["msg_type3"]
        else:
            msg_type3 = None
        if "protocol" in json_data:
            protocol = json_data["protocol"]
        else:
            protocol = None
        if "src_ip" in json_data:
            src_ip = json_data["src_ip"]
        else:
            src_ip = None
        if "dst_ip" in json_data:
            dst_ip = json_data["dst_ip"]
        else:
            dst_ip = None
        if "src_port" in json_data:
            src_port = json_data["src_port"]
        else:
            src_port = None
        if "dst_port" in json_data:
            dst_port = json_data["dst_port"]
        else:
            dst_port = None
        if "latitude" in json_data:
            src_lat = json_data["latitude"]
        else:
            src_lat = None
        if "longitude" in json_data:
            src_long = json_data["longitude"]
        else:
            src_long = None
        if "dst_lat" in json_data:
            dst_lat = json_data["dst_lat"]
        else:
            dst_lat = None
        if "dst_long" in json_data:
            dst_long = json_data["dst_long"]
        else:
            dst_long = None
        if "dst_country" in json_data:
            dst_country = json_data["dst_country"]
        else:
            dst_country = None
        if "city" in json_data:
            city = json_data["city"]
        else:
            city = None
        if "continent" in json_data:
            continent = json_data["continent"]
        else:
            continent = None
        if "continent_code" in json_data:
            continent_code = json_data["continent_code"]
        else:
            continent_code = None
        if "country" in json_data:
            country = json_data["country"]
        else:
            country = None
        if "iso_code" in json_data:
            iso_code = json_data["iso_code"]
        else:
            iso_code = None
        if "postal_code" in json_data:
            postal_code = json_data["postal_code"]
        else:
            postal_code = None
        if protocol:
            color = service_rgb[protocol]
        else:
            color = "#000000"
        if "event_count" in json_data:
            event_count = json_data["event_count"]
        else:
            event_count = None
        if "continents_tracked" in json_data:
            continents_tracked = json_data["continents_tracked"]
        else:
            continents_tracked = None
        if "countries_tracked" in json_data:
            countries_tracked = json_data["countries_tracked"]
        else:
            countries_tracked = None
        if "ips_tracked" in json_data:
            ips_tracked = json_data["ips_tracked"]
        else:
            ips_tracked = None
        if "unknowns" in json_data:
            unknowns = json_data["unknowns"]
        else:
            unknowns = None
        if "event_time" in json_data:
            event_time = json_data["event_time"]
        else:
            event_time = None
        if "country_to_code" in json_data:
            country_to_code = json_data["country_to_code"]
        else:
            country_to_code = None
        if "dst_country_to_code" in json_data:
            dst_country_to_code = json_data["dst_country_to_code"]
        else:
            dst_country_to_code = None
        if "ip_to_code" in json_data:
            ip_to_code = json_data["ip_to_code"]
        else:
            ip_to_code = None

        msg_to_send = {
            "type": msg_type,
            "type2": msg_type2,
            "type3": msg_type3,
            "protocol": protocol,
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "src_port": src_port,
            "dst_port": dst_port,
            "src_lat": src_lat,
            "src_long": src_long,
            "dst_lat": dst_lat,
            "dst_long": dst_long,
            "dst_country": dst_country,
            "city": city,
            "continent": continent,
            "continent_code": continent_code,
            "country": country,
            "iso_code": iso_code,
            "postal_code": postal_code,
            "color": color,
            "event_count": event_count,
            "continents_tracked": continents_tracked,
            "countries_tracked": countries_tracked,
            #'ips_tracked': "<a href='" + str(ips_tracked) + "'>" + str(ips_tracked) + "</a>",
            "ips_tracked": ips_tracked,
            "unknowns": unknowns,
            "event_time": event_time,
            "country_to_code": country_to_code,
            "dst_country_to_code": dst_country_to_code,
            "ip_to_code": ip_to_code,
        }

        self.write_message(json.dumps(msg_to_send))


class EnvHandler(tornado.web.RequestHandler):
    def get(self):
        env = {
            "CLIENT_HOST": os.getenv("CLIENT_HOST"),
            "CLIENT_PORT": os.getenv("CLIENT_PORT"),
            "MAPBOX_TOKEN": os.getenv("MAPBOX_TOKEN"),
            "HD_LAT": os.getenv("HD_LAT"),
            "HD_LNG": os.getenv("HD_LNG"),
            
        }
        self.set_header("Content-Type", "application/javascript")
        self.write(f"window._env_ = {json.dumps(env)}")


def main():
    # Register handler pages
    handlers = [
        (r"/websocket", WebSocketChatHandler),
        (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": "static"}),
        (r"/flags/(.*)", tornado.web.StaticFileHandler, {"path": "static/flags"}),
        (r"/", IndexHandler),
        (r"/env.js", EnvHandler),
    ]

    # Define the static path
    # static_path = path.join( path.dirname(__file__), 'static' )

    # Define static settings
    settings = {
        #'static_path': static_path
    }

    # Create and start app listening on port 8888
    try:
        app = tornado.web.Application(handlers, **settings)
        app.listen(os.getenv("WEB_SERVER_PORT"))
        print("[*] Waiting on browser connections...")
        tornado.autoreload.start()
        tornado.autoreload.watch('static/map.js')
        tornado.autoreload.watch('static/index.css')
        tornado.autoreload.watch('index.html')
        tornado.ioloop.IOLoop.instance().start()
        
    except Exception as appFail:
        print(appFail)


if __name__ == "__main__":
    try:
        main() 
    except KeyboardInterrupt:
        print("\nSHUTTING DOWN")
        subprocess.run(["bash", "../stop.sh"])
        exit()
