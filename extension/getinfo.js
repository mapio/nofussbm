chrome.extension.onRequest.addListener(
	function( request, sender, sendResponse ) {
		sendResponse( {
			"title": document.title,
			"selection": window.getSelection().toString()
		} );
} );
