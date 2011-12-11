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

from logging import INFO

import gunicorn.glogging
from log4mongo.handlers import MongoHandler, MongoFormatter

from .db import DB

class Logger( gunicorn.glogging.Logger ):
	def __init__( self, cfg ):
		super( Logger, self ).__init__( cfg )
		access_handler = MongoHandler( level = INFO, collection = 'access-logs', **DB( 'MONGOLAB_URI' ).URI )
		error_handler = MongoHandler( level = INFO, collection = 'error-logs', **DB( 'MONGOLAB_URI' ).URI )
		access_handler.setFormatter( MongoFormatter() )
		error_handler.setFormatter( MongoFormatter() )
		self.access_log.addHandler( access_handler )
		self.access_log.setLevel( INFO )
		self.error_log.addHandler( error_handler )
		self.error_log.setLevel( INFO )
