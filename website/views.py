from flask import Blueprint, render_template, request, url_for, redirect, session
from .spotify_funcs import query_recommend, create_connection, get_option_songs
from spotipy import SpotifyException
from spotipy.oauth2 import SpotifyClientCredentials
import os 
import spotipy
from werkzeug.utils import redirect
import json

views = Blueprint('view', __name__)

os.environ['SPOTIPY_CLIENT_ID'] = "40562dc726d3436e8379e5d675d483d8"
os.environ['SPOTIPY_CLIENT_SECRET'] = "3798edc98a79485bb91c1a5afd9f8c6b"
spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())

@views.route('/', methods=['GET','POST'])
@views.route('/home', methods=['GET','POST'])
def home():
    data = request.form
    if request.method == 'GET':
        return render_template("home.html")
    else:
        track = request.form.get('track')
        similar_songs = get_option_songs(client=spotify, track_name_or_id=track, type_of_id='Name')
        return render_template("song_options.html", similar_songs=similar_songs)

@views.route("/recommend_track", methods=['GET','POST'])
def recommend_track():
    data = json.loads(request.data)
    print('*'*8)
    print(data, 'data')
    print('*'*8)
    track_id = data['track_id']
    print(track_id)
    results_of_algorithm = query_recommend(track_id=track_id, db=create_connection("/Users/tomerpeker/Side Projects/spotify_db.db"))
    song_options = {}
    print(results_of_algorithm, "RES")
    for res in results_of_algorithm:
        song_options.update(get_option_songs(client=spotify, track_name_or_id=res[1], type_of_id='ID'))
    messages = json.dumps(song_options)
    session['messages'] = messages
    return redirect(url_for("view.recommend_track_results"))

@views.route("/recommend_track_results", methods=['GET','POST'])
def recommend_track_results():
    print("9"*10)
    # messages = request.args['messages']  # counterpart for url_for()
    messages = session['messages']       # counterpart for session
    similar_songs = json.loads(messages)
    print(similar_songs, 'similar')
    print(messages, 'mess')
    return render_template("song_recommend.html", similar_songs=similar_songs)

@views.route("/loading", methods=['POST'])
def loading():
    track_id = json.loads(request.data)['track_id']
    print(track_id)
    messages = json.dumps(track_id)
    session['messages'] = messages
    return redirect(url_for("view.loading"))

@views.route("/loading_page", methods=['GET'])
def loading_page():
    messages = session['messages']       # counterpart for session
    track_id = json.loads(messages)
    return render_template("loading.html", track_id=track_id)