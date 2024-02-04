from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
import requests
from urllib.parse import urlencode
import os
import random
from dotenv import load_dotenv
from typing import Optional

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

load_dotenv()  # Load variables from .env file

CLIENT_SECRET = os.getenv('CLIENT_SECRET')
CLIENT_ID = os.getenv('CLIENT_ID')
REDIRECT_URI = os.environ.get('REDIRECT_URI', 'http://127.0.0.1:8000/callback')

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1/'

# Global variable to store access token
access_token = None


@app.get('/', response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse('index.html', {"request": request})


@app.get("/login")
async def login(request: Request):
    scope = 'user-read-private user-read-email user-top-read'

    params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'scope': scope,
        'redirect_uri': REDIRECT_URI,
        'show_dialog': True
    }

    auth_url = f"{AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(auth_url)


@app.get('/callback')
async def callback(request: Request):
    global access_token

    if 'error' in request.query_params:
        return {"error": request.query_params['error']}

    if 'code' in request.query_params:
        # Get access token
        req_body = {
            'code': request.query_params['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }
        response = requests.post(TOKEN_URL, data=req_body)
        token_info = response.json()
        access_token = token_info['access_token']
        return RedirectResponse('/face-rec')


@app.get('/face-rec', response_class=HTMLResponse)
async def face_rec(request: Request):
    return templates.TemplateResponse("face-rec.html", {"request": request})


@app.post('/mood')
async def set_mood(mood: str):
    try:
        song_url = get_song_for_mood(mood)
        return {"song_url": song_url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def get_song_for_mood(mood):
    global access_token
    if not access_token:
        raise Exception("Access token is not available")

    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    # Get user's top artists
    response = requests.get(API_BASE_URL + 'me/top/artists?limit=5', headers=headers)
    if response.status_code != 200:
        raise Exception("Failed to get top artists")
    top_artists = response.json()['items']
    artist_ids = []
    for artist in top_artists:
        artist_id = artist['id']
        artist_ids.append(artist_id)
    artist_ids_str = ','.join(artist_ids)

    matching_tracks = []

    params = {
        'limit': 5,
        'seed_artists': artist_ids_str,
    }
    if mood == 'neutral':
        params.update({
            'min_valence': 0.4,
            'max_valence': 0.7
        })
    elif mood == 'happy':
        params.update({
            'min_valence': 0.7,
            'min_energy': 0.5,
            'min_danceability': 0.6
        })
    elif mood == 'sad':
        params.update({
            'max_valence': 0.35,
            'max_energy': 0.4,
            'max_loudness': -7
        })
    elif mood == 'surprised':
        params.update({
            'min_valence': 0.6,
            'max_valence': 0.8,
            'min_energy': 0.6,
            'max_danceability': 0.5
        })
    elif mood == 'fearful':
        params.update({
            'max_valence': 0.4,
            'min_energy': 0.5
        })
    elif mood == 'angry':
        params.update({
            'max_valence': 0.4,
            'min_energy': 0.6,
            'min_loudness': -5
        })
    elif mood == 'disgusted':
        params.update({
            'max_valence': 0.5,
            'min_energy': 0.5
        })


    track_response = requests.get(API_BASE_URL + 'recommendations', headers=headers, params=params)
    if track_response.status_code != 200:
        raise Exception("Failed to get recommendations")
    recommended = track_response.json()['tracks']
    for track in recommended:
        track_id = track['id']
        matching_tracks.append(track_id)

    print(matching_tracks)
    return matching_tracks


