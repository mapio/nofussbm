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

from base64 import b64encode, b64decode
from datetime import datetime
from email.mime.text import MIMEText
from functools import wraps
from hashlib import sha1
import hmac
from logging import StreamHandler, Formatter, getLogger, DEBUG
from os import environ as ENV
import re
from smtplib import SMTP
from urlparse import parse_qs

from flask import Flask, make_response, request, g, redirect, url_for, json, abort, render_template

from pymongo import Connection
from pymongo.errors import OperationFailure, DuplicateKeyError

from .helpers import setup_json
setup_json( json ) # horrible hack to personalize decoding in Flask request.json


# Let's go!

app = Flask( __name__ )


# Log to stderr (so heroku logs will pick'em up)

stderr_handler = StreamHandler()
stderr_handler.setLevel( DEBUG )
stderr_handler.setFormatter( Formatter( '%(asctime)s [%(process)s] [%(levelname)s] [Flask: %(name)s] %(message)s','%Y-%m-%d %H:%M:%S' ) )
app.logger.addHandler( stderr_handler )
app.logger.setLevel( DEBUG )


# Configure from the environment, global (immutable) variables 

class Config( object ):
	SECRET_KEY = ENV[ 'SECRET_KEY' ]
	MONGOLAB_URI = ENV[ 'MONGOLAB_URI' ]
	SENDGRID_USERNAME = ENV[ 'SENDGRID_USERNAME' ]
	SENDGRID_PASSWORD = ENV[ 'SENDGRID_PASSWORD' ]

RANGE_RE = re.compile( r'bookmarks=(\d+)(-(\d+))?' )

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
	
def textify( text, code = 200 ):
	response = make_response( text + '\n', code )
	response.headers[ 'Content-Type' ] = 'text/plain; charset=UTF-8'
	return response

def myjsonify( data = None, code = 200, headers = None ):
	data = [] if not data else data
	response = make_response( json.dumps( data, indent = 4, sort_keys = True, ensure_ascii = False ) + '\n', code )
	response.headers[ 'Content-Type' ] = 'application/json; charset=UTF-8'
	if headers: 
		for k,v in headers.items(): response.headers[ k ] = v
	return response

def list_query( ident, limit = None ):
	args = request.args
	if '@' in ident: email = ident
	else: 
		try:
			alias = g.db.aliases.find_one( { 'alias': ident }, { 'email': 1 } )
			email = alias[ 'email' ]
		except TypeError:
			abort( 404 )
		except OperationFailure:
			abort( 500 )
	query = { 'email': email }
	if 'tags' in args: 
		tags = map( lambda _: _.strip(), args[ 'tags' ].split( ',' ) )
		query[ 'tags' ] = { '$all': tags }
	if 'title' in args: 
		query[ 'title' ] = { '$regex': args[ 'title' ], '$options': 'i' }
	if 'skip' in args:
		skip = int( args[ 'skip' ] )
	else:
		skip = 0
	if not limit:
		limit = int( args[ 'limit' ] ) if 'limit' in args else 0
	return g.db.bookmarks.find( query, skip = skip, limit = limit ).sort( [ ( 'date-modified', -1 ) ] )

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
	return render_template( 'signup.html' )

@app.route( '/favicon.ico' )
def favicon():
	return redirect( url_for( 'static', filename = 'favicon.ico' ) )

@app.route( '/<ident>' )
def list( ident ):
	result = []
	try:
		if 'html' in request.args:
			for bm in list_query( ident, 10 ):
				date = bm[ 'date-modified' ]
				result.append( ( date.strftime( '%Y-%m-%d' ), bm[ 'url' ], bm[ 'title' ], bm[ 'tags' ] ) )
			return render_template( 'list.html', bookmarks = result )
		else:
			for bm in list_query( ident ):
				date = bm[ 'date-modified' ]
				result.append( u'\t'.join( ( date.strftime( '%Y-%m-%d' ), bm[ 'url' ], bm[ 'title' ], u','.join( bm[ 'tags' ] ) ) ) )
			return textify( u'\n'.join( result ) )
	except OperationFailure:
		abort( 500 )

@app.route( '/stats' )
def stats():
	result = {}
	try:
		result[ 'users' ] = g.db.bookmarks.group( { 'email': 1 }, None, { 'count': 0 }, 'function( o, p ){ p.count++; }' )
	except OperationFailure:
		abort( 500 )
	return myjsonify( result )
	
# API "views"

API_PREFIX = '/api/v1'

@app.route( API_PREFIX + '/', methods = [ 'POST' ] )
@key_required
def post():
	code = 200
	result = { 'error': [], 'added': [] }
	for pos, bm in enumerate( request.json ):
		clean_bm( bm )
		bm[ 'email' ] = g.email
		bm[ 'date-added' ] = bm[ 'date-modified' ] = datetime.utcnow()
		try:
			_id = g.db.bookmarks.insert( bm, safe = True )
		except OperationFailure:
			result[ 'error' ].append( '#{0}'.format( pos ) )
			code = 500
		else:
			result[ 'added' ].append( _id )
	return myjsonify( result, code )

