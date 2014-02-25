import webapp2
import os
import logging
import Cookie
from lib import utils
from google.appengine.api import capabilities
from google.appengine.api import users
from urllib import urlencode
from lib import counters
from lib import constants


class Handler(webapp2.RequestHandler):
    """ Base class to handle template rendering. """

    def write(self, *a, **kw):
        """ Just write plain text to the screen """
        self.response.out.write(*a, **kw)

    def _render_str(self, template, ** params):
        """
        Render the actual template; there was a bug with text not being properly
        utf-8 encoded that I'm fixing quickly here. Need to find a more elegant solution;
        not sure of the performance hit of doing it this way.

        """

        for key in params:
            if(isinstance(params[key], str)):
                params[key] = params[key].decode('utf-8')
            if(isinstance(params[key], dict)):
                for sub_key in params[key]:
                    if(isinstance(params[key][sub_key], str)):
                        params[key][sub_key] = params[key][sub_key].decode('utf-8')
        t = constants.JINJA_ENV.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        """ Render a template, with **kw to be passed to Jinja """
        self.write(self._render_str(template, **kw))


class MainHandler(Handler):
    """ Handles / """

    def get(self):
        user = users.get_current_user()
        if user:
            user_obj = utils.get_user(user)
            feeds = utils.get_feeds(user_obj.feeds)
            if user_obj.auth_token: # User has an auth token
                if(utils.verify_token(user_obj.auth_token)): # User's auth token is valid
                    self.render('profile.html', signout=constants.SIGNOUT,feeds=feeds)
                else: # User's auth token is out of date
                    self.redirect('/reauth')
            else: # User has no auth token
                self.render('profile.html', signout=constants.SIGNOUT,feeds=feeds)
        else:
            login_url = users.create_login_url(self.request.uri)
            self.render('index.html', login=login_url)

    def post(self):
        """ Posts to this page handle feed deletions """
        user = users.get_current_user()
        if user:
            user_obj = utils.get_user(user)
            args = self.request.arguments()
            feeds = [x for x in args if x != 'delete' and x != 'modify']
            delete = self.request.get('delete')
            if delete:
                utils.delete_feeds(feeds, user_obj)
        self.redirect('/')
      

class Public(Handler):
    """ Handles /publicfeeds """

    def get(self):
        user = users.get_current_user()
        if user:
            self.render('public.html',link="http://trello.com",actions=constants.ACTIONS,signout=constants.SIGNOUT)
        else:
            self.redirect('/')

    def post(self):
        user = users.get_current_user()
        if not user:
            self.redirect('/')
        else:
            board_id = self.request.get('board')
            title = self.request.get('title')
            link = self.request.get('link')
            description = self.request.get('description')
            actions = [x for x in constants.ACTIONS if self.request.get(x)]

            if actions:
                board_id, link, errors = utils.validate_input(board_id, link)
                if errors:
                    self.render('public.html', id=board_id, link=link, errors=errors, actions=constants.ACTIONS, signout=constants.SIGNOUT)
                else:
                    feed_url = utils.create_feed(
                        user,board_id,
                        title,link,
                        description,
                        actions,
                        public_board=True,
                        get_all=False,
                        token=None
                    )
                    self.render('congrats.html',feed_url=feed_url,signout=constants.SIGNOUT)
            else: # They didn't mark any of the checkboxes
                self.render('public.html',check_error=True,actions=constants.ACTIONS,signout=constants.SIGNOUT)


