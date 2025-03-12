"""
MoodSwings - A FastAPI application that generates Spotify playlists based on emotional state.
This module handles the main application logic, including OAuth flow, API endpoints, and mood-based song selection.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
import httpx
import jsonify
import requests
from urllib.parse import urlencode
import os
from dotenv import load_dotenv
from playlistHandler import playlistHandler

# Initialize FastAPI app and configure templates
app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

load_dotenv()  # Load environment variables from .env file
session = {}

# Spotify API credentials and endpoints
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
CLIENT_ID = os.getenv('CLIENT_ID')
REDIRECT_URI = os.environ.get('REDIRECT_URI', 'http://127.0.0.1:8000/callback')

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1/'


@app.get('/', response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse('index.html', {"request": request})


@app.get("/login")
async def login(request: Request):
    scope = 'user-read-private user-read-email user-top-read playlist-read-private playlist-read-collaborative playlist-modify-private playlist-modify-public'

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
    """
    Handle Spotify OAuth callback.
    Exchanges authorization code for access token and stores it in session.
    """
    if 'error' in request.query_params:
        return jsonify({"error": request.query_params['error']})

    if 'code' in request.query_params:
        # Exchange authorization code for access token
        req_body = {
            'code': request.query_params['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }
        response = requests.post(TOKEN_URL, data=req_body)
        token_info = response.json()
        session['access_token'] = token_info['access_token']
        return RedirectResponse('/intermediate')
    

@app.get('/intermediate', response_class=HTMLResponse)
async def intermediate(request: Request):
    if 'access_token' not in session:
        return RedirectResponse('/')
    artists, genres = await get_top_artists_and_genres(session['access_token'])
    return templates.TemplateResponse("intermediate.html", {"request": request, 
                                                            "artists": artists, 
                                                            "genres": genres})

@app.get('/face-rec', response_class=HTMLResponse)
async def root(request: Request):
    id = await get_spotify_id(session['access_token'])
    session['playlist'] = playlistHandler(headers = {"Authorization": "Bearer " + session['access_token']}, 
                                          user_id=id)
    await session['playlist'].get_moodswings_playlist()
    print(session['playlist'].playlist_id)
    return templates.TemplateResponse("face-rec.html", {"request": request, 
                                                        'playlist_url': session['playlist'].playlist_id})


@app.post('/mood')
async def set_mood(mood: str, request: Request):
    if 'access_token' not in session:
        return RedirectResponse('/')

    matching_tracks = await get_song_for_mood(session, mood)

    await session['playlist'].get_moodswings_playlist()
    await session['playlist'].add_songs(matching_tracks)
    # Do something with the matching tracks
    return {"message": f'Mood set successfully to {mood}', "matching_tracks": matching_tracks}


async def get_spotify_id(token):
    url = 'https://api.spotify.com/v1/me'
    headers = {"Authorization": "Bearer " + token}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()  # Raise an exception for HTTP errors
            return response.json()['id']
    except httpx.HTTPStatusError as e:
        # Handle HTTP errors
        raise HTTPException(status_code=e.response.status_code, detail="App in development. Please contact us to enroll in beta.")
    except httpx.RequestError:
        # Handle request errors (e.g., network issues)
        raise HTTPException(status_code=500, detail="Internal server error")
        

async def get_top_artists_and_genres(token):
    url = 'https://api.spotify.com/v1/me/top/artists'
    headers = {"Authorization": "Bearer " + token}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()  # Raise an exception for HTTP errors
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="Book not found")
    except httpx.RequestError:
        raise HTTPException(status_code=500, detail="Internal server error")

    response = response.json()['items'][:10]
    
    top_artists = {}
    for index, item in enumerate(response):
        name = item['name']
        images_url = item['images'][0]['url']
        external_url = item['external_urls']['spotify']
        top_artists[index] = {'name': name, 'image': images_url, 'external_url': external_url}

    top_genres = []
    genre_list = [genre['genres'] for genre in response]
    for genre_l in genre_list:
        for genre in genre_l:
            top_genres.append(genre)
    top_genres = list(set(top_genres))  # remove duplicates

    return top_artists, top_genres


async def get_song_for_mood(session, mood):
    """
    Get song recommendations based on user's mood and top artists.
    
    Args:
        session: Current user session containing access token
        mood: Detected emotional state (happy, sad, angry, etc.)
    
    Returns:
        list: List of Spotify track URIs matching the mood
    
    The function uses Spotify's audio features to match songs with emotional states:
    - Valence: Represents musical positiveness
    - Energy: Represents intensity and activity
    - Danceability: How suitable for dancing
    - Tempo: Overall tempo of the track
    """
    if 'access_token' not in session:
        return RedirectResponse('/')

    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }

    # Get user's top 5 artists for personalized recommendations
    response = requests.get(API_BASE_URL + 'me/top/artists?limit=5', headers=headers)
    if response.status_code != 200:
        raise Exception("Failed to get top artists")
    top_artists = response.json()['items']
    artist_ids = [artist['id'] for artist in top_artists]
    artist_ids_str = ','.join(artist_ids)

    matching_tracks = []

    # Base parameters for recommendations
    params = {
        'limit': 10,
        'seed_artists': artist_ids_str,
    }

    # Adjust audio features based on emotional state
    if mood == 'neutral':
        params.update({
            'min_valence': 0.4,
            'max_valence': 0.7  # Balanced emotional tone
        })
    elif mood == 'happy':
        params.update({
            'min_valence': 0.7,  # High positiveness
            'min_energy': 0.55,  # Energetic
            'min_danceability': 0.6  # Danceable
        })
    elif mood == 'sad':
        params.update({
            'max_valence': 0.3,  # Low positiveness
            'max_energy': 0.45,  # Low energy
            'max_tempo': 95  # Slower tempo
        })
    elif mood == 'surprised':
        params.update({
            'min_valence': 0.6,
            'max_valence': 0.8,
            'min_energy': 0.6,
            'max_energy': 0.8,
            'max_danceability': 0.5
        })
    elif mood == 'fearful':
        params.update({
            'max_valence': 0.4,
            'min_energy': 0.5,
            'max_mode': 0
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

    # Get track recommendations based on mood parameters
    track_response = requests.get(API_BASE_URL + 'recommendations', headers=headers, params=params)
    if track_response.status_code != 200:
        raise Exception("Failed to get recommendations", track_response.status_code)
    recommended = track_response.json()['tracks']
    
    # Extract track URIs for playlist addition
    matching_tracks = [track['uri'] for track in recommended]
    return matching_tracks