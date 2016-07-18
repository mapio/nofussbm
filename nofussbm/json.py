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

from flask.json import JSONEncoder, JSONDecoder
from datetime import datetime
from bson.objectid import ObjectId
from .helpers import to_id

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S.%f'


class NofussbmJSONEncoder(JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime):
            return datetime.strftime(obj, DATETIME_FORMAT)
        if isinstance(obj, ObjectId):
            return str(obj)
        return JSONEncoder.default(self, obj)


class NofussbmJSONDecoder(JSONDecoder):

    def __init__(self, *args, **kwargs):
        self.ALLOWED_KEYS = set(['title', 'url', 'id', 'tags', 'date-added', 'date-modified'])
        self.orig_object_hook = kwargs.pop("object_hook", None)
        super(NofussbmJSONDecoder, self).__init__(*args, object_hook=self.custom_object_hook, **kwargs)

    def custom_object_hook(self, dct):
        res = dict()
        for key, value in dct.items():
            if key not in self.ALLOWED_KEYS:
                continue
            if key == 'id':
                res['id'] = to_id(value)
            elif key == 'tags':
                res['tags'] = [_.strip() for _ in value.split(',')]
            elif key.startswith('date-'):
                try:
                    res[key] = datetime.strptime(value, DATETIME_FORMAT)
                except:
                    pass
            else:
                res[key] = value
        return res
