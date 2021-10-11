import sqlite3
from sqlite3 import Error
import os
import spotipy
from spotipy import SpotifyClientCredentials


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


if __name__ == "__main__":
    db = create_connection("/Users/tomerpeker/Side Projects/spotify_db.db")
    print('Algo')
    print(db.execute("""
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
    where t1.track ='0tgVpDi06FyKpA1z0VMD4v'
    )
    join (
    select  track , count(distinct playlist) Second_popularity
    from spotify_playlists 
    where track !='0tgVpDi06FyKpA1z0VMD4v'
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
    where t1.track ='0tgVpDi06FyKpA1z0VMD4v'
    )
    join (
    select  track , count(distinct playlist) Second_popularity
    from spotify_playlists 
    where track !='0tgVpDi06FyKpA1z0VMD4v'
    group by 1
    )
    on second_track=track
    group by  first_track, second_track
    having first_track is not null and similarity>1 and Percent>0.2
    order by Similarity desc, Percent desc
    limit 3 
    """).fetchall())
    print('Find Dup Rows')
    print(db.execute("""
    select playlist,track, count(*) cnt
    from spotify_playlists
    group by 1,2 
    having cnt>1
    """).fetchall())
    print('Find Popular Tracks')
    print(db.execute("""
            select track,count(distinct playlist) cnt
            from spotify_playlists
            group by 1
            having cnt>1
            order by 2 desc
            limit 10
            """).fetchall())
    print("Hopw many Tracks?")
    print(db.execute("""
                select count(Distinct track)
                from spotify_playlists
                """).fetchall())
    print('Search for specific Track')
    print(db.execute("""
        select *
        from spotify_playlists
        where track ='5uraJqtCBvLpwt3VeomZdq'
        
        """).fetchall())
    print('Search for specific Playlist')
    print(db.execute("""
            select *
            from spotify_playlists
            where playlist ='2kNSWUQbpvwHBXSTwQYk3O'

            """).fetchall())

    db = create_connection("spotify_db.db")
    os.environ['SPOTIPY_CLIENT_ID'] = "40562dc726d3436e8379e5d675d483d8"
    os.environ['SPOTIPY_CLIENT_SECRET'] = "3798edc98a79485bb91c1a5afd9f8c6b"
    called_spotify_number = 0
    spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    called_spotify_number += 1
    words_in_playlist = "That Feeling"

    # tracks_ids_list = spotify.search(q=words_in_playlist, limit=50, type='track')['tracks']['items']
    # # print(playlist_ids_list)
    # for i in tracks_ids_list:
    #     print(i['name'], i['id'], i['artists'][0]['name'], i['external_urls']['spotify'])
    # id_ = '00bWFs6B1WDg8m03bAjsf6'
    # playlist_ids_list = spotify.search(q=words_in_playlist, limit=50, type='playlist')['playlists']['items']
    # d = []
    # for p in playlist_ids_list:
    #     for page in range(0, 1000, 50):
    #         items_in_playlist = spotify.playlist_items(p['id'], limit=50, offset=page,
    #                                                    fields="items.track.id,items.track.id,total",
    #                                                    additional_types=('track',))['items']
    #         for t in items_in_playlist:
    #             if t['track'] is not None:
    #                 if t['track']['id'] == id_:
    #                     d.append([(p, t1) for t1 in items_in_playlist])
    # print(d)
