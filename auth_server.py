#!/usr/bin/env python3

import base64
import hashlib
import json
import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.request import HTTPError, urlopen
from urllib.parse import urlencode, urlparse, parse_qs

from config import TOKEN_FILE as RELATIVE_TOKEN_FILE
from config import CLIENT_ID as SPOTIFY_CLIENT_ID


SERVER_PORT = 8193
REDIRECT_URI = f'http://127.0.0.1:{SERVER_PORT}/auth'

TOKEN_FILE = Path(__file__).parent / RELATIVE_TOKEN_FILE


def create_request_handler():

    shared_context = {
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
            qs = urlparse(self.path).query
            qs_dict = parse_qs(qs)

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()

            if not qs_dict:
                html = self._redirect_tpl
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


class AuthorizationError(Exception):
    pass


def listen_for_authorization_code(port):
    request_handler, shared_context = create_request_handler()
    with HTTPServer(('localhost', port), request_handler) as httpd:
        while True:
            httpd.handle_request()
            if shared_context['code']:
                return shared_context['code']
            elif shared_context['error']:
                raise AuthorizationError(shared_context['error'])


def prompt_user_for_auth():
    code_verifier = base64.urlsafe_b64encode(os.urandom(40)).decode('utf-8')
    code_verifier = re.sub('[^a-zA-Z0-9]+', '', code_verifier)

    code_challenge = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode('utf-8')
    code_challenge = code_challenge.replace('=', '')

    url_params = urlencode({
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'client_id': SPOTIFY_CLIENT_ID,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
        'scope': " ".join((
            'playlist-read-private',
            'playlist-read-collaborative',
            'user-library-read',
        ))
    })
    url = f'https://accounts.spotify.com/authorize?{url_params}'
    print(
        "",
        "Please open the following URL in a Web Browser to continue:",
        url,
        sep='\n'
    )
    code = listen_for_authorization_code(port=SERVER_PORT)
    return code, code_verifier


def request_refresh_token(token_params):
    request_params = urlencode({
        'redirect_uri': REDIRECT_URI,
        'client_id': SPOTIFY_CLIENT_ID,
        **token_params
    }).encode()
    url = 'https://accounts.spotify.com/api/token'
    with urlopen(url, data=request_params) as response:
        return json.loads(response.read().decode())


def activate_refresh_token(refresh_token, code_verifier):
    token_params = {
        'grant_type': 'authorization_code',
        'code': refresh_token,
        'code_verifier': code_verifier,
    }
    content = request_refresh_token(token_params)
    return content['access_token'], content['refresh_token']


def redeem_refresh_token(refresh_token):
    token_params = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    content = request_refresh_token(token_params)
    return content['access_token'], content['refresh_token']


def save_token_to_file(token):
    token_path = Path(TOKEN_FILE).resolve()
    token_path.touch(0o600, exist_ok=True)
    token_path.write_text(token)


def get_token(restore_token=True, save_token=True):
    access_token = None

    if restore_token and TOKEN_FILE.resolve().exists():
        refresh_token = Path(TOKEN_FILE).read_text().strip()
        try:
            access_token, refresh_token = redeem_refresh_token(refresh_token)
        except HTTPError:
            # Go on and get a new refresh token
            pass

    if not access_token:
        code, code_verifier = prompt_user_for_auth()
        access_token, refresh_token = activate_refresh_token(code, code_verifier)

    if save_token:
        save_token_to_file(refresh_token)
    return access_token


if __name__ == '__main__':
    print(get_token())
