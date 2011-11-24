from datetime import datetime
import gzip
from json import JSONEncoder, JSONDecoder
import StringIO

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
			if key == 'tags':
				res[ 'tags' ] = map( lambda _: _.strip(), value.split( ',' ) )
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


class GzipMiddleware(object):
	def __init__(self, app, compresslevel=9):
		self.app = app
		self.compresslevel = compresslevel

	def __call__(self, environ, start_response):
		if 'gzip' not in environ.get('HTTP_ACCEPT_ENCODING', ''):
			return self.app(environ, start_response)
		if environ['PATH_INFO'][-3:] != '.js' and environ['PATH_INFO'][-4:] != '.css':
			return self.app(environ, start_response)
		buffer = StringIO.StringIO()
		output = gzip.GzipFile(
			mode='wb',
			compresslevel=self.compresslevel,
			fileobj=buffer
		)

		start_response_args = []
		def dummy_start_response(status, headers, exc_info=None):
			start_response_args.append(status)
			start_response_args.append(headers)
			start_response_args.append(exc_info)
			return output.write

		app_iter = self.app(environ, dummy_start_response)
		for line in app_iter:
			output.write(line)
		if hasattr(app_iter, 'close'):
			app_iter.close()
		output.close()
		buffer.seek(0)
		result = buffer.getvalue()
		headers = []
		for name, value in start_response_args[1]:
			if name.lower() != 'content-length':
				 headers.append((name, value))
		headers.append(('Content-Length', str(len(result))))
		headers.append(('Content-Encoding', 'gzip'))
		start_response(start_response_args[0], headers, start_response_args[2])
		buffer.close()
		return [result]
