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
from lib import utils
from lib import feeds
from google.appengine.api import users
from datetime import datetime, timedelta
from urllib import urlencode

jinja_environment = jinja2.Environment(autoescape=True,
	loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))

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
    	user = users.get_current_user()

    	if user:
    		signout = users.create_logout_url('/')
    		user_db = utils.get_user(user)
    		feeds = utils.get_feeds(user_db.feeds)

    		self.render('profile.html', signout=signout,feeds=feeds)
        else:
        	login_url = users.create_login_url(self.request.uri)
        	self.render('index.html', login=login_url)
      

class Public(Handler):
	def get(self):
		user = users.get_current_user()
		if user:
			user_db = utils.get_user(user)
			self.render('public.html',link="http://trello.com")
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
			comments = self.request.get('comments')
			cards = self.request.get('cards')
			boards = self.request.get('boards')
			lists = self.request.get('lists')
	
			if comments == '' and cards == '' and boards == '' and lists == '':
				self.render('public.html',check_error=True)
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
				board_id, link, errors = utils.validate_input(board_id,link)
		
				if len(errors) > 0:
					self.render('public.html',id=board_id,link=link,errors=errors)
				else:
					feed_url = utils.create_feed(user,board_id,title,link,description,actions,
						public_board=True,get_all=False,token=None)
					self.render('congrats.html',feed_url=feed_url)

	

class Authorize(Handler):
	def get(self):
		pass

	def post(self):
		pass


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
				self.render('private.html', auth_url=auth_url)
			else:
				self.render('private.html',user_boards=user_boards,link="http://trello.com")

	def post(self):
		token = self.request.get('token')
		user = users.get_current_user()
		if not user:
			self.redirect('/')
		user_obj = utils.get_user(user)
		if token:	
			user_obj.auth_token = token
			user_obj.token_expiration = datetime.now() + timedelta(days=30)
			user_obj.put()
			self.redirect('/privatefeeds')
		else:
			board = self.request.get('board')
			channel_title = self.request.get('title')
			channel_link = self.request.get('link')
			description = self.request.get('description')
			comments = self.request.get('comments')
			cards = self.request.get('cards')
			boards = self.request.get('boards')
			lists = self.request.get('lists')
			actions = []
			if comments == '' and cards == '' and boards == '' and lists == '':
				logging.error('fdsfsd')
				self.redirect('/privatefeeds')
			if comments != '':
				actions.append('comments')
			if cards != '':
				actions.append('cards')					
			if boards != '':
				actions.append('boards')					
			if lists != '':
				actions.append('lists')
			get_all = False
			if board == 'all':
				get_all = True
				board = None
			feed_url = utils.create_feed(user,board,channel_title,channel_link,description,actions,
				public_board=False,get_all=False,token=user_obj.auth_token)
			self.render('congrats.html',feed_url=feed_url)

			



FEED_RE = r'(.*)'
app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/publicfeeds', Public),
    ('/authorize', Authorize),
    ('/feed/' + FEED_RE, Feeds),
    ('/privatefeeds', Private),
    ('/testbed', TestBed)
], debug=True)