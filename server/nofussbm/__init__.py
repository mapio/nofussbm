from base64 import b64encode, b64decode
from datetime import datetime
from email.mime.text import MIMEText
from functools import wraps
from hashlib import sha1
import hmac
from logging import StreamHandler, Formatter, getLogger, DEBUG
from os import environ as ENV
from smtplib import SMTP

from flask import Flask, make_response, request, g, redirect, url_for, json

from pymongo import Connection
from pymongo.errors import OperationFailure

from .helpers import setup_json
setup_json( json ) # horrible hack to personalize decoding in Flask request.json


# Let's go!

app = Flask(__name__)


# Log to stderr (so heroku logs will pick'em up)

stderr_handler = StreamHandler()
stderr_handler.setLevel( DEBUG )
stderr_handler.setFormatter( Formatter( '%(asctime)s [%(process)s] [%(levelname)s] [Flask: %(name)s] %(message)s','%Y-%m-%d %H:%M:%S' ) )
app.logger.addHandler( stderr_handler )
app.logger.setLevel( DEBUG )


# Configure from the environment

try:
    ENV[ 'GZIPMW' ]
    from .helpers import GzipMiddleware
    extapp = GzipMiddleware( app )
    app.logger.info( 'Using GzipMiddleware')
except:
    extapp = app

class Config( object ):
	SECRET_KEY = ENV[ 'SECRET_KEY' ]
	MONGOLAB_URI = ENV[ 'MONGOLAB_URI' ]
	SENDGRID_USERNAME = ENV[ 'SENDGRID_USERNAME' ]
	SENDGRID_PASSWORD = ENV[ 'SENDGRID_PASSWORD' ]

# Utility functions

def send_mail( frm, to, subject, body ):
	msg = MIMEText( body.encode( 'utf8' ), 'plain', 'utf8' )
	msg[ 'Subject' ] = subject
	msg[ 'From' ] = frm
	msg[ 'To' ] = to
	s = SMTP( 'smtp.sendgrid.net' )
	s.login( Config.SENDGRID_USERNAME, Config.SENDGRID_PASSWORD )
	s.sendmail( frm, [ to ], msg.as_string() )
	s.quit()

def new_key( email ):
	return b64encode( '{0}:{1}'.format( email, hmac.new( Config.SECRET_KEY, email, sha1 ).hexdigest() ) )

def check_key( key ):
	try:
		email, signature = b64decode( key ).split( ':' )
	except ( TypeError, ValueError ):
		return None
	if signature == hmac.new( Config.SECRET_KEY, email, sha1 ).hexdigest():
		return email
	else:
		return None

def clean_bm( bm ):
	for key in 'id', 'email', 'date-added', 'date-modified':
		try:
			del bm[ key ]
		except KeyError:
			pass
	return bm
	
def textify( text ):
	response = make_response( text + '\n' )
	response.headers[ 'Content-Type' ] = 'text/plain; charset=UTF-8'
	return response

def myjsonify( data ):
	response = make_response( json.dumps( data, indent = 4, sort_keys = True, ensure_ascii = False ) + '\n' )
	response.headers[ 'Content-Type' ] = 'application/json; charset=UTF-8'
	return response
	
@app.before_request
def before_request():
	g.conn = Connection( Config.MONGOLAB_URI )
	g.db = g.conn[ Config.MONGOLAB_URI.split('/')[ -1 ] ]
	
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
	key = new_key( email )
	g.db.emails.insert( { 'email': email, 'key': key, 'ip': request.remote_addr, 'date': datetime.utcnow() } )
	send_mail( 'Massimo Santini <massimo.santini@gmail.com>', email, 'Your "No Fuss Bookmark" API key', 'Your key is {0}'.format( key ) )
	return ''

