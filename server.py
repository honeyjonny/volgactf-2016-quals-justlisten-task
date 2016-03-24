import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import os.path

import pymongo

from time import sleep

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
            (r"/channels/([\w]{24})", WSConnectionHandler),
        ]

        settings = dict(
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "public"),
            #xsrf_cookies=True,
        )

        self.db = pymongo.MongoClient("localhost", 27017).tutorial

        self.ws = dict()

        self.clear_connections()

        self.init_database()
        self.create_idexes_for_collections()        

        super(Application, self).__init__(handlers, **settings)


    def clear_connections(self):
        self.db.connections.delete_many( {} )
        print("Clear connections")


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



class FlagBot(MongoDbModelsMiddleware, WSClientPoolMiddleware):

    FLAG_POLLING_MS = 120000
    FLAG_CHANNEL = "VolgaCTF_Flag_Channel"
    FLAG = "VolgaCTF{__ooh_crazy_chat_but_pwned__}"

    def __init__(self, application):
        self.application = application
        self.application.FLAG_CHANNEL = self.FLAG_CHANNEL

    def send_flag(self):
        print("[*] Bot flag UP!")

        channelDoc = self.find_channel_by_name(self.FLAG_CHANNEL)

        if channelDoc == None:

            print("[*] Channel { %s } not exists, im create this channel manually" % self.FLAG_CHANNEL)
            self.create_channel_by_name(self.FLAG_CHANNEL)
            channelDoc = self.find_channel_by_name(self.FLAG_CHANNEL)

            if channelDoc == None:
                print("[!] Something wrong! ")
                return

            print("[*] Create channel %s, go work." % self.FLAG_CHANNEL)

        connections = self.find_all_connections_to_channel(channelDoc)

        if connections.count() == 0:
            print("[*] Not connections to flag channel, fuck.")
            return

        else:
            print("[*] Found connections: %d, lets ROCK!" % connections.count())

            for conn in connections:
                try:
                    ws = self.get_connection(conn["token"])
                    ws.write_message("hey, pss...")
                    sleep(1)
                    ws.write_message("i got something for you..")
                    sleep(3)
                    ws.write_message(self.FLAG)
                    sleep(1)
                    ws.write_message(" DANCE! :} ")
                except Exception as e:
                    print(e)
                    ws.close()


            print("[*] Send Done, go sleep.")

    def start(self):
        callback = tornado.ioloop.PeriodicCallback(self.send_flag, self.FLAG_POLLING_MS)
        callback.start()


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)

    print("Start bot")
    bot = FlagBot(app)
    bot.start()


    print("Start app")
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()