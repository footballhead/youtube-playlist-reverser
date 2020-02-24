#!/usr/bin/env python3

import argparse
import configparser
import json
import sys
from typing import List, Optional

import requests

CONFIG = configparser.ConfigParser()
CONFIG.read('config.ini')
KEY = CONFIG['settings']['key']

API_BASE = 'https://www.googleapis.com/youtube/v3'
API_PARAMS = {'key': KEY}


def pretty_format(obj: dict) -> str:
    """Turn a JSON-like dict into something human readable"""
    return json.dumps(obj, indent=4)


def get_playlist_items(playlist_id: str, page_token: str = None) -> Optional[List[str]]:
    """Iterate through all pages and give all items of the playlist"""

    params = {**API_PARAMS}
    params['part'] = 'id'
    params['playlistId'] = playlist_id
    if page_token:
        params['pageToken'] = page_token

    r = requests.get(f'{API_BASE}/playlistItems', params=params)
    if r.status_code != requests.codes.ok:
        sys.stderr.write(f'ERROR: {r.status_code}\n{pretty_format(r.json())}\n')
        return None

    data = r.json()

    page_items = [obj['id'] for obj in data['items']]

    next_page_token = data['nextPageToken'] if 'nextPageToken' in data else None
    if next_page_token:
        return [*page_items, *get_playlist_items(playlist_id, next_page_token)]
    else:
        return page_items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('playlist_id', help='YouTube playlist ID (the gobbledeegook in the URL)')

    args = parser.parse_args()

    # 1. Get ordered video list of the playlist to invert
    videos = get_playlist_items(args.playlist_id)
    if videos is None:
        sys.exit(1)

    # DEBUG
    print(f'{len(videos)} Results:')
    for vid in videos:
        print(vid)

    # 2. Invert video list
    # 3. Create new playlist
    # 4. Shove inverted video list into new playlist

    # print(pretty_format(r.json())) # DEBUG


if __name__ == '__main__':
    main()
