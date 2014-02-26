import re
import logging
from models import Users, Feed
from trellorss.trellorss import TrelloRSS
from trellorss.trello import TrelloClient
from trellorss.trello import Unauthorized
from trellorss.trello import ResourceUnavailable
from google.appengine.ext import ndb
from google.appengine.api import memcache
import constants

def get_user(user):
    """ Get a user from the datastore """
    user_db = Users.get_by_id(user.user_id())
    if user_db is None:
        user_db = Users(id=user.user_id(),email=user.email())
        user_db.put()
    return user_db

def verify_token(token):
    """ Verify whether a token is correct by trying to get a list of a user's boards """
    trello = TrelloClient(constants.KEY, token)
    try:
        trello.list_boards()
    except Unauthorized:
        return False
    return True

def get_feeds(feeds):
    """ Retrieve info from the datastore on a set of feeds """
    feeds = ndb.get_multi(feeds)
    return [x for x in feeds if x is not None]

def delete_feeds(feeds,user):
    """ Remove a feed from memcache, and then delete it from the relevant user """
    feed_objs = get_feeds(make_keys(feeds))
    for feed in feed_objs:
        memcache.delete(str(feed.key.integer_id()))
        if feed in user.feeds:
            user.feeds.remove(feed)
        feed.key.delete()
    user.put()

def make_keys(feeds):
    """ Create the ndb keys for a set of feeds """
    return [ndb.Key('Feed', int(feed)) for feed in feeds]

# http://stackoverflow.com/questions/7160737/python-how-to-validate-a-url-in-python-malformed-or-not
url_regex = re.compile(
        r'^.*' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
url_re = r'.*trello.com/b/(.*)/.*'

def validate_input(board_id,link):
    """ Validate whether a board id is correct, and whether a link is correct """
    errors = []
    try_url = re.match(url_re, board_id)

    if try_url:
        board_id = try_url.group(1)
    trell = TrelloRSS(constants.KEY)

    try:
        trell.get_from(board_id, public_board=True)
    except ResourceUnavailable:
        errors.append('iderror')

    if not re.match(url_regex, link):
        errors.append('link')

    return board_id, link, errors

def create_url(feed_id):
    return "/feed/{}".format(feed_id)

def create_feed(user,board_id,title,link,description,actions,public_board,get_all,token):
    """ Creates a feed and attaches it to a user object """
    user = get_user(user)
    q = Feed.query(
        Feed.channel_title==title,
        Feed.channel_link==link,
        Feed.channel_description==description,
        Feed.feed_name==title,
        Feed.token==token,
        Feed.actions.IN(actions),
        Feed.board_id==board_id,
        Feed.public_board==public_board)
    feed = q.get()
    if feed is None:
        feed = Feed(
            channel_title=title,
            channel_link=link,
            channel_description=description,
            feed_name=title,
            token=token,
            actions=actions,
            board_id=board_id,
            public_board=public_board,
            get_all=get_all,user=user.key)
        feed.put()
    if user.feeds:
        if feed.key not in user.feeds:
            user.feeds.append(feed.key)
            user.put()
    else:
        user.feeds = [feed.key]
        user.put()
    return create_url(feed.key.id())

def get_feed(feed_id):
    """ Retrieve a feed from memcache or generate it if it does not exist """
    xml = memcache.get(feed_id) # In memcache?
    if xml is None:
        feed = Feed.get_by_id(int(feed_id))
        rss = None
        if feed:
            if feed.public_board:
                rss = TrelloRSS(
                    constants.KEY,
                    channel_title=feed.channel_title,
                    rss_channel_link=feed.channel_link,
                    description=feed.channel_description)
            else:
                user = feed.user.get()
                rss = TrelloRSS(
                    constants.KEY,
                    token=user.auth_token,
                    channel_title=feed.channel_title,
                    rss_channel_link=feed.channel_link,
                    description=feed.channel_description)
            if feed.get_all:
                if feed.actions:
                    rss.get_all(items=feed.actions)
                else:
                    rss.get_all()
            else:
                if feed.actions:
                    rss.get_from(feed.board_id,public_board=feed.public_board,items=feed.actions)
                else:
                    rss.get_from(feed.board_id,public_board=feed.public_board)
            xml = rss.rss
            memcache.add(key=feed_id, value=xml, time=1800) # Expire after 30 minutes
    return xml

def find_boards(user):
    """ Retrieves a  user's boards """
    trello = TrelloClient(constants.KEY, user.auth_token)
    boards = trello.list_boards()
    board_info = {}
    for board in boards:
        if board.closed is False:
            board_info[board.id] = board.name
    return board_info