import tornado.web
import tornado.escape


class MainHandler(tornado.web.RequestHandler):
	async def get(self):
		resp = await self.find_users()

		self.write({"users": resp})

	async def find_users(self):
		return [u for u in self.application.db.users.find({}, {"_id": 0 })]


class RegisterHandler(tornado.web.RequestHandler):
	async def post(self):

		print(self.request.body)

		body = tornado.escape.json_decode(self.request.body)

		username = body["username"]
		password = body["password"]

		usr = {"name":username, "pass": password}

		uid = await self.create_user(usr)

		self.write({"userId": str(uid)})

	async def create_user(self, user):
		return self.application.db.users.save(user)