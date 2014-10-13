#!/usr/bin/env python3

import webbrowser

from bottle import Bottle, run, request

class SpotifyAuth():
    def __init__(self, port=None):
        self.token = None
        self.port = port or 8193
        #self.port = 9183
        #print(self.port)
    
    def _auth_callback(self):
        self.token = request.query.code
        self._instance.close()

    def _listenAndWaitForRedirect(self, port):
        app = Bottle()
        app.get('/auth')(self._auth_callback)
        app.get('/auth/')(self._auth_callback)
        self._instance = app
        run(app, port=port)
    
    def askForToken(self):
        urlFormat = "https://accounts.spotify.com/en/authorize?redirect_uri=http:%2F%2Flocalhost:{}%2Fauth&response_type=code&client_id=239865de29224f048b0cb696e2592f8e&scope="
        webbrowser.open(urlFormat.format(self.port))
        self._listenAndWaitForRedirect(self.port)
        return self.token
        
    def restoreCachedToken(self):
        pass

if __name__ == '__main__':
    auth = SpotifyAuth()
    print(auth.askForToken())
