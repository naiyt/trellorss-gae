#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import jinja2
import os
import re
import logging
import Cookie
import os
from lib import utils
from lib import feeds
from google.appengine.api import capabilities
from google.appengine.api import users
from datetime import datetime, timedelta
from urllib import urlencode
from lib import counters

jinja_environment = jinja2.Environment(autoescape=True,
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))

signout = "/logout"

class Handler(webapp2.RequestHandler):
    """Base class that handles writing and rendering (from Steve Huffman, CS 253)"""
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, ** params):
        t = jinja_environment.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

class MainHandler(Handler):
    def get(self):
        counters.pingpong_incr('hits')
        user = users.get_current_user()

        if user:
            user_db = utils.get_user(user)
            feeds = utils.get_feeds(user_db.feeds)

            self.render('profile.html', signout=signout,feeds=feeds)
        else:
            login_url = users.create_login_url(self.request.uri)
            self.render('index.html', login=login_url)

    def post(self):
        counters.pingpong_incr('hits')
        user = users.get_current_user()
        user_db = None
        if user:
            user_db = utils.get_user(user)
        else:
            self.redirect('/')
        args = self.request.arguments()
        feeds = []
        for arg in args:
            if arg != 'delete' and arg != 'modify':
                feeds.append(arg)
        delete = self.request.get('delete')
        modify = self.request.get('modify')
        if delete == '' and modify == '':
            self.redirect('/')
        if delete != '':
            utils.delete_feeds(feeds,user_db)
            self.redirect('/')
        elif modify != '':
            self.render('modify.html')

      

class Public(Handler):
    def get(self):
        counters.pingpong_incr('hits')
        user = users.get_current_user()
        if user:
            user_db = utils.get_user(user)
            self.render('public.html',link="http://trello.com",signout=signout)
        else:
            self.redirect('/')

    def post(self):
        counters.pingpong_incr('hits')
        user = users.get_current_user()
        if not user:
            self.redirect('/')
        else:
            board_id = self.request.get('board')
            title = self.request.get('title')
            link = self.request.get('link')
            description = self.request.get('description')
            comments = self.request.get('comments')
            cards = self.request.get('cards')
            boards = self.request.get('boards')
            lists = self.request.get('lists')
            checklists = self.request.get('checklists')
    
            if comments == '' and cards == '' and boards == '' and lists == '':
                self.render('public.html',check_error=True,signout=signout)
            else:
                actions = []
                if comments != '':
                    actions.append('comments')
                if cards != '':
                    actions.append('cards')                 
                if boards != '':
                    actions.append('boards')                    
                if lists != '':
                    actions.append('lists')
                if checklists != '':
                    actions.append('createChecklist')
                    actions.append('updateCheck')
                board_id, link, errors = utils.validate_input(board_id,link)
        
                if len(errors) > 0:
                    self.render('public.html',id=board_id,link=link,errors=errors,signout=signout)
                else:
                    feed_url = utils.create_feed(user,board_id,title,link,description,actions,
                        public_board=True,get_all=False,token=None)
                    self.render('congrats.html',feed_url=feed_url,signout=signout)

class Feeds(Handler):
    def get(self, feed_id):
        self.write(utils.get_feed(feed_id))

    def post(self):
        pass

class TestBed(Handler):
    def get(self):
        pass

class Private(Handler):
    def get(self):
        counters.pingpong_incr('hits')
        user = users.get_current_user()
        if not user:
            self.redirect('/')
        else:
            user =  utils.get_user(user)
            auth_user = False
            user_boards = None
            if user.auth_token:
                if user.token_expiration > datetime.now():
                    user_boards = utils.find_boards(user)
                else:
                    auth_user = True
            else:
                auth_user = True
            if auth_user:
                args = {'response_type': 'token', 'key': utils.key, 'scope': 'read', 'expiration': '30days','name': 'TrelloRSS'}
                auth_url = "https://trello.com/1/authorize?%s" % urlencode(args)
                self.render('private.html',auth_url=auth_url,signout=signout)
            else:
                self.render('private.html',user_boards=user_boards,link="http://trello.com",
                    title="My Trello RSS", description="My Trello RSS Feed",signout=signout)

    def post(self):
        counters.pingpong_incr('hits')
        token = self.request.get('token')
        user = users.get_current_user()
        if not user:
            self.redirect('/')
        user_obj = utils.get_user(user)
        if token:
            if(utils.verify_token(token)):
                user_obj.auth_token = token
                user_obj.token_expiration = datetime.now() + timedelta(days=30)
                user_obj.put()
                self.redirect('/privatefeeds')
            else:
                args = {'response_type': 'token', 'key': utils.key, 'scope': 'read', 'expiration': '30days','name': 'TrelloRSS'}
                auth_url = "https://trello.com/1/authorize?%s" % urlencode(args)
                self.render('private.html',incorrect_token=True,auth_url=auth_url,signout=signout)
        else:
            board = self.request.get('board')
            channel_title = self.request.get('title')
            channel_link = self.request.get('link')
            description = self.request.get('description')
            comments = self.request.get('comments')
            cards = self.request.get('cards')
            boards = self.request.get('boards')
            lists = self.request.get('lists')
            checklists = self.request.get('checklists')

            actions = []
            if comments == '' and cards == '' and boards == '' and lists == '':
                user_boards = None
                if user_obj.token_expiration > datetime.now():
                    user_boards = utils.find_boards(user_obj)
                self.render('private.html',check_error=True,user_boards=user_boards,link=channel_link,
                    description=description,title=channel_title,signout=signout)
            else:
                if comments != '':
                    actions.append('comments')
                if cards != '':
                    actions.append('cards')                 
                if boards != '':
                    actions.append('boards')                    
                if lists != '':
                    actions.append('lists')
                if checklists != '':
                    actions.append('createChecklist')
                    actions.append('updateCheck')
                get_all = False
                if board == 'all':
                    get_all = True
                    board = None
                feed_url = utils.create_feed(user,board,channel_title,channel_link,description,actions,
                    public_board=False,get_all=False,token=user_obj.auth_token)
                self.render('congrats.html',feed_url=feed_url,signout=signout)



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


class UpdateStatsCron(Handler):

  def update_counter(self, key_name):

    # Checking memory cache
    count = counters.pingpong_get(key_name, from_ping=False)
    if not count:
      return

    counter = counters.SimpleCounter.get_by_id(key_name)
    if not counter:
      counter = counters.SimpleCounter(id=key_name, name=key_name, count=count)
    else:
      counter.count += count
    counter.put()
    counters.pingpong_delete(key_name)

  def get(self):

    if capabilities.CapabilitySet('datastore_v3', capabilities=['write']).is_enabled() \
        and capabilities.CapabilitySet('memcache').is_enabled():
        self.update_counter('hits')


FEED_RE = r'(.*)'
app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/publicfeeds', Public),
    ('/feed/' + FEED_RE, Feeds),
    ('/privatefeeds', Private),
    ('/logout', LogoutPage),
    ('/testbed', TestBed),
    ('/stats-update', UpdateStatsCron)
], debug=False)