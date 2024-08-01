import os
import time
import certifi
import spotipy
from config import *
from rpi_ws281x import *
from spotipy.oauth2 import *
from pymongo import MongoClient
from multiprocessing import Process

def spotifyInit():
    # Setup Spotify
    auth_manager = SpotifyOAuth(
        SPOTIFY_CLIENT,
        SPOTIFY_SECRET,
        "http://localhost:5173/callback",
        scope="user-modify-playback-state",
        cache_path="/home/madspi/Spotify/.cache",
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)
    spAuth = Process(target=spotifyAuth)
    spAuth.start()
    
    # Set up spotify manager
    spotifyManager = Process(target=manageSongRequests, args=(sp,))
    spotifyManager.start()
    return sp

def spotifyAuth():
    while True:
        time.sleep(60)
        auth_manager = SpotifyOAuth(
            SPOTIFY_CLIENT,
            SPOTIFY_SECRET,
            "http://localhost:5173/callback",
            scope="user-modify-playback-state",
            cache_path="/home/madspi/Spotify/.cache",
        )
        sp = spotipy.Spotify(auth_manager=auth_manager)
        
        rpiOnline = False
        devices = sp.devices()['devices']
        for device in devices:
            if device['id'] == SPOTIFY_DEVICE_ID:
                rpiOnline = True
                break
        if not rpiOnline:
            os.system("sudo systemctl restart raspotify")
            
def manageSongRequests(sp):
    lastCall = time.time()
    db = MongoClient(MDB_CONN_STR, tlsCAFile=certifi.where())['test']
    stateCol = db["spotifies"]
    previousSearch = ''
    search = ''
    requestSong = ['', '']
    previousPlayState = 0
    while True:
        state = None
        while state == None:
            try:
                state = stateCol.find_one()
            except:
                db = MongoClient(MDB_CONN_STR, tlsCAFile=certifi.where())['test']
                stateCol = db["spotifies"]
                state = stateCol.find_one()
                
        # Get search results for the user's input
        previousSearch = search
        search = state['input']
        if search != '' and search != previousSearch:
            try:
                searchResults = sp.search(search, 3, 0, "track,playlist")
                playlists = searchResults['playlists']['items']
                formattedPlaylists = []
                for playlist in playlists:
                    formattedPlaylists.append([playlist['name'], playlist['uri'], playlist['images'][0]['url']])

                tracks = searchResults['tracks']['items']
                formattedTracks = []
                for track in tracks:
                    formattedTracks.append([track['name'], track['uri'], track['album']['images'][0]['url']])
                
                searchResults = formattedPlaylists + formattedTracks
                stateCol.update_one(state, {'$set': {'searchResults': searchResults}})
            except:
                pass
        elif search == '' and search != previousSearch:
            stateCol.update_one(state, {'$set': {'searchResults': []}})
        
        # Start playing the requested song
        requestSong = state['songRequest']
        if requestSong[0] != '':
            try:
                stateCol.update_one(state, {'$set': {'currentSong': requestSong, 'songRequest': ['', ''], 'playState': 1, 'playControl': 0}})
                if 'playlist' in requestSong[1]:
                    sp.start_playback(
                        SPOTIFY_DEVICE_ID,
                        context_uri=requestSong[1],
                        position_ms=0,
                    )
                    sp.shuffle(True, SPOTIFY_DEVICE_ID)
                    sp.next_track(SPOTIFY_DEVICE_ID)
                elif 'track' in requestSong[1]:
                    sp.shuffle(False, SPOTIFY_DEVICE_ID)
                    sp.start_playback(
                        SPOTIFY_DEVICE_ID,
                        uris=[requestSong[1]],
                        position_ms=0,
                    )
            except:
                pass
        
        # Update current song and play state
        currentSong = state['currentSong']
        if currentSong[0] != '' and time.time() - lastCall > 1:
            lastCall = time.time()
            try:
                current = sp.currently_playing()
                song = current["item"]
                uri = song["uri"]
                name = song["name"]
                if uri != currentSong[1]:
                    stateCol.update_one(state, {'$set': {'currentSong': [name, uri]}})
                
                globalPlayState = current["is_playing"]
                if globalPlayState and previousPlayState == 0:
                    stateCol.update_one(state, {'$set': {'playState': 1}})
                    previousPlayState = 1
                elif not globalPlayState and previousPlayState == 1:
                    stateCol.update_one(state, {'$set': {'playState': 0}})
                    previousPlayState = 0
            except:
                pass
            
        # Pause / Resume
        requestPlayState = state['playState']
        if requestPlayState != previousPlayState:
            previousPlayState = requestPlayState
            try:
                if requestPlayState == 0:
                    sp.transfer_playback(
                        SPOTIFY_DEVICE_ID,
                        force_play=False,
                    )
                    sp.pause_playback(
                        SPOTIFY_DEVICE_ID
                    )
                elif requestPlayState == 1:
                    sp.transfer_playback(
                        SPOTIFY_DEVICE_ID,
                        force_play=True,
                    )
                    # sp.start_playback(
                    #     SPOTIFY_DEVICE_ID
                    # )
            except:
                pass
        
        # Prev / Next
        requestControlPlayState = state['controlPlayState']
        if requestControlPlayState != 0:
            if requestControlPlayState == 1:
                try:
                    sp.transfer_playback(
                        SPOTIFY_DEVICE_ID,
                        force_play=True,
                    )
                    sp.next_track(
                        SPOTIFY_DEVICE_ID
                    )
                    # sp.start_playback(
                    #     SPOTIFY_DEVICE_ID
                    # )
                    stateCol.update_one(state, {'$set': {'controlPlayState': 0, 'playState': 1}})
                except:
                    pass
            elif requestControlPlayState == -1:
                try:
                    sp.transfer_playback(
                        SPOTIFY_DEVICE_ID,
                        force_play=True,
                    )
                    sp.previous_track(
                        SPOTIFY_DEVICE_ID
                    )
                    # sp.start_playback(
                    #     SPOTIFY_DEVICE_ID
                    # )
                    stateCol.update_one(state, {'$set': {'controlPlayState': 0, 'playState': 1}})
                except:
                    pass