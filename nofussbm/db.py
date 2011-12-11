# Copyright 2011, Massimo Santini <santini@dsi.unimi.it>
# 
# This file is part of "No Fuss Bookmarks".
# 
# "No Fuss Bookmarks" is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
# 
# "No Fuss Bookmarks" is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
# 
# You should have received a copy of the GNU General Public License along with
# "No Fuss Bookmarks". If not, see <http://www.gnu.org/licenses/>.

from os import environ
from urlparse import urlparse

from pymongo import Connection

class DB( object ):
	def __init__( self, uri ):
		if not uri.startswith( 'mongodb://' ): uri = environ[ uri ]
		p = urlparse( uri )
		self.URI = { 
			'host': p.hostname,
			'port': p.port,
			'username': p.username,
			'password': p.password,
			'database_name': p.path[ 1: ],
			'uri': uri }
		self._conn = None
	def __collection( self, collection ):
		if not self._conn: self._conn = Connection( self.URI[ 'uri' ] )
		return self._conn[ self.URI[ 'db' ] ][ collection ]
	def __getattr__( self, collection ):
		return self.__collection( collection )
	def __getitem__( self, collection ):
		return self.__collection( collection )
	def __del__( self ):
		if self._conn: self._conn.disconnect()
