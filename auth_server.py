#!/usr/bin/env python3

import urllib.parse
import ast
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.request import HTTPError, Request, urlopen
from urllib.parse import urlencode

from config import TOKEN_FILE as RELATIVE_TOKEN_FILE
from config import CLIENT_ID as SPOTIFY_CLIENT_ID, CLIENT_SECRET as SPOTIFY_CLIENT_SECRET
from config import REFRESHABLE_AUTH


SERVER_PORT = 8193
REDIRECT_URI = f'http://localhost:{SERVER_PORT}/auth'

TOKEN_FILE = Path(__file__).parent / RELATIVE_TOKEN_FILE


class AuthorizationError(Exception):
    pass


def do_save_token(token):
    token_path = Path(TOKEN_FILE).resolve()
    token_path.touch(0o600, exist_ok=True)
    token_path.write_text(token)


def listen_for_token(port):
    RequestHandler, shared_context = create_request_handler()
    httpd = HTTPServer(('localhost', port), RequestHandler)
    while True:
        httpd.handle_request()
        if shared_context['access_token']:
            return shared_context['access_token']
        if shared_context['code']:
            return shared_context['code']
        elif shared_context['error']:
            raise AuthorizationError(shared_context['error'])


def create_request_handler():

    shared_context = {
        'access_token': None,
        'code': None,
        'error': None
    }

    class AuthRequestHandler(BaseHTTPRequestHandler):
        _redirect_tpl = """
            <html>
            <script>
            if (location.href.indexOf('#') != -1)
                location.href = location.href.replace("#","?");
            </script>
            <h1>Redirecting...</h1>
            </html>
        """
        _success_tpl = """
            <html>
            <h1>Authorization successful</h1>
            <p>You can close this page now</p>
            </html>
        """
        _error_tpl = """
            <html>
            <h1>Authorization error</h1>
            <p>{error}</p>
            </html>
        """
        
        def do_GET(self):
            qs = urllib.parse.urlparse(self.path).query
            qs_dict = urllib.parse.parse_qs(qs)

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()

            if not qs_dict:
                html = self._redirect_tpl
            elif 'access_token' in qs_dict:
                token = qs_dict['access_token'][0]
                shared_context['access_token'] = token
                html = self._success_tpl
            elif 'code' in qs_dict:
                token = qs_dict['code'][0]
                shared_context['code'] = token
                html = self._success_tpl
            else:
                error = qs_dict.get('error', ['unknown'])[0]
                shared_context['error'] = error
                html = self._error_tpl.format(error=error)
            self.wfile.write(html.encode('utf8'))
            self.wfile.flush()
    
    return AuthRequestHandler, shared_context


def redeem_refresh_token(refresh_token):
    request_params = urlencode({
        'redirect_uri': REDIRECT_URI,
        'grant_type': 'authorization_code',
        'client_id': SPOTIFY_CLIENT_ID,
        'client_secret': SPOTIFY_CLIENT_SECRET,
        'code': refresh_token
    }).encode()
    url = f'https://accounts.spotify.com/api/token'
    with urllib.request.urlopen(url, data=request_params) as response:
        content = ast.literal_eval(response.read().decode())
        return content['access_token'], content['refresh_token']


def get_token(restore_token=True, save_token=True):
    if restore_token and TOKEN_FILE.resolve().exists():
        token = Path(TOKEN_FILE).read_text().strip()

        if REFRESHABLE_AUTH:
            try:
                token = redeem_refresh_token(token)
            except HTTPError:
                # This will fail if the token wasn't a refresh token
                pass

        # Check that the token is valid
        req = Request(
            'https://api.spotify.com/v1/me',
            headers={'Authorization': f'Bearer {token}'}
        )
        try:
            urlopen(req)
        except HTTPError:
            pass
        else:
            return token

    if REFRESHABLE_AUTH:
        response_type = 'code'
    else:
        response_type = 'token'

    url_params = urlencode(dict(
        redirect_uri=REDIRECT_URI,
        response_type=response_type,
        client_id=SPOTIFY_CLIENT_ID,
        scope='playlist-read-private playlist-read-collaborative'
    ))
    url = f'https://accounts.spotify.com/authorize?{url_params}'
    print(
        "",
        "Please open the following URL in a Web Browser to continue:",
        url,
        sep='\n'
    )
    token = listen_for_token(port=SERVER_PORT)

    if REFRESHABLE_AUTH:
        token, savable_token = redeem_refresh_token(token)
    else:
        savable_token = token

    if save_token:
        do_save_token(savable_token)
    return token


if __name__ == '__main__':
    print(get_token())
