from flask import Blueprint, url_for, session
from flask import g
import requests
import flask
import secrets
from hashlib import sha3_256
from  urllib import parse
import json
from requests.sessions import Request
from werkzeug.utils import redirect
from werkzeug.wrappers import response

client_id = "40562dc726d3436e8379e5d675d483d8"
redirect_uri = "http://127.0.0.1:5000/process_login/"

auth = Blueprint('auth', __name__)

def generate_code_verifier():         
    return secrets.token_urlsafe(128)

def generate_code_challenge(s):
    return bytes(sha3_256(bytes(s, 'utf-8')).hexdigest(), 'utf-8')



def generate_state():
    return secrets.token_urlsafe(128)

def generate_auth_uri(challenge, client_id, redirect_uri, state=None):
    return f"""https://accounts.spotify.com/authorize?response_type=code&client_id={client_id}&redirect_uri={parse.quote(redirect_uri)}&{'' if state is None else "state="+state+"&"}
    code_challenge={challenge}&code_challenge_method=S256"""

@auth.route('/login_to_spotify')
def login_to_spotify():

    return "<p> Login </p>"

@auth.route('/process_login/', methods=['GET', 'POST'])
def process_login():
    print("there")
    request = flask.request
    print(request.args)
    if request.args.get('code'):
        code = request.args.get('code')
        state = request.args.get('state')
        session['stage'] = json.dumps({"stage": "Passed First"})
        data = {"client_id": client_id,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": session['verifier']}
        print("before redirect, code:", code)
        url_of_request_post = f"https://accounts.spotify.com/api/token?client_id={client_id}&grant_type=authorization_code&code={parse.quote(code)}&redirect_uri={parse.quote(redirect_uri)}&code_verifier={parse.quote(session['verifier'])}"

        print(url_of_request_post)
        res = requests.post(url_of_request_post)
        # access_token = res.body.get('access_token')
        # print(res.content)
        state = request.args.get('state')
        print(res)
    
    return redirect('/')
    
    

@auth.route('/auth_process')
def auth_process():
    code_verifier = generate_code_verifier()
    session['verifier'] = code_verifier
    code_challenge = generate_code_challenge(code_verifier)
    auth_uri = generate_auth_uri(challenge=code_challenge, client_id=client_id,
                                redirect_uri=redirect_uri)

    return redirect(auth_uri)
