import time
from itertools import permutations
from time import sleep
import os
from requests import exceptions as requests_exceptions
import spotipy
from spotipy import SpotifyException
from spotipy.oauth2 import SpotifyClientCredentials
import sqlite3
from sqlite3 import Error
import logging
import asyncio

from nltk import FreqDist
from nltk.corpus import brown

frequency_list = FreqDist(i.lower() for i in brown.words())
wordlist = [frequency[0] for frequency in frequency_list.most_common()[:10 * 1000]]

logging.basicConfig(filename='Spotify.log', level=logging.INFO, filemode='w')


def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        # create table
        c.execute('''CREATE TABLE IF NOT EXISTS spotify_playlists
                     (playlist text, track text,
                     UNIQUE(playlist, track)
                     )''')
        c.execute("CREATE INDEX index_track ON spotify_playlists(track)")
        # commit the changes to db
        conn.commit()
    except Error as e:
        print(e)

    return conn


def update_playlists_table(db_conn, table_name, list_of_params):
    db_conn.executemany(f"""INSERT or ignore INTO {table_name} 
                        values(?, ?) 
                        """,
                        list_of_params)
    db_conn.commit()


class save_last_playlist_id:
    def __init__(self, file_name):
        self.__path = file_name
        self.__file_object = None
        self.max_val = 0

    def __enter__(self):
        try:
            self.__file_object = open(self.__path, 'a+')
            self.__file_object.seek(0)
            self.max_val = int(self.__file_object.read())
            return self
        except FileNotFoundError:
            self.__file_object = open(self.__path, 'w')
            self.__file_object.seek(0)
            self.__file_object.truncate()
            self.__file_object.writelines(str(0))
            return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print(self.max_val, "max")
        self.__file_object.seek(0)
        self.__file_object.truncate()
        self.__file_object.writelines(str(self.max_val))
        self.__file_object.close()


def spotify_search_playlist(spotify_client, words_to_query):
    try:
        return spotify_client.search(q=words_to_query, limit=50, type='playlist')['playlists']
    except TypeError:
        logging.warning("Empty Dictionary")
        return


async def spotify_playlist_items(spotify_client, id_of_playlist, idx, last_id_file, playlist_id):
    try:
        items_in_playlist = spotify_client.playlist_items(id_of_playlist, limit=50,
                                                          fields="items.track.id,items.track.id,total",
                                                          additional_types=('track',))['items']
        list_of_id_playlist_and_track = []
        if 0 < len(items_in_playlist) < 100:

            for name_of_track in items_in_playlist:
                try:
                    track_id = name_of_track['track']['id']
                    if track_id is not None:
                        list_of_id_playlist_and_track.append((playlist_id, track_id))
                        if len(list_of_id_playlist_and_track) > 0:
                            last_id_file.max_val = idx
                            # logging.info('Recorded: ' + playlist_id + " and track" + str(track_id) +
                            #              ' at index ' + str(idx))

                except TypeError:
                    logging.info("No ID for Track")
        return list_of_id_playlist_and_track
    except TypeError:
        print("empty")
        logging.warning("Empty Dictionary")
    except NameError:
        print("Unknown Error, Logged into file")
        logging.critical("Unknown Error", playlist_id)


def get_nested_lists_into_one(lst):
    not_nested = []
    for nested_lst in lst:
        for nested_item in nested_lst:
            not_nested.append(nested_item)
    return not_nested


async def async_spotify_calls(spotify, words_in_playlist, idx, last_id_file, db):
    playlist_ids_list = spotify_search_playlist(spotify_client=spotify, words_to_query=words_in_playlist)
    print(idx)
    if playlist_ids_list is None:
        return
    else:
        playlist_ids_list = playlist_ids_list['items']

        list_of_coroutines = []
        for playlist_ in playlist_ids_list:
            playlist_id = playlist_['id']
            try:
                list_of_coroutines.append(
                    spotify_playlist_items(spotify_client=spotify, id_of_playlist=playlist_id, idx=idx,
                                           last_id_file=last_id_file, playlist_id=playlist_id))

            except SpotifyException as err:
                if err.code == -1:
                    logging.info(f"Could not fetch songs for {playlist_id}")
                    last_id_file.max_val = idx
            except requests_exceptions.Timeout as err:
                logging.info(f"Encountered Timeout While Querying Track, {err}")
                last_id_file.max_val = idx
        print("Loading time start ")
        t = time.time()

        nested_lists_of_playlists_and_items = await asyncio.gather(*list_of_coroutines)
        print("Loading time end ", time.time() - t)
        not_nested_lists_of_playlists_and_items = get_nested_lists_into_one(
            nested_lists_of_playlists_and_items)

        update_playlists_table(db_conn=db, table_name='spotify_playlists',
                               list_of_params=not_nested_lists_of_playlists_and_items)
        last_id_file.max_val = idx


async def create_spotify_db():
    db = create_connection("spotify_db.db")
    os.environ['SPOTIPY_CLIENT_ID'] = "40562dc726d3436e8379e5d675d483d8"
    os.environ['SPOTIPY_CLIENT_SECRET'] = "3798edc98a79485bb91c1a5afd9f8c6b"
    spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    with save_last_playlist_id("last_id_text_file.txt") as last_id_file:
        last_id_file.max_val = int(last_id_file.max_val)
        for idx, words_in_playlist in enumerate(permutations(wordlist, 2)):
            passed = False
            while not passed:
                if idx >= last_id_file.max_val:
                    words_in_playlist = " ".join(words_in_playlist)
                    try:
                        await async_spotify_calls(spotify, words_in_playlist, idx, last_id_file, db)
                        passed = True
                    except SpotifyException as err:
                        if err.code == -1:
                            logging.info(f"Could not find playlist with {words_in_playlist}")
                            last_id_file.max_val = idx
                            passed = True
                    except requests_exceptions.Timeout as err:
                        logging.warning(f"Encountered Timeout {err}")
                        print("Encountered API Limit")
                        last_id_file.max_val = idx
                        sleep(6)

                else:
                    passed = True
if __name__ == '__main__':
    conn_name = sqlite3.connect("spotify_db.db")
    db_name = conn_name.cursor()
    asyncio.run(create_spotify_db())
