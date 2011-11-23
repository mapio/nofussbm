from base64 import b64encode, b64decode
from datetime import datetime
from functools import wraps
from hashlib import sha1
import hmac
from json import dumps
from urllib2 import unquote

from flask import Flask, make_response, request, g, redirect, url_for

from pymongo import Connection
from pymongo.errors import OperationFailure
from bson.objectid import ObjectId, InvalidId

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
	response = make_response( dumps( data, indent = 4, sort_keys = True, ensure_ascii = False ) + '\n' )
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

@app.route( '/' )
def index():
	return redirect( url_for( 'static', filename = 'signup.html' ) )

@app.route( '/getkey/<email>' )
def key( email ):
	return textify( new_key( email ) )

@app.route( '/list/<email>' )
@app.route( '/list/<email>/tag/<tags>' )
def list( email, tags = None ):
	if tags: 
		tags = map( lambda _: _.strip(), unquote( tags ).split( ',' ) )
		query = { 'email': email, 'tags' : { '$all' : tags } }
	else:
		query = { 'email': email }
	result = []
	try:
		for bm in g.db.find( query ):
			result.append( u'\t'.join( ( bm[ 'url' ], bm[ 'title' ], u','.join( bm[ 'tags' ] ) ) ) )
	except:
		result = []
	return textify( u'\n'.join( result ) )


# API "views"

API_PREFIX = '/api/v1'

@app.route( API_PREFIX + '/', methods = [ 'GET' ] )
@key_required
def get():
	result = []
	try:
		for bm in g.db.find( { 'email': g.email } ):
			bm[ 'id' ] = str( bm[ '_id' ] )
			del bm[ '_id' ]
			del bm[ 'email' ]
			result.append( bm )
	except:
		result = []
	return myjsonify( result )

@app.route( API_PREFIX + '/', methods = [ 'DELETE' ] )
@key_required
def delete():
	result = { 'error': [], 'deleted': [], 'ignored': [] }
	for pos, bm in enumerate( request.json ):
		try:
			_id = ObjectId( bm[ 'id' ] )
			ret = g.db.remove(  _id, safe = True )
		except ( KeyError, InvalidId, OperationFailure ):
			result[ 'error' ].append( '#{0}'.format( pos ) )
		else:	
			result[ 'error' if ret[ 'err' ] else 'deleted' if ret[ 'n' ] else 'ignored' ].append( str( _id ) )
	return myjsonify( result )

@app.route( API_PREFIX + '/', methods = [ 'POST' ] )
@key_required
def post():
	result = { 'error': [], 'added': [] }
	for pos, bm in enumerate( request.json ):
		bm[ 'email' ] = g.email
		bm[ 'date-added' ] = datetime.utcnow().isoformat()
		try:
			bm[ 'tags' ] = map( lambda _: _.strip(), bm[ 'tags' ].split( ',' ) ) # don't if it's already a list
		except KeyError:
			bm[ 'tags' ] = []
		try:
			del bm[ 'id' ]
		except KeyError:
			pass
		try:
			_id = g.db.insert( bm, safe = True )
		except OperationFailure:
			result[ 'error' ].append( '#{0}'.format( pos ) )
		else:
			result[ 'added' ].append( str( _id ) )
	return myjsonify( result )

@app.route( API_PREFIX + '/', methods = [ 'PUT' ] )
@key_required
def put():
	result = { 'error': [], 'updated': [], 'ignored': [] }
	for pos, bm in enumerate( request.json ):
		_id = ObjectId( bm[ 'id' ] )
		del bm[ 'id' ]
		bm[ 'email' ] = g.email
		bm[ 'date-modified' ] = datetime.utcnow().isoformat()
		try:
			ret = g.db.update( { '_id': _id  }, { '$set': bm }, safe = True )
		except 	( KeyError, InvalidId, OperationFailure ):
			result[ 'error' ].append( '#{0}'.format( pos ) )
		else:
			result[ 'error' if ret[ 'err' ] else 'updated' if ret[ 'updatedExisting' ] else 'ignored' ].append( str( _id ) )
	return myjsonify( result )
	
