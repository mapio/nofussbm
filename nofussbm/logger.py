from logging import INFO
from os import environ as ENV
from urlparse import urlparse

from log4mongo.handlers import MongoHandler, MongoFormatter

import gunicorn.glogging


MONGOLAB = urlparse( ENV[ 'MONGOLAB_URI' ] )


class Logger( gunicorn.glogging.Logger ):
	def __init__( self, cfg ):
		super( Logger, self ).__init__( cfg )
		access_handler = MongoHandler( level = INFO, host = MONGOLAB.hostname, port = MONGOLAB.port, database_name = MONGOLAB.path[ 1: ], collection = 'access-logs', username = MONGOLAB.username, password = MONGOLAB.password )
		error_handler = MongoHandler( level = INFO, host = MONGOLAB.hostname, port = MONGOLAB.port, database_name = MONGOLAB.path[ 1: ], collection = 'error-logs', username = MONGOLAB.username, password = MONGOLAB.password )
		access_handler.setFormatter( MongoFormatter() )
		error_handler.setFormatter( MongoFormatter() )
		self.access_log.addHandler( access_handler )
		self.access_log.setLevel( INFO )
		self.error_log.addHandler( error_handler )
		self.error_log.setLevel( INFO )
