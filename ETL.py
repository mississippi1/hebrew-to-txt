import sqlite3
from sqlite3 import Error
import time


def create_connection(db_file: str):
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
        c.execute('''CREATE TABLE IF NOT EXISTS spotify_playlists_etl
                             (track_1 text, track_2 text, shared int,
                             UNIQUE(track_1, track_2)
                             )''')
        c.execute('''CREATE TABLE IF NOT EXISTS spotify_track_popularity
                             (track text, popularity int,
                             UNIQUE(track)
                             )''')
        print(1)
        # commit the changes to db
        conn.commit()
    except Error as e:
        print(e)

    return conn


if __name__ == "__main__":
    t = time.time()
    db_raw = create_connection("/Users/tomerpeker/Side Projects/spotify_db.db")
    db_agg = create_connection("/Users/tomerpeker/Side Projects/spotify_db_agg.db")
    cur_raw = db_raw.cursor()
    cur_agg = db_agg.cursor()
    # cur.execute("""
    #         delete from spotify_playlists_etl""")
    # db.commit()
    # cur.execute("""
    #     delete from spotify_track_popularity""")
    # db.commit()
    print(cur_raw.execute("""SELECT 
    count(*), count(distinct track), count(Distinct playlist) from spotify_playlists""").fetchall())
    # cur_raw.execute("""
    # insert into spotify_playlists_etl (track_1, track_2, shared)
    # select t1.track track_1, t2.track track_2,
    # count(distinct t1.playlist) Similarity
    # from spotify_playlists t1
    # join spotify_playlists t2
    # using( playlist)
    #  group by 1,2""")
    # cur.execute("""
    #     delete from spotify_track_popularity""")
    # db.commit()
    # print(cur.execute("""
    # select count(*) from spotify_playlists_etl""").fetchall())
