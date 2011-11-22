import hmac
from hashlib import sha1
from base64 import b64encode, b64decode
from functools import wraps

from flask import Flask, make_response, request, g

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
 		email = check_key( request.headers[ 'X-Nofussbm' ] )
		g.email = email
		return f( *args, **kwargs )
	return _f

# curl -d ''  http://localhost:5000/pippo
@app.route('/', methods=['POST'])
@key_required
def post():
	if g.email:
		data = request.json
		data[ 'email' ] = g.email
		result = g.db.insert( data )
	else:
		result = 'Invalid API key'
	response = make_response( 'Bookmark id: {0}'.format( result ) )
	response.headers[ 'Content.type' ] = 'text/plain'
	return response

# curl http://localhost:5000/pippo
@app.route('/<user>', methods=['GET'])
def get( user ):
    return "get " + user

# curl -X DELETE  http://localhost:5000/pippo
@app.route('/<user>', methods=['DELETE'])
def get( user ):
    return "delete " + user

# curl -T /dev/null http://localhost:5000/pippo
@app.route('/<user>', methods=['PUT'])
def get( user ):
    return "put " + user

if __name__ == "__main__":
    app.run( debug = True )

