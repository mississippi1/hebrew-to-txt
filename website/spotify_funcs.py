import spotipy  
from spotipy import SpotifyClientCredentials
import sqlite3
from sqlite3 import Error

def get_option_songs(client, track_name_or_id, type_of_id):
    """ query spotify for a track and returns optional tracks
     with their respective artists and URL.
    :param client_name: spotify credentianls
     track_name: name of track
    :return: dictionary of id, artist and URL of Track
    """
    dictionary_of_results = {}
    if type_of_id == 'Name':
        tracks_ids_list = client.search(q=track_name_or_id, limit=50, type='track')['tracks']['items']
        for tracks in tracks_ids_list:
            dictionary_of_results[tracks['id']] = [tracks['name'], tracks['artists'][0]['name'], tracks['external_urls']['spotify']]
    elif type_of_id == 'ID':
        tracks_ids_list = client.track(track_id=track_name_or_id)
        dictionary_of_results[tracks_ids_list['id']] = [tracks_ids_list['name'], tracks_ids_list['artists'][0]['name'], tracks_ids_list['external_urls']['spotify']]
    return dictionary_of_results


def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(e)

    return conn

def query_recommend(track_id, db):
    return (db.execute(f"""
    select first_track, second_track , 
    count(distinct shared_playlists) Similarity
        , max(Second_popularity) Second_popularity
        ,round(count(distinct shared_playlists) / 
            max(Second_popularity),2) Percent
    from (
    select t1.track first_track, t2.track second_track,
    playlist shared_playlists
    from spotify_playlists t1
    join spotify_playlists t2
    using( playlist)
    where t1.track ="{track_id}"
    )
    join (
    select  track , count(distinct playlist) Second_popularity
    from spotify_playlists 
    where track !="{track_id}"
    group by 1
    )
    on second_track=track
    group by  first_track, second_track
    having first_track is not null and similarity>2 
    
    union all
    
    select first_track, second_track , 
    count(distinct shared_playlists) Similarity
        , max(Second_popularity) Second_popularity
        ,round(count(distinct shared_playlists) / 
            max(Second_popularity),2) Percent
    from (
    select t1.track first_track, t2.track second_track,
    playlist shared_playlists
    from spotify_playlists t1
    join spotify_playlists t2
    using( playlist)
    where t1.track ="{track_id}"
    )
    join (
    select  track , count(distinct playlist) Second_popularity
    from spotify_playlists 
    where track !="{track_id}"
    group by 1
    )
    on second_track=track
    group by  first_track, second_track
    having first_track is not null and similarity>1 and Percent>0.2
    order by Similarity desc, Percent desc
    limit 3 
    """).fetchall())
    
    