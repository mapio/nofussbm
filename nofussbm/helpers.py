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

from email.mime.text import MIMEText
from smtplib import SMTP

from bson.objectid import ObjectId, InvalidId

from . import Config


def to_id( id_as_str ):
	res = None
	try:
		res = ObjectId( id_as_str )
	except InvalidId:
		pass
	return res

def query_from_dict( email, dct ):
	query = { 'email': email }
	if not dct: return query
	if 'id' in dct:
		query[ '_id' ] = ObjectId( dct[ 'id'] )
	if 'tags' in dct:
		tags = map( lambda _: _.strip(), dct[ 'tags' ].split( ',' ) )
		query[ 'tags' ] = { '$all': tags }
	if 'title' in dct:
		query[ 'title' ] = { '$regex': dct[ 'title' ], '$options': 'i' }
	return query


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
