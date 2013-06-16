/*
 Copyright 2011, Massimo Santini <santini@dsi.unimi.it>

 This file is part of 'No Fuss Bookmarks'.

 'No Fuss Bookmarks' is free software: you can redistribute it and/or modify it
 under the terms of the GNU General Public License as published by the Free
 Software Foundation, either version 3 of the License, or (at your option) any
 later version.

 'No Fuss Bookmarks' is distributed in the hope that it will be useful, but
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
 details.

 You should have received a copy of the GNU General Public License along with
 'No Fuss Bookmarks'. If not, see <http://www.gnu.org/licenses/>.
*/

var form, key;

function onload() {
	form = document.forms.bookmarks;
	key = localStorage.getItem( 'key' );
	if ( ! key ) {
		alert( "Please set your API key in extension's options" );
	}
	chrome.tabs.getSelected( null, function( tab ) {
		chrome.tabs.sendRequest( tab.id, {}, function handler( response ) {
			form.url.value = tab.url;
			form.title.value = response.title;
		} );
	} );
}

function postUrl() {
	var data = JSON.stringify( [ { 'url': form.url.value, 'title': form.title.value, 'tags': form.tags.value } ] );
	var req = new XMLHttpRequest();
	req.onreadystatechange = function() {
		if( this.readyState == 4 && this.status == 200 ) {
			response = JSON.parse( req.responseText );
			if ( response[ 'added' ].length ) {
				form.status.value = 'Added Bookmark, id = ' + response[ 'added' ][ 0 ];
			} else {
				form.status.value = 'The bookmark was not added';
			}
		} else if ( this.readyState == 4 && this.status != 200 ) {
			form.status.value = 'An error has occurred';
		}
	};
	req.open( 'POST', 'http://nofussbm.herokuapp.com/api/v1/', true );
	req.setRequestHeader( 'Content-Type', 'application/json' );
	req.setRequestHeader( 'X-Nofussbm-Key', key );
	req.send( data );
	console.log( data );
}

document.addEventListener( 'DOMContentLoaded', function () {
    onload();
    document.getElementById( 'postit' ).addEventListener( 'click', postUrl );
} );
