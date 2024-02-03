from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
import jsonify
import requests
from urllib.parse import urlencode
import os
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
        # session['access_token'] = token_info['access_token']

        return RedirectResponse('/face-rec')

@app.get('/face-rec', response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("face-rec.html", {"request": request})


@app.post('/mood')
async def set_mood(mood: str):
    print(mood)
    # Do something with the mood parameter
    return {"message": f'Mood set successfully to {mood}'}
