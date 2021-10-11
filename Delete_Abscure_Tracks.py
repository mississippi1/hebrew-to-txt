import sqlite3
from sqlite3 import Error


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
    cur = db.cursor()
    print(cur.execute("select count(track) from ("
                      "select track from spotify_playlists group by 1 having count(distinct playlist) = 2)").fetchall())
    sql = 'DELETE FROM spotify_playlists WHERE track in (' \
          'select track from spotify_playlists group by 1 having count(distinct playlist) =1) '
    cur.execute(sql)
    db.commit()
