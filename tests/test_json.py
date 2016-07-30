import unittest
import nofussbm
import flask
import datetime

from bson import ObjectId


class NofussbmJSONTestCase( unittest.TestCase ):

    def setUp( self ):
        self.app = nofussbm.app
        self.app.config[ 'TESTING' ] = True
        self.client = nofussbm.app.test_client()

    def tearDown( self ):
        pass

    def testJson( self ):
        expected_load = [ {
            u'date-modified': datetime.datetime(2016, 7, 16, 0, 0, 43, 237000),
            u'title': u'Google',
            u'url': u'https://google.com',
            u'tags': [ u'google', u'search engine' ],
            u'id': ObjectId( '5789792b19f4cb77cc3be929' ),
            u'date-added': datetime.datetime(2016, 7, 16, 0, 0, 43, 237000)
        } ]
        to_load = ( '[{'
                    '"date-added": "2016-07-16 00:00:43.237000", '
                    '"date-modified": "2016-07-16 00:00:43.237000", '
                    '"id": "5789792b19f4cb77cc3be929", '
                    '"tags": "google,search engine", '
                    '"title": "Google", '
                    '"url": "https://google.com"'
                    '}]' )
        expected_dump = ( '[{'
                          '"date-added": "2016-07-16 00:00:43.237000", '
                          '"date-modified": "2016-07-16 00:00:43.237000", '
                          '"id": "5789792b19f4cb77cc3be929", '
                          '"tags": ["google", "search engine"], '
                          '"title": "Google", '
                          '"url": "https://google.com"'
                          '}]' )

        self.assertEqual( self.app.json_encoder, nofussbm.json.NofussbmJSONEncoder )
        self.assertEqual( self.app.json_decoder, nofussbm.json.NofussbmJSONDecoder )

        with self.app.app_context():
            load = flask.json.loads( to_load )  # expected_dump
            dump = flask.json.dumps( expected_load )
            self.assertEqual( load, expected_load )
            self.assertEqual( dump, expected_dump )

            tags_as_list_load = flask.json.loads( expected_dump )
            self.assertEqual( tags_as_list_load, expected_load )

if __name__ == '__main__':
    unittest.main()
