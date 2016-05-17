# coding: UTF-8


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

	async def create_channel_by_name_async(self, channelName):
		return self.application.db.channels.save( { "name": channelName } )

	async def find_channel_by_name_async(self, channelName):
		cur = self.application.db.channels.find( { "name": channelName } )
		if cur.count() == 1:
			return cur[0]
		else:
			return None

	def create_channel_by_name(self, channelName):
		return self.application.db.channels.save( { "name": channelName } )

	def find_channel_by_name(self, channelName):
		cur = self.application.db.channels.find( { "name": channelName } )
		if cur.count() == 1:
			return cur[0]
		else:
			return None

	def find_channel_byid(self, channelId):
		chid = ObjectId(channelId)
		cursor = self.application.db.channels.find( { "_id": chid } )
		if cursor.count() == 1:
			return cursor[0]
		else:
			return None

	def create_connection_to_channel(self, channelDoc, token):
		cur = self.application.db.connections.find( { "token": token, "channel_id": str(channelDoc["_id"]) } )
		if cur.count() == 0:
			return self.application.db.connections.save( { "token": token, "channel_id": str(channelDoc["_id"]) } )			
		else:
			return cur[0]["_id"]

	def find_all_connections_to_channel(self, channelDoc):
		return self.application.db.connections.find( { "channel_id": str(channelDoc["_id"]) } )

	def delete_connection_entries(self, token):
		return self.application.db.connections.delete_many( { "token": token } )	
