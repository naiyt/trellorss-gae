from google.appengine.ext import ndb

class Feed(ndb.Model):
	channel_title = ndb.StringProperty()
	channel_link = ndb.StringProperty()
	channel_description = ndb.StringProperty()
	feed_name = ndb.StringProperty()
	actions = ndb.StringProperty(repeated=True) # A list of the actions to filter on
	token = ndb.StringProperty() # Optional if getting public boards
	get_all = ndb.BooleanProperty(default=False) # True if getting all private boards
	board_id = ndb.StringProperty() # Used if get_all is false
	public_board = ndb.BooleanProperty(default=False)
	user = ndb.KeyProperty()

class Users(ndb.Model):
	email = ndb.StringProperty()
	date_created = ndb.DateTimeProperty(auto_now_add=True)
	auth_token = ndb.StringProperty()
	token_expiration = ndb.DateTimeProperty()
	feeds = ndb.KeyProperty(repeated=True)