@app.route( '/list/<email>' )
def list( email ):
	query = { 'email': email }
	if 'tags' in request.args: 
		tags = map( lambda _: _.strip(), request.args[ 'tags' ].split( ',' ) )
		query[ 'tags' ] = { '$all': tags }
	if 'title' in request.args: 
		query[ 'title' ] = { '$regex': request.args[ 'title' ], '$options': 'i' }
	result = []
	try:
		for bm in g.db.bookmarks.find( query ):
			result.append( u'\t'.join( ( bm[ 'url' ], bm[ 'title' ], u','.join( bm[ 'tags' ] ) ) ) )
	except:
		result = []
	return textify( u'\n'.join( result ) )


# API "views"

API_PREFIX = '/api/v1'

@app.route( API_PREFIX + '/', methods = [ 'POST' ] )
@key_required
def post():
	result = { 'error': [], 'added': [] }
	for pos, bm in enumerate( request.json ):
		clean_bm( bm )
		bm[ 'email' ] = g.email
		bm[ 'date-added' ] = datetime.utcnow()
		try:
			_id = g.db.bookmarks.insert( bm, safe = True )
		except OperationFailure:
			result[ 'error' ].append( '#{0}'.format( pos ) )
		else:
			result[ 'added' ].append( _id )
	return myjsonify( result )

@app.route( API_PREFIX + '/', methods = [ 'GET' ] )
@key_required
def get():
	result = []
	try:
		for bm in g.db.bookmarks.find( { 'email': g.email } ):
			bm[ 'id' ] = bm[ '_id' ]; del bm[ '_id' ]
			del bm[ 'email' ]
			bm[ 'tags' ] = u','.join( bm[ 'tags' ] )
			result.append( bm )
	except:
		result = []
	return myjsonify( result )

@app.route( API_PREFIX + '/', methods = [ 'PUT' ] )
@key_required
def put():
	result = { 'error': [], 'updated': [], 'ignored': [] }
	for pos, bm in enumerate( request.json ):
		try:
			_id = bm[ 'id' ]
			clean_bm( bm )
			bm[ 'date-modified' ] = datetime.utcnow()
			ret = g.db.bookmarks.update( { '_id': _id, 'email': g.email }, { '$set': bm }, safe = True )
		except ( KeyError, OperationFailure ):
			result[ 'error' ].append( '#{0}'.format( pos ) )
		else:
			result[ 'error' if ret[ 'err' ] else 'updated' if ret[ 'updatedExisting' ] else 'ignored' ].append( _id )
	return myjsonify( result )

@app.route( API_PREFIX + '/', methods = [ 'DELETE' ] )
@key_required
def delete():
	result = { 'error': [], 'deleted': [], 'ignored': [] }
	for pos, bm in enumerate( request.json ):
		try:
			_id = bm[ 'id' ]
			ret = g.db.bookmarks.remove( { '_id': _id, 'email': g.email }, safe = True )
		except ( KeyError, OperationFailure ):
			result[ 'error' ].append( '#{0}'.format( pos ) )
		else:	
			result[ 'error' if ret[ 'err' ] else 'deleted' if ret[ 'n' ] else 'ignored' ].append( _id )
	return myjsonify( result )

# Delicious import hack

@app.route( API_PREFIX + '/import', methods = [ 'PUT' ] )
@key_required
def delicious_import():
	bms = []
	for line in request.data.splitlines():
		if line.startswith( '<DT>' ):
			parts = line.split( '>' )
			attrs = parts[1].split( '"' )
			bm = {
				'email': g.email,
				'date-added': datetime.utcfromtimestamp( float( attrs[ 3 ] ) ),
				'url': attrs[ 1 ], 
				'title': parts[ 2 ][ : -3 ],
				'tags': map( lambda _: _.strip(), attrs[ 7 ].split( ',' ) )
			}
			bms.append( bm )
	try:
		_id = g.db.bookmarks.insert( bms, safe = True )
	except OperationFailure:
		return textify( 'error' )
	else:
		return textify( 'success' )
