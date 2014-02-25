import jinja2
import os
from collections import OrderedDict
from secret import KEY

SIGNOUT = "/logout"
JINJA_ENV = jinja2.Environment(autoescape=True,
	loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), '../templates')))

ACTIONS = OrderedDict([
	('comments', 'Comments'),
	('cards', 'Created Cards'),
	('boards', 'Created Boards'),
	('lists', 'Created Lists'),
	('updateChecklist', 'Checklists'),
	('moveCards', 'Moving Cards Between Lists')
])

# Args we ask Trello for when creating an auth token. Currently, I request
# a read only token that never expires.
TOKEN_ARGS = {
	'response_type': 'token',
	'key': KEY,
	'scope': 'read',
	'expiration': 'never',
	'name': 'TrelloRSS'
}