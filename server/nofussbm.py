import hmac
from hashlib import sha1
from base64 import b64encode, b64decode
from functools import wraps
from json import dumps

from flask import Flask, make_response, request, g, jsonify

from pymongo import Connection

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

@app.before_request
def before_request():
    g.db = Connection( 'mongodb://test:pippo@dbh45.mongolab.com:27457/test' )[ 'test' ][ 'urls' ]

def key_required( f ):
	@wraps( f )
	def _f( *args, **kwargs ):
 		g.email  = check_key( request.headers[ 'X-Nofussbm' ] )
		return f( *args, **kwargs )
	return _f

@app.route('/', methods = [ 'POST' ] )
@key_required
def post():
	if g.email:
		data = request.json
		data[ 'email' ] = g.email
		result = 'Bookmark id: {0}'.format( g.db.insert( data ) )
	else:
		result = 'Invalid API key'
	response = make_response( result )
	response.headers[ 'Content.type' ] = 'text/plain'
	return response

@app.route('/', methods = [ 'GET' ] )
@key_required
def get():
	result = [ { 'id': str( bm[ '_id' ] ), 'url': bm[ 'url'], 'title': bm[ 'title' ], 'tags': bm[ 'tags' ] } for bm in g.db.find( { 'email': g.email } ) ]
	response = make_response( dumps( result ) )
	response.headers[ 'Content.type' ] = 'application/json'
	return response

@app.route('/key/<email>')
def key( email ):
	response = make_response( new_key( email ) + '\n' )
	response.headers[ 'Content.type' ] = 'text/plain'
	return response

if __name__ == "__main__":
	app.run( debug = True )

