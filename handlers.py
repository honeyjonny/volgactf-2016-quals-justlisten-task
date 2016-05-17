# coding: UTF-8

import tornado.web
import tornado.websocket
import tornado.escape

from hashlib import md5
from time import time

from dbprovider import MongoDbModelsMiddleware

class WSClientPoolMiddleware(object):

	def add_connection(self, token, connection):
		self.application.ws[token] = connection

	def remove_connection(self, token):
		if self.application.ws.get(token) != None:
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

	@property
	def current_username(self):
		if self.current_user == None:
			return None
		else:
			return self.current_user["name"]

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
				return
				# self.set_status(404)
				# self.write({"error": "invalid token"})
				# self.finish()

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
		#self.write( { "users": resp, "current": curr_username } )
		self.render("index.html", users = resp, current_username = self.current_username )


class RegisterHandler(Basehandler):
	async def get(self):
		self.render("form.html", action="register", current_username = self.current_username )

	async def post(self):
		# body = tornado.escape.json_decode(self.request.body)
		# username = body["username"]
		# password = body["password"]

		username = self.get_argument( "username" )
		password = self.get_argument( "password" )

		cursor = await self.find_user_byname(username)
		count = cursor.count()

		if count > 0:
			self.set_status(409)
			self.write({"error": "user already exists"})
			self.finish()
			return

		#injection here
		usr = {"name":username, "pass": password}

		uid = await self.create_user(usr)

		self.set_status(201)
		self.redirect("/login")
		#self.write( { "userId": str(uid) } )


class LoginHandler(Basehandler):
	async def get(self):
		self.render("form.html", action="login", current_username = self.current_username )

	async def post(self):
		#body = tornado.escape.json_decode(self.request.body)
		#username = body["username"]
		#password = body["password"]

		username = self.get_argument( "username" )
		password = self.get_argument( "password" )

		print( username)
		print(password)

		
		usr = {"name":username, "pass": password}

		#injection here
		#crazy fucking shit!
		js = "function () { return db.users.findOne ({ name:'" + username + "', pass:'" + password + "' }); }"		
		self.application.db.eval(js)

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
		else:
			self.set_status(404)
			self.write({ "status": "not found this user", "user": usr})


class ChannelsHandler(RegisteredOnlyHandler):
	async def get(self):
		channels = await self.get_all_channels()

		self.set_status(200)
		self.render("channels.html", current_username = self.current_username, channels = channels)
		#self.write( { "channels": channels } )


	async def post(self):
		#body = tornado.escape.json_decode(self.request.body)
		#channelName = body["channelName"]
		channelName = self.get_argument( "channelName" )

		if len(channelName) == 0:
			self.set_status(409)
			self.write( { "error": "channel name cannot be empty" } )
			self.redirect("/channels")
			return

		channelCur = await self.find_channel_by_name_async(channelName)

		if channelCur != None:
			self.set_status(409)
			self.write({"error": "channel already exists"})
			self.finish()
			return	

		channelId = await self.create_channel_by_name_async(channelName)

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
#	{var ws = new WebSocket("ws://localhost:7777/channels/56f2625ef291101f7471c883"); 
#	ws.onopen = function(){ console.log("open channel"); ws.send("hello"); }; 
#	ws.onmessage = function(evt){ console.log(evt.data);}; })()
#
#
	def open(self, channelId):

		channel = self.find_channel_byid(channelId)

		if channel != None:
			self.current_channel = channel
		else:
			self.write_message("Invalid channelId on connection argument")
			self.close()
			return			

		# print(self.current_user)
		# print(self.current_token)
		# print(self.current_channel)

		if channel["name"] == self.application.FLAG_CHANNEL:
			self.write_message("You cannot explicity connect to this flag channel ; { ")
			self.close()
			return

		connId = self.create_connection_to_channel(channel, self.current_token)
		self.add_connection(self.current_token, self)

		self.write_message( { "token": self.current_token, "channel_id": channelId } ) #"connId": str(connId), 


	def on_message(self, message):

		# print (message)
		# print(self.current_user)
		# print(self.current_token)
		# print(self.current_channel)

		connections = self.find_all_connections_to_channel(self.current_channel)
		for conn in connections:
			try:
				ws = self.get_connection(conn["token"])
				#if self.current_token != conn["token"]:
				ws.write_message(message)
			except Exception as e:
				print("Send err:" + e)
				ws.close()



	def on_close(self):
		self.remove_connection(self.current_token)
		self.delete_connection_entries(self.current_token)





