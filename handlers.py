import tornado.web
import tornado.escape


class Basehandler(tornado.web.RequestHandler):
	async def find_users(self):
		return [u for u in self.application.db.users.find({}, {"_id": 0 })]

	async def create_user(self, user):
		return self.application.db.users.save(user)

	async def find_user_byname(self, name):
		return self.application.db.users.find( {"name":name} )



class MainHandler(Basehandler):
	async def get(self):
		resp = await self.find_users()

		self.write({"users": resp})


class RegisterHandler(Basehandler):
	async def post(self):

		print(self.request.body)

		body = tornado.escape.json_decode(self.request.body)

		username = body["username"]
		password = body["password"]

		cursor = await self.find_user_byname(username)
		isExist = cursor.count()

		if isExist > 0:
			self.write({"error": "user already exists"})
			self.flush()
			return

		usr = {"name":username, "pass": password}

		uid = await self.create_user(usr)

		self.write({"userId": str(uid)})
