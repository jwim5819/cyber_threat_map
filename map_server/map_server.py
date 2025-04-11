import json
import ast
import tornadoredis
import subprocess
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.autoreload

from dotenv import load_dotenv
from sys import exit
from utils.logger import mapserver_logger

# 환경변수 로딩
load_dotenv()


class IndexHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(request):
        request.render(
            "index.html", HOST=os.getenv("HOST_IP"), PORT=os.getenv("HOST_PORT")
        )


class WebSocketChatHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        super(WebSocketChatHandler, self).__init__(*args, **kwargs)
        self.listen()

    @tornado.gen.engine
    def listen(self):
        mapserver_logger.info("WebSocketChatHandler opened")
        try:
            self.client = tornadoredis.Client(os.getenv("REDIS_HOST"))
            self.client.connect()
            mapserver_logger.info("Connected to Redis server")
            yield tornado.gen.Task(self.client.subscribe, "attack-map-production")
            self.client.listen(self.on_message)
        except Exception as ex:
            mapserver_logger.error("Could not connect to Redis server.")
            mapserver_logger.error("{}".format(str(ex)))

    def on_close(self):
        mapserver_logger.info("Closing connection.")

    # redis에서 message를 구독할 때 마다 실행되는 함수
    def on_message(self, msg):        
        if len(msg) == 0 or msg.body == 1:
            return None
        w_msg = ast.literal_eval(msg.body)
        try:
            self.write_message(w_msg)
        except Exception as e:
            mapserver_logger.error(f"mo {e}")
            return None
        
        


def main():
    handlers = [
        (r"/websocket", WebSocketChatHandler),
        (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": "static"}),
        (r"/flags/(.*)", tornado.web.StaticFileHandler, {"path": "static/flags"}),
        (r"/(favicon\.ico)", tornado.web.StaticFileHandler, {"path": "static"}),
        (r"/", IndexHandler)
    ]
    
    try:
        app = tornado.web.Application(handlers=handlers)
        app.listen(os.getenv("CONTAINER_PORT"))
        mapserver_logger.info("Waiting on browser connections...")
        tornado.autoreload.start()
        tornado.autoreload.watch('static/map.js')
        tornado.autoreload.watch('static/map.js')
        tornado.autoreload.watch('static/index.css')
        tornado.autoreload.watch('index.html')
        tornado.autoreload.watch('../data_server/data_server.py')
        tornado.autoreload.watch('../data_server/syslog_receiver.py')
        tornado.ioloop.IOLoop.instance().start()
    except Exception as e:
        mapserver_logger.error(f"mm {e}")
        
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        subprocess.run(["bash", "stop.sh"])
        exit()