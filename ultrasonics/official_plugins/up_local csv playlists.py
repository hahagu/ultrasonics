#!/usr/bin/env python3

"""
up_local csv
Local playlists plugin for ultrasonics.

Designed as both an input and output plugin.
Interacts with physical playlist files, reading the songs present in each one.
Extracts additional tag data from each song discovered.
Upon saving playlists, it will update any existing playlists before creating new ones.

XDGFX, 2020
"""

import io
import os
import re
import shutil
from datetime import datetime

import csv

from app import _ultrasonics
from ultrasonics import logs
from ultrasonics.tools import local_tags, name_filter

log = logs.create_log(__name__)

handshake = {
    "name": "local csv playlists",
    "description": "interface with all local .csv playlists in a directory",
    "type": [
        "inputs"
    ],
    "mode": [
        "playlists"
    ],
    "version": "0.1",
    "settings": []
}

supported_playlist_extensions = [
    ".csv"
]

log.info(
    f"Supported playlist extensions include: {supported_playlist_extensions}")


def run(settings_dict, **kwargs):
    """
    1. Checks for compatibility between unix / nt playlist paths.
    2. Create a list of all playlists which already exist.

    if input:
        3. Read each playlist.
        4. Convert the paths to work with ultrasonics.
        5. Read matadata from each song and use to build the songs_dict.

        @return: settings_dict

    if output:
        3. Create backup of playlists id requested
        4. Either open an existing playlist, or create a new playlist with the provided playlist name.
        5. Convert supplied path back to original playlist path style.
        6. Update each playlist with the new data (overwrites any existing songs)
    """

    database = kwargs["database"]
    global_settings = kwargs["global_settings"]
    component = kwargs["component"]
    applet_id = kwargs["applet_id"]
    songs_dict = kwargs["songs_dict"]

    # Get path for playlist files
    path = settings_dict["dir"].rstrip("/").rstrip("\\")
    playlists = []

    # Create a dictionary 'playlists' of all playlists in the specified directory
    # name is the playlist name
    # path is the full path to the playlist
    try:
        if settings_dict["recursive"] == "Yes":
            # Recursive mode
            for root, _, files in os.walk(path):
                for item in files:
                    playlists.append({
                        "name": os.path.splitext(item)[0],
                        "path": os.path.join(root, item)
                    })

        else:
            # Non recursive mode
            files = os.listdir(path)
            for item in files:
                playlists.append({
                    "name": os.path.splitext(item)[0],
                    "path": os.path.join(path, item)
                })

    except Exception as e:
        log.error(e)

    # Remove any files which don't have a supported extension
    playlists = [item for item in playlists if os.path.splitext(item["path"])[
        1] in supported_playlist_extensions]

    log.info(f"Found {len(playlists)} playlist(s) in supplied directory.")

    if component == "inputs":
        songs_dict = []

        # Apply regex filter to playlists
        filter_titles = [item["name"] for item in playlists]
        filter_titles = name_filter.filter_list(
            filter_titles, settings_dict["filter"])

        log.info(f"{len(filter_titles)} playlist(s) match supplied filter.")

        playlists = [
            item for item in playlists if item["name"] in filter_titles]

        for playlist in playlists:

            # Initialise entry for this playlist
            songs_dict_entry = {
                "name": playlist["name"],
                "id": {},
                "songs": []
            }

            # Read the playlist file
            csvFile = io.open(playlist["path"], 'r', encoding='utf8')
            reader = csv.reader(csvFile, delimiter=',')

            for songRow in reader:
                song = {}
                song['artist'] = songRow[0]
                song['title'] = songRow[1]
                song['album'] = songRow[2]
                song['isrc'] = songRow[3]

                # Add entry to the full songs dict for this playlist
                songs_dict_entry["songs"].append(song)

            # Add previous playlist to full songs_dict
            songs_dict.append(songs_dict_entry)

        return songs_dict

def builder(**kwargs):
    component = kwargs["component"]

    settings_dict = [
        {
            "type": "string",
            "value": f"⚠️ Only {', '.join(supported_playlist_extensions)} extensions are supported for playlists, and .mp3, m4a extensions are supported for audio files. Unsupported files will be ignored."
        },
        {
            "type": "text",
            "label": "Directory",
            "name": "dir",
            "value": "/mnt/music library/playlists",
            "required": True
        },
        {
            "type": "string",
            "value": "Enabling recursive mode will search all subfolders for more playlists."
        },
        {
            "type": "radio",
            "label": "Recursive",
            "name": "recursive",
            "id": "recursive",
            "options": [
                "Yes",
                "No"
            ],
            "required": True
        }
    ]

    if component == "inputs":
        settings_dict.extend(
            [
                {
                    "type": "string",
                    "value": "You can use regex style filters to only select certain playlists. For example, 'disco' would sync playlists 'Disco 2010' and 'nu_disco', or '2020$' would only sync playlists which ended with the value '2020'."
                },
                {
                    "type": "string",
                    "value": "Leave it blank to sync everything 🤓."
                },
                {
                    "type": "text",
                    "label": "Filter",
                    "name": "filter",
                    "value": ""
                }
            ]
        )

    return settings_dict
