#!/usr/bin/env python3

import json
import unicodedata
from os.path import supports_unicode_filenames
from pathlib import Path

from spotipy import Spotify

import auth_server
from config import LIBRARY_FOLDER, PLAYLIST_FIELDS, RESTRICT_FILENAME


# Max number of items per page (allowed by Spotify API)
MAX_LIMIT = 50


def retrieve_all_items(spotify, result):
    items = []
    while result is not None:
        items.extend(result['items'])
        result = spotify.next(result)
    return items


def backup_library(spotify, backup_folder):
    print("Retrieving saved tracks")
    result = spotify.current_user_saved_tracks(limit=MAX_LIMIT)
    items = retrieve_all_items(spotify, result)
    backup_fpath = backup_folder / "tracks.json"
    backup_fpath.write_text(json.dumps(items))

    print("Retrieving saved albums")
    result = spotify.current_user_saved_albums(limit=MAX_LIMIT)
    items = retrieve_all_items(spotify, result)
    backup_fpath = backup_folder / "albums.json"
    backup_fpath.write_text(json.dumps(items))

    print("Retrieving saved shows")
    result = spotify.current_user_saved_shows(limit=MAX_LIMIT)
    items = retrieve_all_items(spotify, result)
    backup_fpath = backup_folder / "shows.json"
    backup_fpath.write_text(json.dumps(items))


def main():
    # Create the library folder, if it doesn't already exist
    library_folder = Path(__file__).parent / LIBRARY_FOLDER
    library_folder.mkdir(exist_ok=True)

    print("Retrieving auth token")
    token = auth_server.get_token()
    print("Starting export")
    sp = Spotify(auth=token)

    pl_folder = library_folder / "playlists"
    pl_folder.mkdir(exist_ok=True)
    backup_fnames = set()
    for pl in retrieve_all_items(sp, sp.current_user_playlists()):
        name = pl['name']
        # Replace any characters that can't go in a filename
        plname = pl['name'].replace('/', '_').replace('\\', '_')\
                           .replace('"', '^').replace("'", '^') \
                           .replace(':', '=').replace('?', '_') \
                           .replace('|', '-').replace('*', '+') \
                           .replace('<', '[').replace('>', ']')

        # Remove any Unicode characters from filename, if the filesystem
        # doesn't support them, or if option is enabled
        if not supports_unicode_filenames or RESTRICT_FILENAME:
            plname = unicodedata.normalize('NFKD', plname)
            # Hack to make sure plname is a string, not bytes
            plname = plname.encode(encoding='ascii', errors='ignore') \
                           .decode(encoding='ascii').strip()

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
        playlist = sp.playlist(playlist_id=pl['id'], fields=PLAYLIST_FIELDS)
        if 'tracks' in playlist and 'items' in playlist['tracks'] and 'next' in playlist['tracks']:
            playlist['tracks']['items'] = retrieve_all_items(sp, playlist['tracks'])
        backup_fpath.write_text(json.dumps(playlist))

    # Move deleted playlists elsewhere
    deleted_fpath = pl_folder / 'deleted'
    deleted_fpath.mkdir(exist_ok=True)
    all_fnames = set(p.name for p in pl_folder.glob('*.json'))
    deleted_fnames = all_fnames - backup_fnames
    for fname in deleted_fnames:
        print(f'Move playlist backup to deleted folder: {fname}')
        (pl_folder / fname).replace(deleted_fpath / fname)

    backup_library(sp, library_folder)


if __name__ == "__main__":
    main()
