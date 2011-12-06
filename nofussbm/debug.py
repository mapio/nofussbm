from . import app

def _run():
	app.run( debug = True, use_reloader = False )