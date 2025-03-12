# MoodSwings: Emotion-Driven Spotify Playlist Generator

MoodSwings is an innovative web application that generates personalized Spotify playlists based on your emotional state, detected through facial recognition. By combining the Spotify Web API with emotion detection, it creates a unique music experience that adapts to your mood in real-time.

## Demo

Watch the demo here: https://www.youtube.com/watch?v=RxarAuW3nMM

## Features

- 🎵 Spotify API Integration for personalized music recommendations
- 😊 Real-time facial emotion detection
- 🎯 Smart playlist generation based on musical features
- 🔄 Dynamic playlist updates
- 🎨 Clean, modern web interface

## Technical Stack

- **Backend**: FastAPI (Python)
- **Frontend**: HTML/Jinja2 Templates
- **Authentication**: OAuth 2.0 with Spotify API
- **API Integration**: Spotify Web API
- **Async Operations**: httpx for asynchronous HTTP requests

## Technical Challenges & Solutions

### 1. Spotify API Integration
- **Challenge**: Managing OAuth 2.0 flow and token handling
- **Solution**: Implemented a robust authentication system using FastAPI's dependency injection and session management

### 2. Playlist Management
- **Challenge**: Efficient handling of playlist operations (creation, updates, deletions)
- **Solution**: Created a dedicated `playlistHandler` class with async methods for optimal performance

### 3. Mood-Based Song Selection
- **Challenge**: Mapping emotional states to musical attributes
- **Solution**: Developed a sophisticated algorithm using Spotify's audio features (valence, energy, tempo) to match songs with emotional states:
  - Happy: High valence (>0.7), high energy (>0.55)
  - Sad: Low valence (<0.3), low energy (<0.45)
  - Angry: High energy (>0.6), high loudness (>-5dB)
  - Neutral: Balanced valence (0.4-0.7)

## Setup & Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables in `.env`:
   ```
   CLIENT_SECRET=your_spotify_client_secret
   CLIENT_ID=your_spotify_client_id
   REDIRECT_URI=your_redirect_uri
   ```
4. Run the application:
   ```bash
   uvicorn main:app --reload
   ```