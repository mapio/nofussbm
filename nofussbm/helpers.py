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

from datetime import datetime
from json import JSONEncoder, JSONDecoder

from bson.objectid import ObjectId, InvalidId

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S.%f'

ALLOWED_KEYS = set(( 'title', 'url', 'id', 'tags', 'date-added', 'date-modified' ))

def setup_json( json ):

	def object_hook( dct ):
		res = {}
		for key, value in dct.items(): 
			if key not in ALLOWED_KEYS: continue
			if key == 'id':
				try:
					res[ 'id' ] = ObjectId( value )
				except InvalidId:
					pass
			elif key == 'tags':
				res[ 'tags' ] = map( lambda _: _.strip(), value.split( ',' ) )
			elif key.startswith( 'date-' ):
				try:
					res[ key ] = datetime.strptime( value, DATETIME_FORMAT )
				except:
					pass
			else:
				res[ key ] = value
		return res

	class Encoder( JSONEncoder ):
		def default(self, obj):
			if isinstance( obj, datetime ):
				return datetime.strftime( obj, DATETIME_FORMAT )
			if isinstance( obj, ObjectId ):
				return str( obj )
			return JSONEncoder.default( self, obj )
	
	prev_dumps = json.dumps
	prev_loads = json.loads
	
	def _dumps( *args, **kwargs ):
		kwargs.update( { 'cls':  Encoder } )
		return prev_dumps( *args, **kwargs )
	def _loads( *args, **kwargs ):
		return prev_loads( *args, object_hook = object_hook, **kwargs )
	
	json.dumps = _dumps
	json.loads = _loads
