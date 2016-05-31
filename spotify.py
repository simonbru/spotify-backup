
import requests

import auth_server


def parse_uri(spotify_uri):
    parts = spotify_uri.lstrip('spotify:').split(':')
    return {key: value for key, value in zip(parts[0::2], parts[1::2])}


class Spotify():
    def __init__(self, auth_token):
        self.auth_token = auth_token
        self._user_id = None

    @property
    def _session(self):
        s = requests.Session()
        s.headers.update({"Authorization": "Bearer " + self.auth_token})
        return s

    @property
    def user_id(self):
        if not self._user_id:
            req = self._session.get("https://api.spotify.com/v1/me")
            res = req.json()
            # print(req.text)
            self._user_id = res['id']
        return self._user_id

    @property
    def playlists(self):
        url = "https://api.spotify.com/v1/users/{}/playlists?limit=50".format(self.user_id)
        req = self._session.get(url)
        # print(req.text)
        return req.json()['items']

    def playlist(self, playlist_uri):
        infos = parse_uri(playlist_uri)
        urlFormat = "https://api.spotify.com/v1/users/{}/playlists/{}"
        req = self._session.get(urlFormat.format(infos['user'], infos['playlist']))
        return req.json()


def debug_sp():
    return Spotify(auth_server.get_token())

# def extract

if __name__ == "__main__":
    sp = Spotify(auth_server.get_token())
    print(sp.user_id)
