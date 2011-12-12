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
from os import environ

from flask import Flask, make_response, request, g, redirect, url_for, abort, render_template

from pymongo.errors import OperationFailure


# Configure from the environment, global (immutable) variables (before submodules import)

class Config( object ):
	SECRET_KEY = environ[ 'SECRET_KEY' ]
	SENDGRID_USERNAME = environ[ 'SENDGRID_USERNAME' ]
	SENDGRID_PASSWORD = environ[ 'SENDGRID_PASSWORD' ]

from .api import api
from .tags import tags
from .db import DB

# Create the app, register APIs blueprint and setup {before,teardown}_request  

app = Flask( __name__ )
app.register_blueprint( api, url_prefix = '/api/v1' )

@app.before_request
def before_request():
	g.db = DB( 'MONGOLAB_URI' )

@app.teardown_request
def teardown_request( exception ):
	del g.db

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
	if 'limit' in args:
		limit = int( args[ 'limit' ] )
	else:
		if limit is None: limit = 0
	if skip < 0 or limit < 0: abort( 400 )
	return g.db.bookmarks.find( query, skip = skip, limit = limit ).sort( [ ( 'date-modified', -1 ) ] )


# Public "views"

@app.route( '/' )
def index():
	return redirect( url_for( 'signup' ) )

@app.route( '/favicon.ico' )
def favicon():
	return redirect( url_for( 'static', filename = 'favicon.ico' ) )

@app.route( '/signup.html' )
def signup():
	return render_template( 'signup.html' )

@app.route( '/options.html' )
def options():
	return render_template( 'options.html' )

@app.route( '/<ident>' )
def list( ident ):
	
	try:
		list_appearance = request.cookies.get( 'list_appearance' )
	except KeyError:
		list_appearance = 'text'
	try:
		bookmarks_per_page = int( request.cookies.get( 'bookmarks_per_page' ) )
	except ( KeyError, TypeError ):
		bookmarks_per_page = 10
	try:	
		show_tags = request.cookies.get( 'show_tags' ) == 'true'
	except KeyError:
		show_tags = True
	content_only = 'content_only' in request.args
		
	result = []
	email = ident2email( ident )
	try:
		if list_appearance == 'html':
			for bm in list_query( email, bookmarks_per_page ):
				date = bm[ 'date-modified' ]
				result.append( ( date.strftime( '%Y-%m-%d' ), bm[ 'url' ], bm[ 'title' ], bm[ 'tags' ] ) )
			if content_only:
				return render_template( 'list-content.html', bookmarks = result )
			else:
				return render_template( 'list.html', bookmarks = result, top_tags = tags( g.db, email ) if show_tags else None )
		else:
			for bm in list_query( email ):
				date = bm[ 'date-modified' ]
				result.append( u'\t'.join( ( date.strftime( '%Y-%m-%d' ), bm[ 'url' ], bm[ 'title' ], u','.join( bm[ 'tags' ] ) ) ) )
			return textify( u'\n'.join( result ) )
	except OperationFailure:
		abort( 500 )
