#!/usr/bin/env python3

import json
from pathlib import Path

from spotipy import Spotify

import auth_server
from config import PLAYLISTS_FOLDER


def retrieve_all_items(spotify, result):
    items = []
    while result is not None:
        items.extend(result['items'])
        result = spotify.next(result)
    return items


def main():
    pl_folder = Path(__file__).parent / PLAYLISTS_FOLDER
    pl_folder.mkdir(exist_ok=True)

    print("Retrieving auth token")
    token = auth_server.get_token()
    print("Starting export")
    sp = Spotify(auth=token)
    backup_fnames = set()
    for pl in retrieve_all_items(sp, sp.current_user_playlists()):
        name = pl['name']
        plname = pl['name'].replace('/', '_').replace('\\', '_')\
                           .replace('"', '`').replace("'", '`')\
                           .replace(":", '-').replace('?', '-')
        backup_fname = f"{plname}_{pl['id']}.json"
        backup_fnames.add(backup_fname)
        backup_fpath = pl_folder / backup_fname

        # Check if there already is a current backup
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

    # Move deleted playlists elsewhere
    deleted_fpath = pl_folder / 'deleted'
    deleted_fpath.mkdir(exist_ok=True)
    all_fnames = set(p.name for p in pl_folder.glob('*.json'))
    deleted_fnames = all_fnames - backup_fnames
    for fname in deleted_fnames:
        print(f'Move playlist backup to deleted folder: {fname}')
        (pl_folder / fname).replace(deleted_fpath / fname)


if __name__ == "__main__":
    main()
