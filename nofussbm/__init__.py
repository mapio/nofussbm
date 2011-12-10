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

from logging import StreamHandler, Formatter, getLogger, DEBUG
from os import environ as ENV
from urlparse import parse_qs

from flask import Flask, make_response, request, g, redirect, url_for, abort, render_template

from pymongo import Connection
from pymongo.errors import OperationFailure, DuplicateKeyError


# Configure from the environment, global (immutable) variables (before submodules import)

class Config( object ):
	SECRET_KEY = ENV[ 'SECRET_KEY' ]
	MONGOLAB_URI = ENV[ 'MONGOLAB_URI' ]
	SENDGRID_USERNAME = ENV[ 'SENDGRID_USERNAME' ]
	SENDGRID_PASSWORD = ENV[ 'SENDGRID_PASSWORD' ]

from .api import api
from .tags import tags

# Create the app, register APIs blueprint and setup {before,teardown}_request  

app = Flask( __name__ )
app.register_blueprint( api, url_prefix = '/api/v1' )

@app.before_request
def before_request():
	g.conn = Connection( Config.MONGOLAB_URI )
	g.db = g.conn[ Config.MONGOLAB_URI.split('/')[ -1 ] ]
	
@app.teardown_request
def teardown_request( exception ):
	g.conn.disconnect()

# Log to stderr (so heroku logs will pick'em up)

stderr_handler = StreamHandler()
stderr_handler.setLevel( DEBUG )
stderr_handler.setFormatter( Formatter( '%(asctime)s [%(process)s] [%(levelname)s] [Flask: %(name)s] %(message)s','%Y-%m-%d %H:%M:%S' ) )
app.logger.addHandler( stderr_handler )
app.logger.setLevel( DEBUG )


# Helpers

def textify( text, code = 200 ):
	response = make_response( text + '\n', code )
	response.headers[ 'Content-Type' ] = 'text/plain; charset=UTF-8'
	return response

def ident2email( ident ):
	if '@' in ident: email = ident
	else: 
		try:
			alias = g.db.aliases.find_one( { 'alias': ident }, { 'email': 1 } )
			email = alias[ 'email' ]
		except TypeError:
			abort( 404 )
		except OperationFailure:
			abort( 500 )
	return email
	
def list_query( email, limit = None ):
	args = request.args
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
	email = ident2email( ident )
	try:
		if 'html' in request.args:
			for bm in list_query( email, 10 ):
				date = bm[ 'date-modified' ]
				result.append( ( date.strftime( '%Y-%m-%d' ), bm[ 'url' ], bm[ 'title' ], bm[ 'tags' ] ) )
			return render_template( 'list.html', bookmarks = result, tags = tags( g.db, email )[ : 10 ] )
		else:
			for bm in list_query( email ):
				date = bm[ 'date-modified' ]
				result.append( u'\t'.join( ( date.strftime( '%Y-%m-%d' ), bm[ 'url' ], bm[ 'title' ], u','.join( bm[ 'tags' ] ) ) ) )
			return textify( u'\n'.join( result ) )
	except OperationFailure:
		abort( 500 )