@app.route( API_PREFIX + '/', methods = [ 'GET' ] )
@key_required
def get():
	result = []

	skip = limit = 0
	if 'Range' in request.headers:
		m = RANGE_RE.match( request.headers[ 'Range' ] )
		if m:
			m = m.groups()
			skip = int( m[ 0 ] )
			limit = int( m[ 2 ] ) - skip + 1 if m[ 2 ] else 0 
		if not m or limit < 0: abort( 416 )

	query = { 'email': g.email }
	if 'X-Nofussbm-query' in request.headers:
		args = parse_qs( request.headers[ 'X-Nofussbm-query' ] )
		if 'tags' in args: 
			tags = map( lambda _: _.strip(), args[ 'tags' ][ 0 ].split( ',' ) )
			query[ 'tags' ] = { '$all': tags }
		if 'title' in args: 
			query[ 'title' ] = { '$regex': args[ 'title' ][ 0 ], '$options': 'i' }

	try:
		cur = g.db.bookmarks.find( query, skip = skip, limit = limit )
		n = cur.count()
		for bm in cur:
			bm[ 'id' ] = bm[ '_id' ]; del bm[ '_id' ]
			del bm[ 'email' ]
			bm[ 'tags' ] = u','.join( bm[ 'tags' ] )
			result.append( bm )
	except OperationFailure:
		abort( 500 )
	return myjsonify( result, headers = { 'Content-Range': 'bookmarks {0}-{1}/{2}'.format( skip, skip + ( limit - 1 if limit else n ), n ), 'Accept-Ranges': 'bookmarks' } )

@app.route( API_PREFIX + '/', methods = [ 'PUT' ] )
@key_required
def put():
	result = { 'error': [], 'updated': [], 'ignored': [] }
	code = 200
	for pos, bm in enumerate( request.json ):
		try:
			_id = bm[ 'id' ]
			clean_bm( bm )
			bm[ 'date-modified' ] = datetime.utcnow()
			ret = g.db.bookmarks.update( { '_id': _id, 'email': g.email }, { '$set': bm }, safe = True )
		except ( KeyError, OperationFailure ):
			result[ 'error' ].append( '#{0}'.format( pos ) )
			code = 500
		else:
			result[ 'error' if ret[ 'err' ] else 'updated' if ret[ 'updatedExisting' ] else 'ignored' ].append( _id )
	return myjsonify( result, code )

@app.route( API_PREFIX + '/', methods = [ 'DELETE' ] )
@key_required
def delete():
	result = { 'error': [], 'deleted': [], 'ignored': [] }
	code = 200
	for pos, bm in enumerate( request.json ):
		try:
			_id = bm[ 'id' ]
			ret = g.db.bookmarks.remove( { '_id': _id, 'email': g.email }, safe = True )
		except ( KeyError, OperationFailure ):
			result[ 'error' ].append( '#{0}'.format( pos ) )
			code = 500
		else:	
			result[ 'error' if ret[ 'err' ] else 'deleted' if ret[ 'n' ] else 'ignored' ].append( _id )
	return myjsonify( result, code )

# signup and alias helpers

@app.route( API_PREFIX + '/sendkey', methods = [ 'POST' ] )
def sendkey():
	email = request.form[ 'email' ]
	key = new_key( email )
	g.db.emails.insert( { 'email': email, 'key': key, 'ip': request.remote_addr, 'date': datetime.utcnow() } )
	try:
		send_mail( 'Massimo Santini <massimo.santini@gmail.com>', email, 'Your "No Fuss Bookmark" API key', 'Your key is {0}'.format( key ) )
	except:
		abort( 500 )
	return ''

@app.route( API_PREFIX + '/setalias/<alias>', methods = [ 'POST' ] )
@key_required
def setalias( alias ):
	result = {}
	code = 200
	try:
		old = g.db.aliases.find_and_modify( { 'email': g.email }, { '$set': { 'alias' : alias } }, upsert = True )
		if 'alias' in old: result[ 'old' ] = old[ 'alias' ]
		result[ 'status' ] = 'set'
	except OperationFailure:
		error = g.db.error()
		if 'err' in error and 'duplicate' in error[ 'err' ]: 
			result[ 'status' ] = 'duplicate'
		else:
			code = 500
			result[ 'status' ] = 'server error'
		return myjsonify( result )
	return myjsonify( result, code )

# Delicious import hack

@app.route( API_PREFIX + '/import', methods = [ 'PUT' ] )
@key_required
def delicious_import():
	bms = []
	for line in request.data.splitlines():
		if line.startswith( '<DT>' ):
			parts = line.split( '>' )
			attrs = parts[1].split( '"' )
			date = datetime.utcfromtimestamp( float( attrs[ 3 ] ) )
			bm = {
				'email': g.email,
				'date-added': date,
				'date-modified': date,
				'url': attrs[ 1 ], 
				'title': parts[ 2 ][ : -3 ],
				'tags': map( lambda _: _.strip(), attrs[ 7 ].split( ',' ) )
			}
			bms.append( bm )
	try:
		_id = g.db.bookmarks.insert( bms, safe = True )
	except OperationFailure:
		abort( 500 )
	else:
		return textify( 'success' )
