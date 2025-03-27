import spacy
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from textblob import TextBlob
import tensorflow as tf
from tensorflow.keras import layers, models
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
import time
import json
from datetime import datetime
import random
import threading

# Load environment variables
load_dotenv()

class UserPreferenceTracker:
    """Track and learn from user feedback and listening history"""
    def __init__(self, user_id, data_file='user_preferences.json'):
        self.user_id = user_id
        self.data_file = data_file
        self.user_data = self._load_user_data()
        
    def _load_user_data(self):
        """Load user data from file or create new profile"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    all_users = json.load(f)
                    if self.user_id in all_users:
                        return all_users[self.user_id]
            except:
                pass
                
        # Create new user profile if not found
        return {
            'liked_tracks': [],
            'disliked_tracks': [],
            'play_history': [],
            'emotion_preferences': {
                'happy': {'features': {}, 'artists': [], 'genres': []},
                'sad': {'features': {}, 'artists': [], 'genres': []},
                'angry': {'features': {}, 'artists': [], 'genres': []},
                'neutral': {'features': {}, 'artists': [], 'genres': []},
                'anxious': {'features': {}, 'artists': [], 'genres': []}
            }
        }
        
    def save_user_data(self):
        """Save user preferences to file"""
        all_users = {}
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    all_users = json.load(f)
            except:
                pass
                
        all_users[self.user_id] = self.user_data
        
        with open(self.data_file, 'w') as f:
            json.dump(all_users, f, indent=2)
            
    def record_play(self, track_id, track_info, emotion, features=None):
        """Record when a track is played"""
        self.user_data['play_history'].append({
            'track_id': track_id,
            'track_name': track_info.get('name', ''),
            'artist': track_info.get('artist', ''),
            'emotion': emotion,
            'timestamp': datetime.now().isoformat(),
            'features': features
        })
        self.save_user_data()
        
    def record_feedback(self, track_id, liked, emotion, track_features=None):
        """Record user feedback for a track"""
        if liked:
            if track_id not in self.user_data['liked_tracks']:
                self.user_data['liked_tracks'].append(track_id)
            if track_id in self.user_data['disliked_tracks']:
                self.user_data['disliked_tracks'].remove(track_id)
        else:
            if track_id not in self.user_data['disliked_tracks']:
                self.user_data['disliked_tracks'].append(track_id)
            if track_id in self.user_data['liked_tracks']:
                self.user_data['liked_tracks'].remove(track_id)
                
        # Update preferences for this emotion
        if track_features and emotion in self.user_data['emotion_preferences']:
            self._update_feature_preferences(emotion, track_features, liked)
            
        self.save_user_data()
        
    def _update_feature_preferences(self, emotion, features, liked):
        """Update feature preferences based on feedback"""
        prefs = self.user_data['emotion_preferences'][emotion]['features']
        
        # Initialize feature preferences if they don't exist
        for feature, value in features.items():
            if feature not in prefs:
                prefs[feature] = {'count': 0, 'sum': 0, 'avg': 0.5}
                
        # Update preferred feature values based on feedback
        weight = 1 if liked else 0.5  # Like feedback has more weight
        for feature, value in features.items():
            if isinstance(value, (int, float)):
                prefs[feature]['count'] += weight
                prefs[feature]['sum'] += value * weight
                prefs[feature]['avg'] = prefs[feature]['sum'] / prefs[feature]['count']
                
    def update_artist_preference(self, emotion, artist_id, liked):
        """Update artist preferences"""
        preferences = self.user_data['emotion_preferences'][emotion]
        
        if liked and artist_id not in preferences['artists']:
            preferences['artists'].append(artist_id)
        elif not liked and artist_id in preferences['artists']:
            preferences['artists'].remove(artist_id)
            
        self.save_user_data()
        
    def get_preferred_features(self, emotion):
        """Get preferred audio features for an emotion"""
        prefs = self.user_data['emotion_preferences'][emotion]['features']
        feature_targets = {}
        
        # If we have preference data, use it
        if prefs:
            for feature, data in prefs.items():
                if data['count'] > 0:
                    feature_targets[feature] = data['avg']
                    
        # Use more relevant plays to refine features
        relevant_plays = [play for play in self.user_data['play_history'] 
                         if play['emotion'] == emotion][-20:]
        
        # Check for repeat plays (songs played multiple times)
        track_counts = {}
        for play in relevant_plays:
            track_id = play['track_id']
            if track_id not in track_counts:
                track_counts[track_id] = 0
            track_counts[track_id] += 1
            
        # Find most replayed tracks as they're likely preferred
        favorite_tracks = [track_id for track_id, count in track_counts.items() 
                          if count > 1 and track_id in self.user_data['liked_tracks']]
        
        # Adjust features based on favorites
        if favorite_tracks:
            favorite_plays = [play for play in relevant_plays 
                             if play['track_id'] in favorite_tracks and play.get('features')]
            
            # Compute average features from favorites
            if favorite_plays:
                for feature in ['valence', 'energy', 'tempo', 'acousticness', 'danceability']:
                    values = [play['features'].get(feature, 0.5) for play in favorite_plays 
                             if feature in play.get('features', {})]
                    if values:
                        feature_targets[feature] = sum(values) / len(values)
        
        return feature_targets

    def get_dynamic_targets(self, emotion, default_ranges):
        """Get dynamically adjusted target ranges based on user preferences"""
        targets = {}
        preferred_features = self.get_preferred_features(emotion)
        
        # Start with defaults
        for feature, range_vals in default_ranges.items():
            # If we have learned preferences, adjust the range around them
            if feature in preferred_features:
                pref_val = preferred_features[feature]
                # Create a range centered around the preferred value
                range_width = range_vals[1] - range_vals[0]
                lower = max(0, pref_val - range_width/4)
                upper = min(1, pref_val + range_width/4)
                targets[feature] = (lower, upper)
            else:
                targets[feature] = range_vals
                
        return targets

    def get_favorite_genres(self, emotion, limit=5):
        """Get user's favorite genres for an emotion"""
        return self.user_data['emotion_preferences'][emotion]['genres'][:limit]
        
    def get_favorite_artists(self, emotion, limit=5):
        """Get user's favorite artists for an emotion"""
        return self.user_data['emotion_preferences'][emotion]['artists'][:limit]


