#!/usr/bin/env python3

import argparse
import configparser
import json
import sys
import time
from typing import Dict, List, Optional

import requests

CONFIG = configparser.ConfigParser()
CONFIG.read('config.ini')
KEY = CONFIG['settings']['key']
ACCESS_TOKEN = CONFIG['settings']['access_token']

API_BASE = 'https://www.googleapis.com/youtube/v3'
API_PARAMS = {'key': KEY}
API_HEADERS = {'Authorization': f'Bearer {ACCESS_TOKEN}'}


def pretty_format(obj: dict) -> str:
    """Turn a JSON-like dict into something human readable"""
    return json.dumps(obj, indent=4)


def get_playlist_items(playlist_id: str, page_token: str = None) -> Optional[List[Dict[str, str]]]:
    """Recursivly iterate through all pages, return ordered list of `resourceId`s"""

    # Use the API key instead of OAuth (if you can help it)
    params = {**API_PARAMS}
    # 'snippet' because need resource IDs of the videos
    params['part'] = 'snippet'
    params['playlistId'] = playlist_id
    if page_token:
        params['pageToken'] = page_token

    # Progress dot (user feedback is important)
    sys.stdout.write('.')
    sys.stdout.flush()

    r = requests.get(f'{API_BASE}/playlistItems', params=params)
    if r.status_code != requests.codes.ok:
        print(f'ERROR: {r.status_code}\n{pretty_format(r.json())}')
        return None

    data = r.json()

    page_items = [obj['snippet']['resourceId'] for obj in data['items']]

    next_page_token = data['nextPageToken'] if 'nextPageToken' in data else None
    if next_page_token:
        return [*page_items, *get_playlist_items(playlist_id, next_page_token)]
    else:
        return page_items


def youtube_response_has_error(response: dict, reason: str) -> bool:
    """Return true if one of the errors in the response is of the provided reason (e.g. quotaExceeded, etc)"""
    # TODO: There's probably a one-liner for this
    # YT API has a 'error' object wrapping all error info. E.g. error.status == 403/404 here.
    # The YT specific reason is stored in an array called `error.errors`
    errors = response['error']['errors']
    for error in errors:
        if error['reason'] == reason:
            return True
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('playlist_id_to_reverse', help='YouTube playlist ID (the gobbledeegook in the URL) to reverse')
    parser.add_argument('result_playlist_id', help='YouTube playlist ID of where to store results')

    args = parser.parse_args()

    # 1. Get ordered video list of the playlist to invert
    print(f'Getting videos for {args.playlist_id_to_reverse}')
    videos = get_playlist_items(args.playlist_id_to_reverse)
    if videos is None:
        sys.exit(1)

    # DEBUG
    print(f'\n{len(videos)} Results:')
    for vid in videos:
        print(f'{vid}')

    # 2. Invert video list
    videos.reverse()

    # 3. Create new playlist
    print('Making playlist')
    # TODO: Auto make playlist. For now, just give one on cmdline

    # 4. Shove inverted video list into new playlist
    print('Shoving videos into playlist')
    for resourceId in videos:
        sys.stdout.write('.')
        sys.stdout.flush()

        while True:
            # continue    will retry
            # break       will advance (effectively ignores videos for non-200)
            # sys.exit(1) will halt
            #
            # NOTE TO SELF: Try not to have nested for/while loops in here...

            r = requests.post(f'{API_BASE}/playlistItems',
                            params={'part': 'snippet'},
                            headers=API_HEADERS,
                            json={"snippet": {"playlistId": args.result_playlist_id, "resourceId": resourceId}})

            if r.status_code == requests.codes.ok:
                # All is good, onto the next!
                break

            if r.status_code == requests.codes.forbidden:
                # Have to drill into the message deets but if this is a quota exdeeding situation then retry.

                if youtube_response_has_error(r.json(), 'quotaExceeded'):
                    print('\nHit YouTube quota, backing off and retrying')
                    time.sleep(1)
                    continue

                # No idea what other 403 errors are so fall through and treat as fatal 

            if r.status_code == requests.codes.not_found:
                # If video is not found there could be a lot of reasons (not available in your area, taken down, private, etc.).
                # Ignore videos that can't be found.

                if youtube_response_has_error(r.json(), 'videoNotFound'):
                    print(f'\nvideoNotFound, ignoring: {vid}')
                    break

                # Treat other 404s as fatal for now

            print(f'FATAL: {r.status_code}\n{pretty_format(r.json())}')
            sys.exit(1)

    print('\nDone!')


if __name__ == '__main__':
    main()
