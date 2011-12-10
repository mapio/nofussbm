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

from datetime import datetime

from bson.code import Code
from bson.son import SON

def tags( db, email ):
	try:
		tags_updated = db.tags.find_one( { '_id.email': email }, { 'value.modified': 1 }  )[ 'value' ][ 'modified' ]
	except TypeError:
		tags_updated = None
	try:
		bookmarks_updated = db.bookmarks.find_one( { 'email': email }, { 'date-modified': 1 }, sort = [ ('date-modified', -1 )] )[ 'date-modified']
	except TypeError: 
		bookmarks_updated = None
	if not tags_updated or tags_updated < bookmarks_updated: _update_tags( db, email )
	return db.tags.find_one( { '_id.email': email } )[ 'value' ][ 'tags' ]

def _update_tags( db, email ):
	
	db[ 'tags-exapnded' ].remove( { '_id.email': email } ) 
	db.bookmarks.map_reduce( Code( """
		function() {
			for ( index in this.tags ) {
				emit( { 'email': this.email, 'tag': this.tags[ index ] }, { count: 1, modified: this[ 'date-modified' ] } );
			}
		}
	""" ), Code( """
		function( key, values ) {
			var result = { count: 0, modified: values[ 0 ].modified };
			values.forEach( function( value ) {
				result.count += value.count;
		    	if ( result.modified < value.modified ) result.modified = value.modified;
			} );
			return result;
		}	
	""" ), query = { 'email': email }, out = SON( [ ( 'merge', 'tags-exapnded' ) ] ) )
	db[ 'tags-exapnded' ].map_reduce( Code ("""
		function() {
			emit( { 'email': this._id.email }, { 'tags': [ [ this._id.tag, this.value.count ] ], 'modified': this.value.modified } );
		}
	"""), Code( """
		function( key, values ) {
			var result = { 'tags': [], 'modified': values[ 0 ].modified } 
			values.forEach( function( value ) {
				result.tags.push.apply( result.tags, value.tags );
		    	if ( result.modified < value.modified ) result.modified = value.modified;
			} );
			return result;
		}
	""" ), finalize = Code( """
		function( key, value ) {
			value.tags = value.tags.sort( function( a, b ) { return b[ 1 ] - a[ 1 ]; } );
			return value;
		}	
	""" ), query = { '_id.email': email }, out = SON( [ ( 'merge', 'tags' ) ] ) )
	

