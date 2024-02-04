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

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

load_dotenv()  # Load variables from .env file
session = {}

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

    if 'error' in request.query_params:
        return jsonify({"error": request.query_params['error']})

    if 'code' in request.query_params:
        # get access token
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
        print(session)
        return RedirectResponse('/intermediate')
    

@app.get('/intermediate', response_class=HTMLResponse)
async def intermediate(request: Request):
    if 'access_token' not in session:
        return RedirectResponse('/')
    artists, genres = await get_top_artists_and_genres(session['access_token'])
    print(artists)
    return templates.TemplateResponse("intermediate.html", {"request": request, 
                                                            "artists": artists, 
                                                            "genres": genres})


@app.get('/face-rec', response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("face-rec.html", {"request": request})


@app.post('/mood')
async def set_mood(mood: str):
    print(mood)
    # Do something with the mood parameter
    return {"message": f'Mood set successfully to {mood}'}


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
        raise HTTPException(status_code=e.response.status_code, detail="Book not found")
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
        top_artists[index] = {'name': name, 'image': images_url}

    top_genres = []
    genre_list = [genre['genres'] for genre in response]
    for genre_l in genre_list:
        for genre in genre_l:
            top_genres.append(genre)
    top_genres = list(set(top_genres))  # remove duplicates

    return top_artists, top_genres
