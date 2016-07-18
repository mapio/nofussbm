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

import hmac
import re

from base64 import b64encode, b64decode
from datetime import datetime
from functools import wraps
from hashlib import sha1
from urlparse import parse_qs

from flask import Blueprint, make_response, request, g, json, abort
from pymongo.errors import OperationFailure, DuplicateKeyError

from . import Config, mongo
from .helpers import send_mail, to_id, query_from_dict


api = Blueprint( 'api', __name__ )

RANGE_RE = re.compile( r'bookmarks=(\d+)(-(\d+))?' )


def myjsonify( data = None, code = 200, headers = None ):
	data = [] if not data else data
	response = make_response( json.dumps( data, indent = 4, sort_keys = True, ensure_ascii = False ) + '\n', code )
	response.headers[ 'Content-Type' ] = 'application/json; charset=UTF-8'
	if headers:
		for k,v in headers.items(): response.headers[ k ] = v
	return response


# Helpers

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


# Views

@api.route( '/', methods = [ 'POST' ] )
@key_required
def post():
	code = 200
	result = { 'error': [], 'added': [] }
	for pos, bm in enumerate( request.json ):
		clean_bm( bm )
		bm[ 'email' ] = g.email
		bm[ 'date-added' ] = bm[ 'date-modified' ] = datetime.utcnow()
		try:
			_id = mongo.db.bookmarks.insert( bm )
		except OperationFailure:
			result[ 'error' ].append( '#{0}'.format( pos ) )
			code = 500
		else:
			result[ 'added' ].append( _id )
	return myjsonify( result, code )

@api.route( '/', methods = [ 'GET' ] )
@api.route( '/<bid>', methods = [ 'GET' ] )
@key_required
def get( bid = None ):
	result = []

	if bid:
		try:
			result.append( mongo.db.bookmarks.find_one( { '_id': to_id( bid ) , 'email': g.email } ) )
		except OperationFailure:
			abort( 500 )
		return myjsonify( result )

	skip = limit = 0
	if 'Range' in request.headers:
		m = RANGE_RE.match( request.headers[ 'Range' ] )
		if m:
			m = m.groups()
			skip = int( m[ 0 ] )
			limit = int( m[ 2 ] ) - skip + 1 if m[ 2 ] else 0
		if not m or limit < 0: abort( 416 )

	args = parse_qs( request.headers[ 'X-Nofussbm-Query' ] ) if 'X-Nofussbm-Query' in request.headers else None
	query = query_from_dict( g.email, dict( ( k, args[ k ][ 0 ] ) for k in args.keys() ) if args else None )

	try:
		cur = mongo.db.bookmarks.find( query, skip = skip, limit = limit )
		n = cur.count()
		for bm in cur:
			bm[ 'id' ] = bm[ '_id' ]; del bm[ '_id' ]
			del bm[ 'email' ]
			bm[ 'tags' ] = u','.join( bm[ 'tags' ] )
			result.append( bm )
	except OperationFailure:
		abort( 500 )
	return myjsonify( result, headers = { 'Content-Range': 'bookmarks {0}-{1}/{2}'.format( skip, skip + ( limit - 1 if limit else n ), n ), 'Accept-Ranges': 'bookmarks' } )

@api.route( '/', methods = [ 'PUT' ] )
@key_required
def put():
	result = { 'error': [], 'updated': [], 'ignored': [] }
	code = 200
	for pos, bm in enumerate( request.json ):
		try:
			_id = bm[ 'id' ]
			clean_bm( bm )
			bm[ 'date-modified' ] = datetime.utcnow()
			ret = mongo.db.bookmarks.update_one( { '_id': _id, 'email': g.email }, { '$set': bm } )
			print ret
		except ( KeyError, OperationFailure ):
			result[ 'error' ].append( '#{0}'.format( pos ) )
			code = 500
		else:
			result[ 'updated' if ret.modified_count == 1 else 'ignored' ].append( _id )
	return myjsonify( result, code )

@api.route( '/', methods = [ 'DELETE' ] )
@key_required
def delete():
	result = { 'error': [], 'deleted': [], 'ignored': [] }
	code = 200
	for pos, bm in enumerate( request.json ):
		try:
			_id = bm[ 'id' ]
			ret = mongo.db.bookmarks.delete_one( { '_id': _id, 'email': g.email } )
		except ( KeyError, OperationFailure ):
			result[ 'error' ].append( '#{0}'.format( pos ) )
			code = 500
		else:
			result[ 'deleted' if ret.deleted_count == 1 else 'ignored' ].append( _id )
	return myjsonify( result, code )

# signup and alias helpers

@api.route( '/sendkey', methods = [ 'POST' ] )
def sendkey():
	email = request.form[ 'email' ]
	key = new_key( email )
	mongo.db.emails.insert( { 'email': email, 'key': key, 'ip': request.remote_addr, 'date': datetime.utcnow() } )
	try:
		send_mail( 'Massimo Santini <massimo.santini@gmail.com>', email, 'Your "No Fuss Bookmark" API key', 'Your key is {0}'.format( key ) )
	except:
		abort( 500 )
	return ''

@api.route( '/setalias/<alias>', methods = [ 'POST' ] )
@key_required
def setalias( alias ):
	result = {}
	code = 200
	try:
		old = mongo.db.aliases.find_and_modify( { 'email': g.email }, { '$set': { 'alias' : alias } }, upsert = True )
		if 'alias' in old: result[ 'old' ] = old[ 'alias' ]
		result[ 'status' ] = 'set'
	except OperationFailure:
		error = mongo.db.error()
		if 'err' in error and 'duplicate' in error[ 'err' ]:
			result[ 'status' ] = 'duplicate'
		else:
			code = 500
			result[ 'status' ] = 'server error'
		return myjsonify( result )
	return myjsonify( result, code )

# Delicious import hack

@api.route( '/import', methods = [ 'PUT' ] )
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
		_id = mongo.db.bookmarks.insert( bms )
	except OperationFailure:
		abort( 500 )
	else:
		return textify( 'success' )

@api.route( '/stats' )
def stats():
	result = {}
	try:
		result[ 'users' ] = mongo.db.bookmarks.group( { 'email': 1 }, None, { 'count': 0 }, 'function( o, p ){ p.count++; }' )
	except OperationFailure:
		abort( 500 )
	return myjsonify( result )
