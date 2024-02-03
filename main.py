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

MOOD_FEATURES = {
    "neutral": {"valence": (0.3, 0.7), "energy": (0.3, 0.7)},
    "fearful": {"valence": (0, 0.4), "energy": (0.2, 0.6)},
    "happy": {"valence": (0.7, 1.0), "energy": (0.7, 1.0)},
    "sad": {"valence": (0, 0.3), "energy": (0, 0.3)},
    "angry": {"valence": (0, 0.5), "energy": (0.7, 1.0)},
    "disgusted": {"valence": (0, 0.4), "energy": (0.4, 0.7)},
    "surprised": {"valence": (0.5, 1.0), "energy": (0.5, 1.0)}
}

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

    # Filter tracks based on mood
    matching_tracks = []

    for track in top_tracks:
        track_id = track['id']
        feature_response = requests.get(API_BASE_URL + f'audio-features/{track_id}', headers=headers)
        if feature_response.status_code != 200:
            raise Exception("Failed to get track audio features")
        track_features = feature_response.json()
        print(track_features)

    random_track = random.choice(top_tracks)
    print(random_track['id'], mood)
    return random_track['id']

    
    # # Select a random track - for now, mood is not used to filter tracks
    # random_track = random.choice(top_tracks)
    # print (random_track['id'])
    # return random_track['id']


# def select_tracks(mood: str) -> Optional[str]:
#     global access_token
#     if not access_token:
#         raise Exception("Access token is not available")

#     headers = {
#         'Authorization': f'Bearer {access_token}'
#     }

#     try:
#         # Get user's top artists
#         response = requests.get(API_BASE_URL + 'me/top/artists', headers=headers)
#         response.raise_for_status()
#         top_artists = response.json()['items']

#         # Select a random artist
#         random_artist = random.choice(top_artists)

#         # Get top tracks of the selected artist
#         artist_id = random_artist['id']
#         response = requests.get(f'{API_BASE_URL}artists/{artist_id}/top-tracks?country=US', headers=headers)
#         response.raise_for_status()
#         top_tracks = response.json()['tracks']

#     except requests.RequestException as e:
#         print(f"Failed to fetch data from Spotify: {e}")
#         return None

#     top_tracks_uri = [track['uri'] for track in top_tracks]

#     # Select a track that matches the mood
#     selected_track_uri = select_tracks(API_BASE_URL, headers, top_tracks_uri, mood)
#     return selected_track_uri

# def get_song_for_mood(api_url: str, headers: dict, top_tracks_uri: list, mood: str) -> Optional[str]:
#     print("...selecting tracks")

#     mood_features = MOOD_FEATURES.get(mood, {"valence": (0, 1), "energy": (0, 1)})
#     valence_range = mood_features["valence"]
#     energy_range = mood_features["energy"]

#     matching_tracks = []

#     for track_uri in top_tracks_uri:
#         track_id = track_uri.split(":")[-1]
#         try:
#             response = requests.get(f"{api_url}audio-features/{track_id}", headers=headers)
#             response.raise_for_status()

#             track_features = response.json()
#             if (valence_range[0] <= track_features["valence"] <= valence_range[1] and
#                     energy_range[0] <= track_features["energy"] <= energy_range[1]):
#                 matching_tracks.append(track_uri)

#         except requests.RequestException:
#             continue

#     if matching_tracks:
#         print ("mood: ", mood)
#         track = random.choice(matching_tracks)
#         print (track)
#         return track
#     else:
#         # If no matching tracks, return a random track from the list
#         return random.choice(top_tracks_uri) if top_tracks_uri else None





