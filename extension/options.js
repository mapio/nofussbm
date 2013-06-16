/*
 Copyright 2011, Massimo Santini <santini@dsi.unimi.it>

 This file is part of "No Fuss Bookmarks".

 "No Fuss Bookmarks" is free software: you can redistribute it and/or modify it
 under the terms of the GNU General Public License as published by the Free
 Software Foundation, either version 3 of the License, or (at your option) any
 later version.

 "No Fuss Bookmarks" is distributed in the hope that it will be useful, but
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
 details.

 You should have received a copy of the GNU General Public License along with
 "No Fuss Bookmarks". If not, see <http://www.gnu.org/licenses/>.
*/

var form;

function onload() {
	form = document.forms.options;
	form.key.value = localStorage.getItem( 'key' );
}

function set() {
	localStorage.setItem( 'key', form.key.value );
}

document.addEventListener( 'DOMContentLoaded', function () {
    onload();
    document.getElementById( 'key' ).addEventListener( 'change', set );
} );
