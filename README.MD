<h1 align="center">AI Chatbot</h1>
<p align="center">
  <img src="media/Cover_Image.jpg" alt="Cover_Image" width="500">
</p>

<p>
Voice assistant capable of responding to complex prompts and satisfying music requests received through speech or remotely accessible web interface. Includes accessories such as verbal, textual, and tactile input options to manipulate device settings (volume, sleep, reboot, shutdown), conversation flow (resetting memory, verbal response termination), and music playback (pause, resume, previous, next).

The web interface was based on the MERN stack structure and includes features such as secure user authentication and login using password encryption and JWT access tokens, special interface options for admins (activating user accounts, deleting users, music playback control, voice assistant volume manipulation, song search suggestions), creating multiple conversation threads, and full-screen conversation mode. Both the frontend and backend were hosted on EC2 instances, request routing was handled using Route 53, and access over HTTPS was enabled by Caddy.
</p>

## Requirements:
* Voice Assistant
  * RPi 4B
  * 3 tactile buttons
  * 1 WS2812 LED ring
  * Speaker HAT
  * Custom 3D printed case
* Web Interface
  * 2 EC2 instances (kept crashing with one due to limited specs with free tier)
  * 1 Route 53 hosted zone (routes for frontend and backend EC2 instances)

## Demo:
* Username: DEMO
* Password: DEMO
* Demo users can't edit their profile for obvious reasons, but you can still test out the conversation features
* <a href="https://github.com/MattHua04/AI_Chatbot_Frontend">Frontend Repo</a>
* <a href="https://github.com/MattHua04/AI_Chatbot_Backend">Backend Repo</a>
<p align="center">
  <a href="https://ai-chatbot.hbypjt.com">
    <img src="media/Dashboard.jpg" alt="AI Chatbot" width="100%">
  </a>
</p>

<h2 align="center">Listening for user prompt</h2>
<p align="center">
  <img src="media/Listening.jpg" alt="Listening" width="400">
</p>

<h2 align="center">Volume level visualization</h2>
<p align="center">
  <img src="media/Volume.jpg" alt="Volume" width="400">
</p>

<h2 align="center">Sleep mode</h2>
<p align="center">
  <img src="media/Sleep.jpg" alt="Sleep" width="400">
</p>
