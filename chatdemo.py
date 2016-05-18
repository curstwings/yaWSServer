#coding=utf-8
#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
from tornado import autoreload
"""Simplified chat demo for websockets.

Authentication, error handling, etc are left as an exercise for the reader :)
"""

import logging
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import os.path
import uuid

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html", messages=ChatSocketHandler.cache)

class ChatSocketHandler(tornado.websocket.WebSocketHandler):
    waiters = set()
    cache = []
    cache_size = 200
    external_storage = {}
    # Data format: {'random_uuid': {'id': 'random_uuid', 'instance': WebSocketHandler(), 'user_id': '2990096', 'mu': '2206'}}

#     def __init__(self, application, request, **kwargs):
#         self.designated = {}
#         # Data format: {'2206': 'random_uuid'}
# 
#         self.external_storage = kwargs['external_storage']
#         kwargs = {}
# 
#         tornado.web.RequestHandler.__init__(self, application, request,
#                                             **kwargs)
#         self.stream = request.connection.stream
#         self.ws_connection = None
    
    def get_compression_options(self):
        # Non-None enables compression with default options.
        return {}

    def open(self):
        # 完成連線，將此 WebSocket 儲存
        self.id = str(uuid.uuid4())
        self.external_storage[self.id] = {'id': self.id, 'instance': self, 'user_id': None}
        logging.info('User: ' + self.id + ' has connected.')
        if self not in ChatSocketHandler.waiters:
            ChatSocketHandler.waiters.add(self)

    def on_close(self):
        # 連線結束，將此 WebSocket 移除
        # 下面這段還不知道有沒有效果(好像有內)
        try:
            del self.external_storage[self.id]
            self.connected = False
            logging.info("on_close success")
        except:
            logging.info("on_close fail")
            pass
        
        #下面實作把自己從waiter裡面移除
        logging.info('User: ' + self.id + ' [x] disconnected.')
        if self in ChatSocketHandler.waiters:
            ChatSocketHandler.waiters.remove(self)

    @classmethod
    def update_cache(cls, chat):
        cls.cache.append(chat)
        if len(cls.cache) > cls.cache_size:
            cls.cache = cls.cache[-cls.cache_size:]

    @classmethod
    def send_updates(cls, chat, targetid):
        logging.info("sending message to %d waiters", len(cls.waiters))
        
        for waiter in cls.waiters:
            if cls.external_storage[targetid]['instance'] == waiter:
                try:
                    waiter.write_message(chat)
                    logging.info(cls.waiters)
                except:
                    logging.error("Error sending message", exc_info=True)

    def on_message(self, message):
        logging.info("got message %r", message)
        #將收到訊息以冒號為標記分割成幾段
        #parts = message.split(':', 1)
        #logging.info("part 1:" + parts[0])

        #以tornado內建方法decode message
        parsed = tornado.escape.json_decode(message)
        chat = {
            "id": str(uuid.uuid4()),
            "body": parsed["body"],
            "tarid": parsed["user"],
            }
        chat["html"] = tornado.escape.to_basestring(
            self.render_string("message.html", message=chat))
        
        #可以用self.external_storage[self.id]['instance']來對應waiters裡面的物件！！！！！
        logging.info("self.uuid = " + self.id)
        logging.info("self.uuid = " + self.external_storage[self.id]['id'])
        logging.info("target.id = " + chat['tarid'])
        
        #if self.external_storage[self.id]
        ChatSocketHandler.update_cache(chat)
        ChatSocketHandler.send_updates(chat, chat['tarid'])

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/chatsocket", ChatSocketHandler),
        ]
        settings = dict(
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
            debug = True,
            autoreload = True
        )
        super(Application, self).__init__(handlers, **settings)

def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    main()
