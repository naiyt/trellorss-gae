from trellorss import TrelloRSS
from testvar import *

test = TrelloRSS(key, token)

# test.get_all(items=['updateCard'])
test.get_all()

print test.rss