#!/usr/bin/env python3

import json
from pathlib import Path

from spotipy import Spotify

import auth_server


def retrieve_all_items(spotify, result):
    items = []
    while result is not None:
        items.extend(result['items'])
        result = spotify.next(result)
    return items


def main():
    print("Retrieving auth token")
    pl_folder = Path(__file__).parent / 'playlists'
    token = auth_server.get_token()
    print("Starting export")
    sp = Spotify(auth=token)
    for pl in retrieve_all_items(sp, sp.current_user_playlists()):
        name = pl['name']

        # Check if there already is a current backup
        plname = pl['name'].replace('/','_')
        backup_fpath = pl_folder / f"{plname}_{pl['id']}.json"
        if backup_fpath.resolve().exists():
            text = backup_fpath.read_text()
            stored_playlist = json.loads(text)
            if stored_playlist.get('snapshot_id') == pl['snapshot_id']:
                print(f'Playlist backup is up-to-date: {name}')
                continue

        print(f'Retrieving playlist: {name}')
        playlist = sp.user_playlist(
            user=pl['owner']['id'], playlist_id=pl['id']
        )
        playlist['tracks'] = retrieve_all_items(sp, playlist['tracks'])
        backup_fpath.write_text(json.dumps(playlist))


if __name__ == "__main__":
    main()
