# http://blog.yjl.im/2011/02/simple-counter-for-google-app-engine.html

from google.appengine.ext import db, ndb
from google.appengine.api import taskqueue
from google.appengine.api import memcache
from datetime import datetime
from google.appengine.ext import deferred 
import time
import webapp2
from time import gmtime
import logging


class SimpleCounter(ndb.Model):

  name = ndb.StringProperty(required=True)
  count = ndb.IntegerProperty(required=True)
  added = ndb.DateTimeProperty(auto_now_add=True)
  updated = ndb.DateTimeProperty(auto_now=True)


def pingpong_incr(key_name):

  # Changing slot every 10 minutes
  slot = gmtime().tm_min / 10 % 2
  # A bug with initial value: http://code.google.com/p/googleappengine/issues/detail?id=2012
  if memcache.incr('%s_%s' % (key_name, slot), namespace='ia') is None:
	# Can set no such key existed
	memcache.set('%s_%s' % (key_name, slot), 1, namespace='ia')


def pingpong_get(key_name, from_ping=True):

  if from_ping:
	slot = gmtime().tm_min / 10 % 2
  else:
	slot = (gmtime().tm_min + 10) / 10 % 2
  return memcache.get('%s_%s' % (key_name, slot), namespace='ia')


def pingpong_delete(key_name):

  slot = (gmtime().tm_min + 10) / 10 % 2
  memcache.delete('%s_%s' % (key_name, slot), namespace='ia')