class Private(Handler):
    def get(self):
        user = users.get_current_user()
        if user:
            user_obj =  utils.get_user(user)
            user_boards = None
            if user_obj.auth_token is None: # We need an auth token for this user
                args = constants.TOKEN_ARGS
                auth_url = "https://trello.com/1/authorize?%s" % urlencode(args)
                self.render('private.html', actions=constants.ACTIONS, auth_url=auth_url, signout=constants.SIGNOUT)
            else: 
                user_boards = utils.find_boards(user_obj)
                self.render('private.html',
                    actions=constants.ACTIONS,
                    user_boards=user_boards,
                    link="http://trello.com",
                    title="My Trello RSS",
                    description="My Trello RSS Feed",
                    signout=constants.SIGNOUT)
        else:
            self.redirect('/')


    def post(self):
        """
        Handles adding tokens and creating private boards.
        TODO: Refactor this into a couple of handlers, and include the public board handling as well
        to make the code more succinct and extensible. This method is too long and unwieldy.

        """

        token = self.request.get('token')
        user = users.get_current_user()
        if not user:
            self.redirect('/')
        user_obj = utils.get_user(user)
        if token: # Adding a token for a user
            if utils.verify_token(token):
                user_obj.auth_token = token
                user_obj.put()
                self.redirect('/privatefeeds')
            else:
                args = constants.TOKEN_ARGS
                auth_url = "https://trello.com/1/authorize?%s" % urlencode(args)
                self.render('private.html',
                    actions=constants.ACTIONS,
                    incorrect_token=True,
                    auth_url=auth_url,
                    signout=constants.SIGNOUT)
        else: # Adding a board for a user
            board_id = self.request.get('board')
            title = self.request.get('title')
            link = self.request.get('link')
            description = self.request.get('description')
            actions = [x for x in constants.ACTIONS if self.request.get(x)]

            if actions:
                get_all = False
                if board_id == 'all':
                    get_all = True
                    board_id = None
                feed_url = utils.create_feed(
                    user,board_id,
                    title,link,
                    description,actions,
                    public_board=False,
                    get_all=get_all,
                    token=user_obj.auth_token)
                self.render('congrats.html',feed_url=feed_url,signout=constants.SIGNOUT)
            else: # They missed some required info
                user_boards = utils.find_boards(user_obj)
                self.render('private.html',
                    actions=constants.ACTIONS,
                    check_error=True,
                    user_boards=user_boards,
                    link=link,
                    description=description,
                    title=title,
                    signout=constants.SIGNOUT)


class Feeds(Handler):
    """ Just retrieves and prints a feed """

    def get(self, feed_id):
        self.write(utils.get_feed(feed_id))


class LogoutPage(Handler):
    """
    Logout from this app only, not all of Google:
    http://ptspts.blogspot.ca/2011/12/how-to-log-out-from-appengine-app-only.html

    """

    def get(self):
        target_url = self.request.referer or '/'
        if os.environ.get('SERVER_SOFTWARE', '').startswith('Development/'):
          self.redirect(users.create_logout_url(target_url))
          return

        # On the production instance, we just remove the session cookie, because
        # redirecting users.create_logout_url(...) would log out of all Google
        # (e.g. Gmail, Google Calendar).
        #
        # It seems that AppEngine is setting the ACSID cookie for http:// ,
        # and the SACSID cookie for https:// . We just unset both below.
        cookie = Cookie.SimpleCookie()
        cookie['ACSID'] = ''
        cookie['ACSID']['expires'] = -86400  # In the past, a day ago.
        self.response.headers.add_header(*cookie.output().split(': ', 1))
        cookie = Cookie.SimpleCookie()
        cookie['SACSID'] = ''
        cookie['SACSID']['expires'] = -86400
        self.response.headers.add_header(*cookie.output().split(': ', 1))
        self.redirect(target_url) 


class Reauth(Handler):
    """When a token expires or was revoked, this is used to reauthorizes said user"""

    def get(self):
        user = users.get_current_user()
        if user:
            user_obj = utils.get_user(user)
            if(utils.verify_token(user_obj.auth_token)):
                self.redirect('/')
            else:
                args = constants.TOKEN_ARGS
                auth_url = "https://trello.com/1/authorize?%s" % urlencode(args)
                self.render('reauth.html',auth_url=auth_url,signout=constants.SIGNOUT)
        else:
            self.redirect('/')

    def post(self):
        token = self.request.get('token')
        user = users.get_current_user()
        if not user:
            self.redirect('/')
        user_obj = utils.get_user(user)
        if token:
            if(utils.verify_token(token)):
                user_obj.auth_token = token
                user_obj.put()
                self.redirect('/')
            else:
                args = constants.TOKEN_ARGS
                auth_url = "https://trello.com/1/authorize?%s" % urlencode(args)
                self.render('reauth.html',incorrect_token=True,auth_url=auth_url,signout=constants.SIGNOUT)
        else:
            self.redirect('/')


FEED_RE = r'(.*)'
app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/publicfeeds', Public),
    ('/feed/' + FEED_RE, Feeds),
    ('/privatefeeds', Private),
    ('/logout', LogoutPage),
    ('/reauth', Reauth),
], debug=False)