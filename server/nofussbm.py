import hmac
from hashlib import sha1
from base64 import b64encode, b64decode
from functools import wraps
from json import dumps

from flask import Flask, make_response, request, g

from pymongo import Connection
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = 'a well kept secret'


def new_key( email ):
	return b64encode( '{0}:{1}'.format( email, hmac.new( app.secret_key, email, sha1 ).hexdigest() ) )

def check_key( key ):
	try:
		email, signature = b64decode( key ).split( ':' )
	except ( TypeError, ValueError ):
		return None
	if signature == hmac.new( app.secret_key, email, sha1 ).hexdigest():
		return email
	else:
		return None

def textify( text ):
	response = make_response( text + '\n' )
	response.headers[ 'Content-Type' ] = 'text/plain; charset=UTF-8'
	return response

def myjsonify( data ):
	response = make_response( dumps( data, indent = 4, ensure_ascii = False ) + '\n' )
	response.headers[ 'Content-Type' ] = 'application/json; charset=UTF-8'
	return response
	
@app.before_request
def before_request():
	g.conn = Connection( 'mongodb://test:pippo@dbh45.mongolab.com:27457/test' )
	g.db = g.conn[ 'test' ][ 'urls' ]
	
@app.teardown_request
def teardown_request( exception ):
	g.conn.disconnect()

def key_required( f ):
	@wraps( f )
	def _f( *args, **kwargs ):
		try:
 			email  = check_key( request.headers[ 'X-Nofussbm-Key' ] )
		except KeyError:
			email = None
		if email:
			g.email = email
			return f( *args, **kwargs )
		else:
			response = make_response( 'Missing HTTP header X-Nofussbm-Key', 403 )
			response.headers[ 'Content-Type' ] = 'text/plain'
			return response
	return _f


# Public "views"

@app.route('/key/<email>')
def key( email ):
	return textify( new_key( email ) )


# API "views"

API_PREFIX = '/api/v1'

@app.route( API_PREFIX + '/', methods = [ 'GET' ] )
@key_required
def get():
	result = []
	for bm in g.db.find( { 'email': g.email } ):
		bm[ 'id' ] = str( bm[ '_id' ] )
		del bm[ '_id' ]
		del bm[ 'email' ]
		result.append( bm )
	return myjsonify( result )

@app.route( API_PREFIX + '/', methods = [ 'DELETE' ] )
@key_required
def delete():
	result = { 'error': [], 'deleted': [], 'ignored': [] }
	for bm in request.json:
		_id = ObjectId( bm[ 'id' ] )
		ret = g.db.remove( _id, safe = True )
		result[ 'error' if ret[ 'err' ] else 'deleted' if ret[ 'n' ] else 'ignored' ].append( str( _id ) )
	return myjsonify( result )

@app.route( API_PREFIX + '/', methods = [ 'POST' ] )
@key_required
def post():
	data = request.json
	data[ 'email' ] = g.email
	result = 'Bookmark id: {0}'.format( g.db.insert( data ) )
	return textify( result )

@app.route( API_PREFIX + '/', methods = [ 'PUT' ] )
@key_required
def put():
	result = { 'error': [], 'updated': [], 'ignored': [] }
	for bm in request.json:
		_id = ObjectId( bm[ 'id' ] )
		del bm[ 'id' ]
		bm[ 'email' ] = g.email
		ret = g.db.update( { '_id': _id  }, { '$set': bm }, safe = True )
		result[ 'error' if ret[ 'err' ] else 'updated' if ret[ 'updatedExisting' ] else 'ignored' ].append( str( _id ) )
	return myjsonify( result )

if __name__ == "__main__":
	app.run( debug = True )

