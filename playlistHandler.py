"""
PlaylistHandler - A class for managing Spotify playlists in the MoodSwings application.
This module handles all playlist-related operations including creation, deletion, and song management.
"""

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles


class playlistHandler():
    """
    A class to handle all Spotify playlist operations.
    
    This class manages the creation and modification of the MoodSwings playlist,
    including adding and removing songs based on the user's emotional state.
    
    Attributes:
        headers (dict): Authorization headers for Spotify API requests
        user_id (str): Spotify user ID
        playlist_id (str): ID of the MoodSwings playlist
    """

    def __init__(self, headers, user_id):
        """
        Initialize the playlist handler with user credentials.
        
        Args:
            headers (dict): Authorization headers for Spotify API requests
            user_id (str): Spotify user ID
        """
        self.headers = headers
        self.user_id = user_id
        self.playlist_id = None
    
    async def get_moodswings_playlist(self):
        """
        Get or create the MoodSwings playlist for the user.
        
        This method searches for an existing MoodSwings playlist in the user's
        library. If found, it clears any existing tracks. If not found, it
        creates a new playlist.
        
        Returns:
            str: The playlist ID
        
        Raises:
            HTTPException: If there's an error accessing the Spotify API
        """
        url = f'https://api.spotify.com/v1/users/{self.user_id}/playlists?limit=50'
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail="Playlists not found")
        except httpx.RequestError:
            raise HTTPException(status_code=500, detail="Internal server error")
        
        response = response.json()['items']
        
        playlist_found = False
        # Search for existing MoodSwings playlist
        for playlist in response:
            if playlist['name'] == 'MoodSwings playlist':
                playlist_found = True
                playlist_id = playlist['id']
                # Clear existing tracks if any
                if playlist['tracks']['total'] > 0:
                    await self.delete_songs(playlist_id)
                break

        if not playlist_found:
            # Create new playlist if none exists
            playlist_id = await self.create_playlist()
            
        self.playlist_id = playlist_id

    async def delete_songs(self, playlist_id):
        """
        Remove all songs from the specified playlist.
        
        Args:
            playlist_id (str): ID of the playlist to clear
            
        Raises:
            HTTPException: If there's an error accessing the Spotify API
        """
        # Get current tracks in the playlist
        url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks?limit=50'
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail="No songs found in playlist")
        except httpx.RequestError:
            raise HTTPException(status_code=500, detail="Internal server error")

        response = response.json()['items']
        
        # Prepare track IDs for deletion
        songs_to_delete = [track['track']['id'] for track in response]
        
        # Remove tracks from playlist
        url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
        body = {
            "tracks": [{"uri": f'spotify:track:{track}'} for track in songs_to_delete]
        }

        async with httpx.AsyncClient() as client:
            response = await client.delete(url, headers=self.headers, json=body)
            
        if response.status_code != 200:
            print(f"Failed to delete tracks. Status code: {response.status_code}")

    async def create_playlist(self):
        """
        Create a new MoodSwings playlist for the user.
        
        Returns:
            str: ID of the newly created playlist
            
        Raises:
            HTTPException: If there's an error creating the playlist
        """
        url = f'https://api.spotify.com/v1/users/{self.user_id}/playlists'
        body = {
                "name": "MoodSwings playlist",
                "description": "Playlist created by MoodSwings",
                "public": "false"
                }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=body, headers=self.headers)
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail="Failed to create playlist")
        except httpx.RequestError:
            raise HTTPException(status_code=500, detail="Internal server error")
        
        return response.json()['id']

    async def add_songs(self, songs):
        """
        Add songs to the MoodSwings playlist.
        
        Args:
            songs (list): List of Spotify track URIs to add
            
        Raises:
            HTTPException: If there's an error adding the songs
        """
        url = f'https://api.spotify.com/v1/playlists/{self.playlist_id}/tracks'
        body = {"uris": songs}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=body, headers=self.headers)
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail="Failed to add songs")
        except httpx.RequestError:
            raise HTTPException(status_code=500, detail="Internal server error")