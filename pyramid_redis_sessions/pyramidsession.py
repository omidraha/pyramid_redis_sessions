import os
import time
import cPickle
import binascii
from pyramid.compat import text_
from zope.interface import implementer

from .util import persist

from .redisdict import RedisDict

from pyramid.interfaces import ISession

@implementer(ISession)
class PyramidRedis(RedisDict):
    """ Implements the Pyramid ISession interface and is returned by
    the RedisSessionFactory.

    Inherits from ``RedisDict`` to implement the required ``IDict``
    interface. Note: an upcoming change will likely merge ``PyramidRedis`` and
    ``RedisDict`` into a single class to reduce shared code and keep them
    from being dependent on each other in unexpected ways.
    """
    def __init__(self, redis, session_id, timeout, delete_cookie,
                 encode=cPickle.dumps, decode=cPickle.loads):
        self.session_id = session_id
        self.redis = redis
        self.timeout = timeout
        self.encode = encode
        self.decode = decode
        self.delete_cookie = delete_cookie
        self.created = time.time()
        self.managed_dict = self.from_redis() # required for ``RedisDict``

    def invalidate(self):
        """ Delete all keys unique to this session and expire cookie."""
        self.clear()
        self.delete_cookie()

    @property
    def new(self):
        return getattr(self, '_v_new', False)

    @persist
    def changed(self):
        """ Persists the working dict immediately with ``@persist``."""
        pass

    def new_csrf_token(self):
        token = text_(binascii.hexlify(os.urandom(20)))
        self['_csrft_'] = token
        return token

    def get_csrf_token(self):
        token = self.get('_csrft_', None)
        if token is None:
            token = self.new_csrf_token()
        else:
            token = unicode(token)
        return token

    def flash(self, msg, queue='', allow_duplicate=True):
        """ This method modifies a mutable value (appending to a list) and needs
        to call ``self.changed()`` to ensure the changes are sent to redis. """
        storage = self.setdefault('_f_' + queue, [])
        if allow_duplicate or (msg not in storage):
            storage.append(msg)
            self.changed()

    def peek_flash(self, queue=''):
        storage = self.get('_f_' + queue, [])
        return storage

    def pop_flash(self, queue=''):
        storage = self.pop('_f_' + queue, [])
        return storage
