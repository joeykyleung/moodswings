from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
import requests
from urllib.parse import urlencode
import os
import random
from dotenv import load_dotenv

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
    response = requests.get(API_BASE_URL + 'me/top/artists', headers=headers)
    if response.status_code != 200:
        raise Exception("Failed to get top artists")
    top_artists = response.json()['items']
    
    # Select a random artist
    random_artist = random.choice(top_artists)

    # Get top tracks of the selected artist
    artist_id = random_artist['id']
    response = requests.get(API_BASE_URL + f'artists/{artist_id}/top-tracks?country=US', headers=headers)
    if response.status_code != 200:
        raise Exception("Failed to get artist's top tracks")
    top_tracks = response.json()['tracks']
    
    # Select a random track - for now, mood is not used to filter tracks
    random_track = random.choice(top_tracks)
    print (random_track['external_urls']['spotify'])
    return random_track['external_urls']['spotify']


