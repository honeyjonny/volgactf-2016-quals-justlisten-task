import tornado.web
import tornado.escape

from tornado.web import Finish

from hashlib import md5
from time import time


class MongoDbModelsMiddleware(object):
	async def find_users(self):
		return [u for u in self.application.db.users.find({}, {"_id": 0 })]

	async def create_user(self, user):
		return self.application.db.users.save(user)

	async def find_user_byname(self, name):
		return self.application.db.users.find( {"name": name} )

	async def find_user_by_logindata(self, userDto):
		return self.application.db.users.find( userDto )

	async def save_cookie_for_user(self, user, cookie):
		return self.application.db.tokens.save( { "user_id": user["_id"], "value": cookie } ) 

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

	async def create_connection_to_channel(self, channelDoc, tokenDoc):
		return self.application.db.connections.save( { "token_id": str( tokenDoc["_id"] ), "channel_id": str(channelDoc["_id"]) } )

	async def find_all_connections_to_channel(self, channelDoc):
		return self.application.db.connections.find( { "channel_id": str(channelDoc["_id"]) } )	


class Basehandler(tornado.web.RequestHandler, MongoDbModelsMiddleware):

	async def generate_session_for_user(self, userDto):
		digest = md5()
		digest.update(userDto["name"].encode("utf-8"))
		digest.update(userDto["pass"].encode("utf-8"))
		digest.update( str( userDto["_id"] ).encode("utf-8") )
		digest.update( str( time() ).encode("utf-8") )		
		return digest.hexdigest()

	async def prepare(self):
		cookie_value = self.get_cookie("_ws_token")

		if cookie_value == None:
			self.current_user = None;

		else:
			user = await self.find_user_by_token(cookie_value)
			if user == None:
				self.set_status(404)
				self.write({"error": "invalid token"})
				self.finish()

			else:
				self.current_user = user


class RegisteredOnlyHandler(Basehandler):
	async def prepare(self):
		await super().prepare()

		cookie_value = self.get_cookie("_ws_token")

		if self.current_user == None and cookie_value == None:
			self.set_status(401)
			self.write({"error": "unauthorized"})
			self.finish()



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


class Loguothandler(RegisteredOnlyHandler):
	async def get(self):
		user = self.current_user
		await self.delete_prev_tokens(user)

		self.set_status(303)
		self.redirect("/")