class MellowMind:
    def __init__(self, user_id="default_user"):
        # Initialize NLP model
        self.nlp = spacy.load('en_core_web_sm')
        
        # Initialize emotion classifier
        self.emotion_classifier = self._build_emotion_classifier()
        
        # Initialize Spotify client with full permissions
        self.spotify = self._initialize_spotify()
        
        # Initialize user preference tracker
        self.user_id = user_id
        self.preferences = UserPreferenceTracker(user_id)
        
        # Initialize current playback state
        self.current_emotion = None
        self.current_track = None
        self.current_queue = []
        self.continuous_playback = False
        self.playback_thread = None
        self.stop_playback_thread = False
        
        # Default emotion to music features mapping
        self.default_emotion_features = {
            'happy': {'valence': (0.7, 1.0), 'energy': (0.7, 1.0), 'tempo': (120, 180), 
                      'danceability': (0.6, 1.0), 'acousticness': (0, 0.4)},
            'sad': {'valence': (0.0, 0.3), 'energy': (0.2, 0.5), 'tempo': (60, 90), 
                   'danceability': (0.2, 0.5), 'acousticness': (0.5, 1.0)},
            'angry': {'valence': (0.2, 0.5), 'energy': (0.8, 1.0), 'tempo': (140, 180), 
                     'danceability': (0.4, 0.8), 'acousticness': (0, 0.3)},
            'neutral': {'valence': (0.4, 0.6), 'energy': (0.4, 0.6), 'tempo': (90, 120), 
                       'danceability': (0.4, 0.6), 'acousticness': (0.3, 0.7)},
            'anxious': {'valence': (0.3, 0.5), 'energy': (0.3, 0.5), 'tempo': (70, 100), 
                        'danceability': (0.3, 0.5), 'acousticness': (0.6, 0.9)}
        }

    def _initialize_spotify(self):
        """Initialize Spotify client with necessary permissions"""
        return spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=os.getenv('SPOTIFY_CLIENT_ID'),
            client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
            redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI'),
            scope="user-library-read user-modify-playback-state user-read-playback-state streaming user-top-read user-read-recently-played"
        ))

    def _build_emotion_classifier(self):
        """Build and return emotion classification model"""
        model = models.Sequential([
            layers.Dense(128, activation='relu', input_shape=(300,)),
            layers.Dropout(0.3),
            layers.Dense(64, activation='relu'),
            layers.Dropout(0.3),
            layers.Dense(32, activation='relu'),
            layers.Dense(5, activation='softmax')
        ])
        model.compile(optimizer='adam',
                     loss='sparse_categorical_crossentropy',
                     metrics=['accuracy'])
        return model

    def get_available_devices(self):
        """Get list of available Spotify playback devices"""
        devices = self.spotify.devices()
        return devices['devices']

    def select_device(self, device_id=None):
        """Select specific device for playback"""
        devices = self.get_available_devices()
        
        if not devices:
            raise Exception("No available playback devices found")
        
        if device_id is None:
            # Use the first available device
            device_id = devices[0]['id']
            
        self.spotify.transfer_playback(device_id=device_id)
        return device_id

    def analyze_text_emotion(self, text):
        """Analyze emotion from text using NLP"""
        doc = self.nlp(text)
        blob = TextBlob(text)
        sentiment = blob.sentiment
        
        # Extract features
        features = {
            'polarity': sentiment.polarity,
            'subjectivity': sentiment.subjectivity,
            'word_count': len(doc),
            'exclamation_count': text.count('!'),
            'question_count': text.count('?'),
            'has_negation': any(token.dep_ == 'neg' for token in doc)
        }
        
        # Map sentiment to emotions (simplified mapping)
        if sentiment.polarity > 0.5:
            emotion = 'happy'
        elif sentiment.polarity < -0.5:
            emotion = 'sad'
        elif sentiment.subjectivity > 0.8 and features['has_negation']:
            emotion = 'angry'
        elif sentiment.subjectivity < 0.3:
            emotion = 'neutral'
        else:
            emotion = 'anxious'
        
        return emotion, features

    def get_track_audio_features(self, track_id):
        """Get audio features for a track from Spotify"""
        try:
            features = self.spotify.audio_features(track_id)[0]
            return features
        except:
            return None

    def get_recommendations_by_features(self, emotion, limit=20):
        """Get music recommendations based on emotional features and user preferences"""
        # Get dynamic targets adjusted by user preferences
        targets = self.preferences.get_dynamic_targets(emotion, self.default_emotion_features)
        
        # Get user's favorite artists for this emotion to use as seeds
        seed_artists = self.preferences.get_favorite_artists(emotion)
        
        # If no preferred artists, get some from user's general top artists
        if not seed_artists:
            try:
                top_artists = self.spotify.current_user_top_artists(limit=5, time_range='medium_term')
                seed_artists = [artist['id'] for artist in top_artists['items']]
            except:
                seed_artists = []
        
        # Get recently played tracks for seed selection
        recently_played = []
        try:
            recent = self.spotify.current_user_recently_played(limit=10)
            recently_played = [item['track']['id'] for item in recent['items']]
        except:
            pass
            
        # Get liked tracks for this emotion
        liked_tracks = [track_id for track_id in self.preferences.user_data['liked_tracks']
                       if any(play['track_id'] == track_id and play['emotion'] == emotion 
                             for play in self.preferences.user_data['play_history'])]
        
        # Prepare parameters for recommendation API
        params = {}
        
        # Prioritize seed tracks from user history
        seed_tracks = []
        if liked_tracks:
            # Use some liked tracks as seeds
            seed_tracks = random.sample(liked_tracks, min(2, len(liked_tracks)))
        elif recently_played:
            # Use some recent tracks as seeds
            seed_tracks = random.sample(recently_played, min(2, len(recently_played)))
        
        # Add seed artists if available
        seed_artists_subset = []
        if seed_artists:
            seed_artists_subset = random.sample(seed_artists, min(3, len(seed_artists)))
        
        # Add seeds to parameters (maximum of 5 total seeds)
        if seed_tracks:
            params['seed_tracks'] = seed_tracks[:5-len(seed_artists_subset)]
        if seed_artists_subset:
            params['seed_artists'] = seed_artists_subset
        
        # If no seeds available, get genre seeds
        if not seed_tracks and not seed_artists_subset:
            available_genres = self.spotify.recommendation_genre_seeds()['genres']
            genre_map = {
                'happy': ['pop', 'dance', 'party', 'happy'],
                'sad': ['sad', 'indie', 'ambient', 'piano'],
                'angry': ['rock', 'metal', 'punk', 'hardcore'],
                'neutral': ['indie', 'chill', 'alternative', 'folk'],
                'anxious': ['ambient', 'classical', 'piano', 'meditation']
            }
            
            recommended_genres = [g for g in genre_map.get(emotion, ['pop']) if g in available_genres]
            if recommended_genres:
                params['seed_genres'] = recommended_genres[:5]
        
        # Add target features
        for feature, (min_val, max_val) in targets.items():
            target_val = (min_val + max_val) / 2
            params[f'target_{feature}'] = target_val
            
        # Set number of tracks to return
        params['limit'] = limit
        
        # Get recommendations
        try:
            recommendations = self.spotify.recommendations(**params)
            
            # Filter out recently played tracks for freshness
            filtered_tracks = [track for track in recommendations['tracks'] 
                              if track['id'] not in recently_played[:5]]
            
            # If filtering removed too many, add some back
            if len(filtered_tracks) < 5 and recommendations['tracks']:
                filtered_tracks.extend([t for t in recommendations['tracks'] 
                                      if t not in filtered_tracks][:max(5, limit//2)-len(filtered_tracks)])
            
            return [{
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'uri': track['uri'],
                'id': track['id']
            } for track in filtered_tracks]
        except Exception as e:
            print(f"Error getting recommendations: {str(e)}")
            return []

    def create_playlist(self, tracks, emotion, name=None):
        """Create a Spotify playlist from a list of tracks"""
        try:
            # Create custom playlist name if not provided
            if not name:
                timestamp = datetime.now().strftime("%Y-%m-%d")
                name = f"MellowMind {emotion.capitalize()} - {timestamp}"
            
            # Create playlist
            user_id = self.spotify.current_user()['id']
            playlist = self.spotify.user_playlist_create(
                user_id, 
                name, 
                public=False,
                description=f"Mood-based playlist for {emotion} created by MellowMind"
            )
            
            # Add tracks to playlist
            if playlist and tracks:
                track_uris = [track['uri'] for track in tracks]
                self.spotify.playlist_add_items(playlist['id'], track_uris)
                
                return playlist['external_urls']['spotify']
        except Exception as e:
            print(f"Error creating playlist: {str(e)}")
        
        return None

    def play_music(self, track_uri, device_id=None):
        """Play music on specified device and record it"""
        try:
            if device_id is None:
                device_id = self.select_device()
                
            # Start playback
            self.spotify.start_playback(device_id=device_id, uris=[track_uri])
            
            # Get current playing track info
            current_track = self.spotify.current_user_playing_track()
            if current_track and current_track['item']:
                track_id = current_track['item']['id']
                track_name = current_track['item']['name']
                artist_name = current_track['item']['artists'][0]['name']
                
                # Get audio features
                audio_features = self.get_track_audio_features(track_id)
                
                # Record this play
                track_info = {
                    'name': track_name,
                    'artist': artist_name,
                    'uri': track_uri
                }
                self.preferences.record_play(track_id, track_info, self.current_emotion, audio_features)
                
                # Save current track info
                self.current_track = {
                    'id': track_id,
                    'name': track_name,
                    'artist': artist_name,
                    'uri': track_uri,
                    'features': audio_features
                }
                
                print(f"\nNow playing: {track_name} by {artist_name}")
                return True
                
        except spotipy.exceptions.SpotifyException as e:
            print(f"Spotify Error: {str(e)}")
            return False
        except Exception as e:
            print(f"Error playing music: {str(e)}")
            return False

    def play_music_continuous(self, initial_track_index=0):
        """Play music continuously from the queue"""
        # Stop any existing playback thread
        self.stop_playback_thread = True
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=2)
        
        self.stop_playback_thread = False
        self.continuous_playback = True
        
        # Start a new playback thread
        self.playback_thread = threading.Thread(
            target=self._playback_thread_func, 
            args=(initial_track_index,)
        )
        self.playback_thread.daemon = True
        self.playback_thread.start()
        
        print("\nContinuous playback started. Type any command ('pause', 'next', etc.) to control playback.")
        
    def _playback_thread_func(self, start_index=0):
        """Background thread for continuous playback"""
        if not self.current_queue or start_index >= len(self.current_queue):
            print("No tracks in queue to play.")
            return
        
        # Play the first track
        current_index = start_index
        self.play_music(self.current_queue[current_index]['uri'])
        
        # Check periodically if the track has finished
        while not self.stop_playback_thread:
            time.sleep(3)  # Check every 3 seconds
            
            try:
                current_playback = self.spotify.current_user_playing_track()
                
                # If nothing is playing or track finished
                if current_playback is None or not current_playback['is_playing']:
                    # Move to next track if available
                    current_index += 1
                    if current_index < len(self.current_queue):
                        track = self.current_queue[current_index]
                        print(f"\nAutomatic playback: {track['name']} by {track['artist']}")
                        self.play_music(track['uri'])
                    else:
                        print("\nReached end of queue. Getting more recommendations...")
                        # Get more recommendations and add to queue
                        more_tracks = self.get_recommendations_by_features(self.current_emotion, limit=10)
                        
                        # Filter out tracks already in queue
                        existing_ids = [track['id'] for track in self.current_queue]
                        more_tracks = [track for track in more_tracks if track['id'] not in existing_ids]
                        
                        if more_tracks:
                            self.current_queue.extend(more_tracks)
                            track = self.current_queue[current_index]
                            print(f"\nPlaying: {track['name']} by {track['artist']}")
                            self.play_music(track['uri'])
                        else:
                            print("No more recommendations available.")
                            break
            except Exception as e:
                print(f"Playback monitoring error: {str(e)}")
                time.sleep(5)  # Wait a bit longer if there was an error
        
        print("Continuous playback stopped.")
        self.continuous_playback = False

    def rate_current_track(self, liked):
        """Rate the currently playing track"""
        if self.current_track and self.current_emotion:
            self.preferences.record_feedback(
                self.current_track['id'], 
                liked, 
                self.current_emotion,
                self.current_track.get('features')
            )
            
            # If artist info available, update artist preference
            if 'artists' in self.current_track and self.current_track['artists']:
                artist_id = self.current_track['artists'][0]['id']
                self.preferences.update_artist_preference(self.current_emotion, artist_id, liked)
                
            feedback = "liked" if liked else "disliked"
            print(f"You {feedback} '{self.current_track['name']}' - Your preferences have been updated")
            return True
        else:
            print("No track is currently playing")
            return False

    def toggle_continuous_playback(self):
        """Toggle continuous playback on/off"""
        if self.continuous_playback:
            # Stop continuous playback
            self.stop_playback_thread = True
            print("Stopping continuous playback...")
        else:
            # Start continuous playback from current track
            try:
                current = self.spotify.current_user_playing_track()
                if current and current['item']:
                    # Find current track in queue
                    current_id = current['item']['id']
                    for i, track in enumerate(self.current_queue):
                        if track['id'] == current_id:
                            self.play_music_continuous(i)
                            break
                    else:
                        # Current track not in queue, start from beginning
                        self.play_music_continuous(0)
                else:
                    # Nothing playing, start from beginning
                    self.play_music_continuous(0)
            except:
                # Error checking current track, start from beginning
                self.play_music_continuous(0)

    def control_playback(self, command):
        """Control music playback"""
        try:
            if command == 'pause':
                self.spotify.pause_playback()
            elif command == 'resume':
                self.spotify.start_playback()
            elif command == 'next':
                self.spotify.next_track()
                # Update current track after skipping
                time.sleep(1)  # Wait for API to update
                current = self.spotify.current_user_playing_track()
                if current and current['item']:
                    self.current_track = {
                        'id': current['item']['id'],
                        'name': current['item']['name'],
                        'artist': current['item']['artists'][0]['name'],
                        'uri': current['item']['uri'],
                        'features': self.get_track_audio_features(current['item']['id'])
                    }
            elif command == 'previous':
                self.spotify.previous_track()
                # Update current track after going back
                time.sleep(1)  # Wait for API to update
                current = self.spotify.current_user_playing_track()
                if current and current['item']:
                    self.current_track = {
                        'id': current['item']['id'],
                        'name': current['item']['name'],
                        'artist': current['item']['artists'][0]['name'],
                        'uri': current['item']['uri'],
                        'features': self.get_track_audio_features(current['item']['id'])
                    }
            elif command.startswith('like'):
                self.rate_current_track(True)
            elif command.startswith('dislike'):
                self.rate_current_track(False)
            elif command == 'continuous':
                self.toggle_continuous_playback()
            elif command == 'save_playlist':
                if self.current_queue:
                    url = self.create_playlist(self.current_queue, self.current_emotion)
                    if url:
                        print(f"Playlist saved: {url}")
                    else:
                        print("Failed to create playlist")
                else:
                    print("No tracks in queue to save")
            return True
        except Exception as e:
            print(f"Playback control error: {str(e)}")
            return False

def main():
    # Create .env file with your Spotify API credentials
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write("""SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback""")
        print("Please add your Spotify API credentials to the .env file")
        return

    # Get user ID
    user_id = input("Enter your user ID (or press Enter for default): ") or "default_user"

    # Initialize MellowMind
    try:
        app = MellowMind(user_id)
        print(f"\nWelcome to MellowMind, {user_id}!")
    except Exception as e:
        print(f"Error initializing MellowMind: {str(e)}")
        return

    print("Tell me how you're feeling, and I'll play music that matches your mood.")
    print("Available commands:")
    print("  'play' - play selected track")
    print("  'pause/resume' - control playback")
    print("  'next/previous' - navigate tracks")
    print("  'like/dislike' - provide feedback")
    print("  'continuous' - toggle continuous playback")
    print("  'save_playlist' - save current queue as a Spotify playlist")
    print("  'quit' - exit the application")

    while True:
        try:
            user_input = input("\nHow are you feeling? (or enter a command): ").lower()
            
            if user_input == 'quit':
                # Stop continuous playback before quitting
                app.stop_playback_thread = True
                break
                
            # Handle playback controls
            if user_input in ['pause', 'resume', 'next', 'previous', 'like', 'dislike', 
                              'continuous', 'save_playlist']:
                app.control_playback(user_input)
                continue
            
            # Process emotion and get recommendations
            emotion, features = app.analyze_text_emotion(user_input)
            app.current_emotion = emotion  # Save current emotion
            
            print(f"\nDetected Emotion: {emotion}")
            recommendations = app.get_recommendations_by_features(emotion, limit=20)
            
            if not recommendations:
                print("\nCouldn't find recommendations. Try another description of your mood.")
                continue
                
            # Store recommendations in queue for continuous playback
            app.current_queue = recommendations
            
            print("\nRecommended Songs:")
            for i, song in enumerate(recommendations[:10], 1):  # Show first 10
                print(f"{i}. {song['name']} by {song['artist']}")
            
            print("\nOptions:")
            print("1. Play a specific song from the list")
            print("2. Start continuous playback")
            print("3. Save as a playlist")
            choice = input("Enter your choice (1-3): ")
            
            if choice == '1':
                # Play specific track
                track_num = input("Enter song number to play: ")
                if track_num.isdigit() and 1 <= int(track_num) <= len(recommendations[:10]):
                    song = recommendations[int(track_num)-1]
                    app.play_music(song['uri'])
                    
                    # Ask about continuous playback
                    cont = input("\nStart continuous playback after this song? (y/n): ").lower()
                    if cont.startswith('y'):
                        app.play_music_continuous(int(track_num)-1)
            
            elif choice == '2':
                # Start continuous playback from beginning
                app.play_music_continuous(0)
                
            elif choice
