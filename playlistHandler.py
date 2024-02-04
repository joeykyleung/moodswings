import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles


class playlistHandler():

    def __init__(self, headers, user_id):
        self.headers = headers
        self.user_id = user_id
        self.playlist_id = None
    
    # get all playlists from user
    async def get_moodswings_playlist(self):
        url = f'https://api.spotify.com/v1/users/{self.user_id}/playlists?limit=50'
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()  # Raise an exception for HTTP errors
        except httpx.HTTPStatusError as e:
            # Handle HTTP errors
            raise HTTPException(status_code=e.response.status_code, detail="Playlists not found")
        except httpx.RequestError:
            # Handle request errors (e.g., network issues)
            raise HTTPException(status_code=500, detail="Internal server error")
        
        response = response.json()['items']
        
        playlist_found = False
        # search for playlist in list of playlists
        for i in range(len(response)):
            if response[i]['name'] == 'MoodSwings playlist':
                playlist_found = True
                playlist_id = response[i]['id']
                # delete songs if there are tracks in the playlist
                if response[i]['tracks']['total'] > 0:
                    print('Playlist contains songs already')
                    await self.delete_songs(playlist_id)
                break

        if not playlist_found:
            # create playlist
            playlist_id = await self.create_playlist()
            
        self.playlist_id = playlist_id


    async def delete_songs(self, playlist_id):
        url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks?limit=50'
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()  # Raise an exception for HTTP errors
        except httpx.HTTPStatusError as e:
            # Handle HTTP errors
            raise HTTPException(status_code=e.response.status_code, detail="No songs found in playlist")
        except httpx.RequestError:
            # Handle request errors (e.g., network issues)
            raise HTTPException(status_code=500, detail="Internal server error")

        response = response.json()['items']
        songs_to_delete = []
        for i in range(len(response)):
            songs_to_delete.append(response[i]['track']['id'])
        
        url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
        body = {
            "tracks": [{"uri": 'spotify:track:' + track} for track in songs_to_delete]
        }

        print(body)

        with httpx.Client() as client:
            response = client.request("DELETE", url, headers=self.headers, json=body)

        # Handle the response as needed
        if response.status_code == 200:
            print("Tracks deleted successfully!")
        else:
            print(f"Failed to delete tracks. Status code: {response.status_code}, Response: {response.json()}")



    async def create_playlist(self):
        print('Creating playlist')

        url = f'https://api.spotify.com/v1/users/{self.user_id}/playlists'
        body = {
                "name": "MoodSwings playlist",
                "description": "Playlist created by MoodSwings",
                "public": "false"
                }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=body, headers=self.headers)
                response.raise_for_status()  # Raise an exception for HTTP errors
        except httpx.HTTPStatusError as e:
            # Handle HTTP errors
            raise HTTPException(status_code=e.response.status_code, detail="Playlists not found")
        except httpx.RequestError:
            # Handle request errors (e.g., network issues)
            raise HTTPException(status_code=500, detail="Internal server error")
        
        response = response.json()['id']
        return response


    async def add_songs(self, songs):

        # await self.get_moodswings_playlist()

        print('Adding songs')

        url = f'https://api.spotify.com/v1/playlists/{self.playlist_id}/tracks'
        body = {
                "uris": songs
                }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=body, headers=self.headers)
                response.raise_for_status()  # Raise an exception for HTTP errors
        except httpx.HTTPStatusError as e:
            # Handle HTTP errors
            raise HTTPException(status_code=e.response.status_code, detail="Playlists not found")
        except httpx.RequestError:
            # Handle request errors (e.g., network issues)
            raise HTTPException(status_code=500, detail="Internal server error")
        
        print('Added songs to playlist')