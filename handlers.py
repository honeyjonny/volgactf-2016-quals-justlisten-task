import tornado.web
import tornado.websocket
import tornado.escape

from hashlib import md5
from time import time

from bson import ObjectId


class MongoDbModelsMiddleware(object):
	async def find_users(self):
		return [u for u in self.application.db.users.find({}, {"_id": 0 })]

	async def create_user(self, user):
		return self.application.db.users.save(user)

	async def find_user_byname(self, name):
		return self.application.db.users.find( {"name": name} )

	async def find_user_by_logindata(self, userDto):
		return self.application.db.users.find( userDto )

	async def save_cookie_for_user(self, userDoc, cookie):
		return self.application.db.tokens.save( { "user_id": userDoc["_id"], "value": cookie } ) 

	async def delete_prev_tokens(self, userDoc):
		deleted = self.application.db.tokens.delete_many(  { "user_id": userDoc["_id"] } )
		return deleted.deleted_count

	async def find_user_by_token(self, token):
		cur = self.application.db.tokens.find( { "value" : token } )
		if cur.count() == 1:
			token_doc = cur[0]
			userCur = self.application.db.users.find( {"_id": token_doc["user_id"] }  )
			if userCur.count() == 1:			
				user = userCur[0]
				return user		
		return None

	async def get_all_channels(self):
		def map_doc_to_dto(chDoc):
			chDoc["_id"] = str(chDoc["_id"])
			return chDoc
		return [ map_doc_to_dto(ch) for ch in self.application.db.channels.find( {} ) ]

	async def create_channel_by_name(self, channelName):
		return self.application.db.channels.save( { "name": channelName } )

	async def find_channel_by_name(self, channelName):
		return self.application.db.channels.find( { "name": channelName } )

	def find_channel_byid(self, channelId):
		chid = ObjectId(channelId)
		cursor = self.application.db.channels.find( { "_id": chid } )
		if cursor.count() == 1:
			return cursor[0]
		else:
			raise Exception("Multiple channel return by one channelId")

	def create_connection_to_channel(self, channelDoc, token):
		return self.application.db.connections.save( { "token": token, "channel_id": str(channelDoc["_id"]) } )

	def find_all_connections_to_channel(self, channelDoc):
		return self.application.db.connections.find( { "channel_id": str(channelDoc["_id"]) } )	


class WSClientPoolMiddleware(object):

	def add_connection(self, token, connection):
		self.application.ws[token] = connection

	def remove_connection(self, token):
		del self.application.ws[token]

	def get_connection(self, token):
		return self.application.ws[token]


class Basehandler(tornado.web.RequestHandler, MongoDbModelsMiddleware):

	@property	
	def current_token(self):
		if not hasattr(self, "_current_token"):
			self._current_token = self.get_cookie("_ws_token")
		return self._current_token

	@current_token.setter
	def current_token(self, value):
		self._current_token = value

	async def generate_session_for_user(self, userDto):
		digest = md5()
		digest.update(userDto["name"].encode("utf-8"))
		digest.update(userDto["pass"].encode("utf-8"))
		digest.update( str( userDto["_id"] ).encode("utf-8") )
		digest.update( str( time() ).encode("utf-8") )		
		return digest.hexdigest()

	async def prepare(self):
		token = self.current_token #self.get_cookie("_ws_token")

		if token == None:
			self.current_user = None;

		else:
			user = await self.find_user_by_token(token)
			if user == None:
				self.set_status(404)
				self.write({"error": "invalid token"})
				self.finish()

			else:
				self.current_user = user


class RegisteredOnlyHandler(Basehandler):
	async def prepare(self):
		await super().prepare()

		#cookie_value = self.get_cookie("_ws_token")
		if self.current_user == None and self.current_token == None:
			self.set_status(401)
			self.write({"error": "unauthorized"})
			self.finish()


class BaseWSHandler(RegisteredOnlyHandler, tornado.websocket.WebSocketHandler, WSClientPoolMiddleware):
	@property
	def current_channel(self):
		if not hasattr(self, "_current_channel"):
			self._current_channel = None
		return self._current_channel

	@current_channel.setter
	def current_channel(self, value):
		self._current_channel = value	


class MainHandler(Basehandler):
	async def get(self):
		resp = await self.find_users()

		print (self.current_user)

		curr_username = self.current_user["name"] if self.current_user else None

		self.write( { "users": resp, "current": curr_username } )


class RegisterHandler(Basehandler):
	async def post(self):
		body = tornado.escape.json_decode(self.request.body)

		username = body["username"]
		password = body["password"]

		cursor = await self.find_user_byname(username)
		count = cursor.count()

		if count > 0:
			self.set_status(409)
			self.write({"error": "user already exists"})
			self.finish()
			return

		usr = {"name":username, "pass": password}

		uid = await self.create_user(usr)

		self.write( { "userId": str(uid) } )


class LoginHandler(Basehandler):
	async def post(self):
		body = tornado.escape.json_decode(self.request.body)

		username = body["username"]
		password = body["password"]

		usr = {"name":username, "pass": password}

		cursor = await self.find_user_by_logindata(usr)
		count = cursor.count()

		if count == 1:

			user = cursor[0]
			#print(user)

			cookie = await self.generate_session_for_user(user)

			await self.delete_prev_tokens(user)
			await self.save_cookie_for_user(user, cookie)

			self.set_status(202)
			self.set_cookie("_ws_token", cookie)
			self.redirect("/")
			return


class ChannelsHandler(RegisteredOnlyHandler):
	async def get(self):
		channels = await self.get_all_channels()

		self.set_status(200)
		self.write( { "channels": channels } )


	async def post(self):
		body = tornado.escape.json_decode(self.request.body)

		channelName = body["channelName"]

		channelCur = await self.find_channel_by_name(channelName)
		count = channelCur.count()

		if count > 0:
			self.set_status(409)
			self.write({"error": "channel already exists"})
			self.finish()
			return	

		channelId = await self.create_channel_by_name(channelName)

		self.set_status(201)
		self.write( { "channelId": str(channelId) } )
		self.redirect("/channels")


class Logouthandler(RegisteredOnlyHandler):
	async def get(self):
		user = self.current_user
		await self.delete_prev_tokens(user)

		self.set_status(303)
		self.redirect("/")



class WSConnectionHandler(BaseWSHandler):

# test case
# 
# (function()
#	{var ws = new WebSocket("ws://localhost:7777/channels/56f0d8f8f291101bb8866fb1"); 
#	ws.onopen = function(){ console.log("open channel"); ws.send("hello"); }; 
#	ws.onmessage = function(evt){ console.log(evt.data);}; })()
#
#
	def open(self, channelId):
		channel = self.find_channel_byid(channelId)

		if channel != None:
			self.current_channel = channel

		print(self.current_user)
		print(self.current_token)
		print(self.current_channel)

		if channel["name"] == "flag":
			print("You cannot explicity connect to this flag channel")
			self.write_message("You cannot explicity connect to this flag channel")
			self.close()
			return

		connId = self.create_connection_to_channel(channel, self.current_token)
		self.add_connection(self.current_token, self)

		self.write_message( { "connId": str(connId) } )

	def on_message(self, message):
		print (message)
		print(self.current_user)
		print(self.current_token)
		print(self.current_channel)

	def on_close(self):
		self.remove_connection(self.current_token)





