# MellowMind App
An AI based application in which a chatbot initates a conversation(in any language) to analyse mood/
emotions of the user and plays song to enhance the mood.(Eg: it would play a feel good beat if person is sad, 
the ones favourited by person or played frequently are played first). Voice commands are also Supported.
It's like an AI powered smart music cum mental-wellbeing app.

## Features
+ Mood-based music recommendation and play
+ Emotion analysis using NLP
+ Personalized learning from user feedback
+ Spotify integration
+ All pLayback options, playlist creation, favourite option

## Installation
### Prequisites
+ Python 3.8+
+ Spotify Developer Account

### Backend Setup
1) Clone the repository
   
2) Create a virtual environment
bashCopypython -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

3) Install dependencies
bashCopypip install -r requirements.txt
python -m spacy download en_core_web_sm

4) Set up Spotify API Credentials

a) Go to Spotify Developer Dashboard
b) Create a new application
c) Copy Client ID and Client Secret
d) Rename .env.example to .env
e) Fill in your Spotify credentials

### Frontend Setup

1) Navigate to frontend directory
bash
Copycd frontend
npm install
npm start

### Running The App
1) Start backend
bash
Copypython mellow_mind.py

3) Start frontend
bash
Copynpm start

## Contributing
Pull requests are welcome. For major changes, please open an issue first.

## License
MIT


