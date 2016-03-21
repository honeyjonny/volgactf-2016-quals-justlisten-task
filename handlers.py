import tornado.web
import tornado.escape

from hashlib import md5
from time import time


class Basehandler(tornado.web.RequestHandler):
	async def find_users(self):
		return [u for u in self.application.db.users.find({}, {"_id": 0 })]

	async def create_user(self, user):
		return self.application.db.users.save(user)

	async def find_user_byname(self, name):
		return self.application.db.users.find( {"name":name} )

	async def find_user_by_logindata(self, userDto):
		return self.application.db.users.find( userDto )

	async def save_cookie_for_user(self, user, cookie):
		return self.application.db.tokens.save( { "user_id": user["_id"], "value": cookie } ) 

	async def delete_prev_tokens(self, user):
		deleted = self.application.db.tokens.delete_many(  { "user_id": user["_id"] } )
		#print(deleted.deleted_count)
		return deleted.deleted_count

	async def find_user_by_token(self, token):
		cur = self.application.db.tokens.find( { "value" : token } )
		if cur.count() == 1:
			token_doc = cur[0]
			userCur = self.application.db.users.find( {"_id": token_doc["user_id"] }  )
			assert userCur.count() == 1
			
			user = userCur[0]
			return user
		else:
			return None



	async def generate_session_for_user(self, userDto):
		digest = md5()
		digest.update(userDto["name"].encode("utf-8"))
		digest.update(userDto["pass"].encode("utf-8"))
		digest.update( str( userDto["_id"] ).encode("utf-8") )
		digest.update(str( time() ).encode("utf-8") )
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





class MainHandler(Basehandler):
	async def get(self):
		resp = await self.find_users()

		print (self.current_user)

		self.write({"users": resp, "current": self.current_user["name"]})


class RegisterHandler(Basehandler):
	async def post(self):
		body = tornado.escape.json_decode(self.request.body)

		username = body["username"]
		password = body["password"]

		cursor = await self.find_user_byname(username)
		isExist = cursor.count()

		if isExist > 0:
			self.set_status(409)
			self.write({"error": "user already exists"})
			self.flush()
			return

		usr = {"name":username, "pass": password}

		uid = await self.create_user(usr)

		self.write({"userId": str(uid)})


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
