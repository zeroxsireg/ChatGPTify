from flask import Flask, request, redirect, session, url_for
import os
from chatgptify import SpotifyPlaylist
import spotipy
from spotipy.oauth2 import SpotifyOAuth

app = Flask(__name__)
app.secret_key = os.urandom(24)  # for session handling

# Spotify OAuth Configuration
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID', '307b89a2e69744868e3858ab05e58331')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET', '8d7c4a6cd17448a0a25d25fe9ef215a4')
SPOTIFY_REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI', 'https://chat-gp-tify.vercel.app/callback')
SCOPE = 'playlist-modify-public playlist-modify-private user-library-read'

@app.route('/')
def index():
    # Create Spotify OAuth instance
    sp_oauth = SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SCOPE
    )
    
    # Get the authorization URL
    auth_url = sp_oauth.get_authorize_url()
    return f'''
        <h1>ChatGPTify</h1>
        <p>Click below to authorize with Spotify:</p>
        <a href="{auth_url}">Login with Spotify</a>
    '''

@app.route('/callback')
def callback():
    # Create Spotify OAuth instance
    sp_oauth = SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SCOPE
    )
    
    # Get the authorization code from the request
    code = request.args.get('code')
    
    if code:
        # Get the access token
        token_info = sp_oauth.get_access_token(code)
        session['token_info'] = token_info
        
        return redirect(url_for('create_playlist'))
    else:
        return 'Error: No authorization code received', 400

@app.route('/create-playlist')
def create_playlist():
    token_info = session.get('token_info')
    if not token_info:
        return redirect(url_for('index'))
    
    try:
        play = SpotifyPlaylist()
        # For demonstration, creating a simple ambient playlist
        play.ask_chatgpt(
            prompt="create a playlist with relaxing electronic ambient music suitable for deep focus and work",
            prompt_type="playlist"
        )
        play.create_playlist()
        play.ask_chatgpt(prompt="", prompt_type="name")
        play.save_playlist()
        
        return f'''
            <h1>Success!</h1>
            <p>Your playlist has been created.</p>
            <p>Check your Spotify account for the new playlist.</p>
            <a href="/">Create Another Playlist</a>
        '''
    except Exception as e:
        return f'Error creating playlist: {str(e)}', 500

if __name__ == '__main__':
    app.run(debug=True) 