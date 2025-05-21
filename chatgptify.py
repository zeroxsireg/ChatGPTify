import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import textwrap
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch


class SpotifyTrack():
    def __init__(self, uri, name, artist, album):
        self.uri = uri
        self.name = name
        self.artist = artist
        self.album = album


class SpotifyPlaylist():
    def __init__(self) -> None:      
        scope = 'playlist-modify-public playlist-modify-private user-library-read'
        
        # Initialize the model and tokenizer
        print("Loading model and tokenizer (this might take a minute)...")
        self.model_name = "google/flan-t5-base"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
        
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=os.environ['SPOTIFY_CLIENT_ID'],
                                               client_secret=os.environ['SPOTIFY_CLIENT_SECRET'],
                                               redirect_uri=os.environ['SPOTIFY_REDIRECT_URI'],
                                               scope=scope))

        self.playlist = None
        self.name = "AI presents..."

        self.playlist_response = None
        self.last_response = None
    

    def ask_chatgpt(self, prompt : str, prompt_type : str = "", display=True) -> None:
        """Ask prompt to the local model

        Args:
            prompt (str): User prompt to ask. 
                * prompt_type = "playlist" - A fixed start string is appended: 
                    "Provide a playlist containing songs " ...
                * prompt_type = "name" - Prompt is fixed, provided string is not considered
                    "What might be a suitable and creative name for this playlist?" \
                     " Only provide the name and no other details."
                * prompt_type = "" - User can ask any prompt
            
            prompt_type (str, optional): Selects the type of prompt. Defaults to "".
                * prompt_type = "playlist" - For playlist song suggestion
                * prompt_type = "name"     - For playlist name suggestion
                * prompt_type = ""         - Unrestricted prompts 

            display (bool, optional): Whether to display output. Defaults to True.

        Raises:
            RuntimeError: Upon model execution failure.
        """        
        print("Generating response...")
        
        if prompt_type == "playlist": 
            prompt = "Create a playlist with 10 songs " + prompt + "\nFormat: 1. Song Name by Artist Name\n2. Song Name by Artist Name\netc."
        elif prompt_type == "name":
            prompt = "What might be a suitable and creative name for this playlist?" \
                     " Only provide the name and no other details."
       
        try:
            # Tokenize and generate
            inputs = self.tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)
            outputs = self.model.generate(
                **inputs,
                max_length=256,
                num_return_sequences=1,
                temperature=0.7,
                do_sample=True,
                no_repeat_ngram_size=2
            )
            response_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            if prompt_type == "playlist": 
                self.playlist_response = response_text
            if prompt_type == "name": 
                self.name = str(response_text.replace('"',''))
            self.last_response = response_text
            
            if display:
                width = 70
                print("-" * width)
                print("     " * (width // 11) + "AI Response")
                prompt_str = textwrap.fill("Prompt: " + prompt)
                print(prompt_str)
                print("-" * width)
                display_str = textwrap.fill(response_text)
                print(display_str)
                print()
                print("-" * width)
                
        except Exception as e:
            raise RuntimeError(f"Failed to get response from model: {str(e)}")

    def create_playlist(self) -> None:
        """Queries Spotify API to retrieve tracks 
        """        
        query = self.playlist_response[self.playlist_response.find('1.'):].split('\n\n')[0].split('\n')
        query = [q[q.find('. ')+2:].replace('"', '') for q in query]

        print("Creating playlist...")
        playlist = []
        for q in query:
            try:
                if 'by' in q:
                    name, artist = q.split(' by ')
                    if '-' in artist: artist = artist[:artist.find('-')]
                    search_q = "{}%10artist:{}".format(name, artist)
                    r = self.sp.search(search_q)
                elif '-' in q:
                    name, artist = q.split(' - ')
                    search_q = "{}%10artist:{}".format(name, artist)
                    r = self.sp.search(search_q)
                else:
                    r = self.sp.search(q)
                item = r['tracks']['items'][0]  # Select the first track
                track = SpotifyTrack(uri=item['uri'], name=item['name'], 
                                     artist=item['artists'], album=item['album'])
                playlist.append(track)
            except:
                print("Track not found: {}".format(q))

        self.playlist = playlist

    
    def save_playlist(self, name : str = "") -> None:
        """Saves the created playlist under user account

        Args:
            name (str, optional): Name of the playlist. Uses the name created by ChatGPT or
                default name when not specified
        """
        print("Saving to library...")

        if not name: name = self.name

        user_id = self.sp.current_user()['id']
        self.sp.user_playlist_create(user=user_id, name=name, public=True)

        p_id = None
        for playlist in self.sp.user_playlists(user_id)['items']:
            if playlist['name'] == name:
                p_id = playlist['id']
                break
        
        tracks = [track.uri for track in self.playlist]
        self.sp.user_playlist_add_tracks(user=user_id, playlist_id=p_id, tracks=tracks)

