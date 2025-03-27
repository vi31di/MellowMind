import React, { useState, useEffect } from 'react';
import { 
  Music, 
  Play, 
  Pause, 
  SkipForward, 
  SkipBack, 
  Heart, 
  ThumbsDown, 
  List, 
  Smile, 
  Frown, 
  Meh, 
  Mic 
} from 'lucide-react';

// Mock Spotify API integration (would replace with actual backend calls)
const useSpotifyAPI = () => {
  const [currentTrack, setCurrentTrack] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [recommendations, setRecommendations] = useState([]);
  const [emotion, setEmotion] = useState(null);

  const analyzeMood = async (moodText) => {
    // Simulate mood analysis
    const emotions = {
      'happy': { color: 'bg-yellow-100', icon: <Smile className="text-yellow-500" /> },
      'sad': { color: 'bg-blue-100', icon: <Frown className="text-blue-500" /> },
      'neutral': { color: 'bg-gray-100', icon: <Meh className="text-gray-500" /> },
      'anxious': { color: 'bg-purple-100', icon: <Frown className="text-purple-500" /> },
      'angry': { color: 'bg-red-100', icon: <Frown className="text-red-500" /> }
    };

    const detectedEmotion = Object.keys(emotions)[
      Math.floor(Math.random() * Object.keys(emotions).length)
    ];

    setEmotion({
      type: detectedEmotion,
      ...emotions[detectedEmotion]
    });

    // Simulate getting recommendations
    const mockRecommendations = [
      { id: '1', name: 'Calm Waters', artist: 'Ocean Waves', duration: '3:45' },
      { id: '2', name: 'Peaceful Morning', artist: 'Sunrise Melody', duration: '4:12' },
      { id: '3', name: 'Tranquil Thoughts', artist: 'Zen Sounds', duration: '3:30' }
    ];

    setRecommendations(mockRecommendations);

    return detectedEmotion;
  };

  const playTrack = (track) => {
    setCurrentTrack(track);
    setIsPlaying(true);
  };

  const controls = {
    play: () => setIsPlaying(true),
    pause: () => setIsPlaying(false),
    next: () => {
      const currentIndex = recommendations.findIndex(r => r.id === currentTrack.id);
      const nextTrack = recommendations[(currentIndex + 1) % recommendations.length];
      playTrack(nextTrack);
    },
    previous: () => {
      const currentIndex = recommendations.findIndex(r => r.id === currentTrack.id);
      const prevTrack = recommendations[(currentIndex - 1 + recommendations.length) % recommendations.length];
      playTrack(prevTrack);
    }
  };

  return { 
    currentTrack, 
    isPlaying, 
    recommendations, 
    emotion, 
    analyzeMood, 
    playTrack,
    controls 
  };
};

const MellowMindApp = () => {
  const [moodInput, setMoodInput] = useState('');
  const { 
    currentTrack, 
    isPlaying, 
    recommendations, 
    emotion, 
    analyzeMood, 
    playTrack,
    controls 
  } = useSpotifyAPI();

  const handleMoodSubmit = async (e) => {
    e.preventDefault();
    await analyzeMood(moodInput);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-100 flex flex-col">
      {/* Header */}
      <header className="p-4 flex justify-between items-center bg-white/70 backdrop-blur-md shadow-sm">
        <div className="flex items-center space-x-2">
          <Music className="text-purple-600" />
          <h1 className="text-xl font-bold text-purple-800">MellowMind</h1>
        </div>
        <nav className="flex space-x-4">
          <button className="text-purple-600 hover:text-purple-800">Home</button>
          <button className="text-purple-600 hover:text-purple-800">Playlists</button>
          <button className="text-purple-600 hover:text-purple-800">Profile</button>
        </nav>
      </header>

      {/* Mood Input Section */}
      <div className="flex-grow container mx-auto px-4 py-8 flex flex-col justify-center items-center">
        <form 
          onSubmit={handleMoodSubmit} 
          className="w-full max-w-xl bg-white rounded-xl shadow-lg p-6"
        >
          <div className="flex items-center border-b border-purple-200 py-2">
            <Mic className="text-purple-500 mr-3" />
            <input 
              type="text" 
              value={moodInput}
              onChange={(e) => setMoodInput(e.target.value)}
              placeholder="Describe how you're feeling..."
              className="w-full text-lg text-purple-800 placeholder-purple-300 focus:outline-none"
            />
            <button 
              type="submit" 
              className="bg-purple-500 text-white px-4 py-2 rounded-full hover:bg-purple-600 transition"
            >
              Analyze Mood
            </button>
          </div>
        </form>

        {/* Emotion Display */}
        {emotion && (
          <div className={`mt-6 ${emotion.color} p-4 rounded-xl flex items-center space-x-4 shadow-md`}>
            {emotion.icon}
            <span className="text-lg font-semibold capitalize">
              {emotion.type} Mood Detected
            </span>
          </div>
        )}

        {/* Recommendations */}
        {recommendations.length > 0 && (
          <div className="mt-8 w-full max-w-xl">
            <h2 className="text-xl font-bold text-purple-800 mb-4">Recommended Tracks</h2>
            <div className="space-y-3">
              {recommendations.map((track) => (
                <div 
                  key={track.id} 
                  className={`
                    flex items-center justify-between 
                    bg-white rounded-lg p-4 shadow-md 
                    hover:shadow-xl transition
                    ${currentTrack?.id === track.id ? 'ring-2 ring-purple-500' : ''}
                  `}
                >
                  <div className="flex items-center space-x-4">
                    <button 
                      onClick={() => playTrack(track)}
                      className="text-purple-600 hover:text-purple-800"
                    >
                      <Play />
                    </button>
                    <div>
                      <h3 className="font-semibold text-purple-800">{track.name}</h3>
                      <p className="text-sm text-purple-500">{track.artist}</p>
                    </div>
                  </div>
                  <span className="text-purple-400">{track.duration}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Player Controls */}
      {currentTrack && (
        <div className="fixed bottom-0 left-0 right-0 bg-white/90 backdrop-blur-md shadow-2xl p-4">
          <div className="container mx-auto flex justify-between items-center">
            {/* Current Track Info */}
            <div className="flex items-center space-x-4">
              <div className="bg-purple-100 p-2 rounded-full">
                <Music className="text-purple-600" />
              </div>
              <div>
                <h3 className="font-semibold text-purple-800">{currentTrack.name}</h3>
                <p className="text-sm text-purple-500">{currentTrack.artist}</p>
              </div>
            </div>

            {/* Playback Controls */}
            <div className="flex items-center space-x-6">
              <button 
                onClick={controls.previous} 
                className="text-purple-600 hover:text-purple-800"
              >
                <SkipBack />
              </button>
              {isPlaying ? (
                <button 
                  onClick={controls.pause} 
                  className="bg-purple-500 text-white p-3 rounded-full hover:bg-purple-600"
                >
                  <Pause />
                </button>
              ) : (
                <button 
                  onClick={controls.play} 
                  className="bg-purple-500 text-white p-3 rounded-full hover:bg-purple-600"
                >
                  <Play />
                </button>
              )}
              <button 
                onClick={controls.next} 
                className="text-purple-600 hover:text-purple-800"
              >
                <SkipForward />
              </button>
            </div>

            {/* Feedback Controls */}
            <div className="flex items-center space-x-4">
              <button className="text-green-500 hover:text-green-600">
                <Heart />
              </button>
              <button className="text-red-500 hover:text-red-600">
                <ThumbsDown />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MellowMindApp;
