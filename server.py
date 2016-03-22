import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import os.path

import pymongo

from handlers import *

from tornado.options import define, options

define("port", default=7777, help="run on the given port", type=int)


class Application(tornado.web.Application):

    COLLECTIONS = {

    # collection : index fields : is unique flag

    "users": { "name": True, "pass": False },
    "tokens": { "user_id": True, "value": True },
    "channels": { "name": True },
    "connections": { "token": False, "channel_id": False },

    }

    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/register", RegisterHandler),
            (r"/login", LoginHandler),
            (r"/channels", ChannelsHandler),
            (r"/logout", Logouthandler),
            (r"/channels/([\w]+)", WSConnectionHandler),
        ]

        settings = dict(
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            #xsrf_cookies=True,
        )

        self.db = pymongo.MongoClient("localhost", 27017).tutorial

        self.ws = dict()

        self.init_database()
        self.create_idexes_for_collections()

        super(Application, self).__init__(handlers, **settings)


    def init_database(self):
        for coll in self.COLLECTIONS.keys():
            try:
                self.db.create_collection(coll)
            except Exception as e:
                print(e)


    def create_idexes_for_collections(self):
        for coll in self.COLLECTIONS.keys():
            
            indexes = self.COLLECTIONS[coll]

            for index_name in indexes.keys():
                self.db[coll].create_index([ ( index_name, 1), ("unique", indexes[index_name] ) ] )



def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()