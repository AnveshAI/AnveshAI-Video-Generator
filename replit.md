# AnveshAI Video Generator

## Overview
AnveshAI is an AI-powered video generator that transforms text prompts into cinematic videos using Pollinations.ai for image generation and MoviePy for video rendering.

## Project Architecture

### Technology Stack
- **Backend**: Flask (Python 3.11)
- **Image Generation**: Pollinations.ai API
- **Video Processing**: MoviePy
- **Frontend**: HTML, Tailwind CSS, Vanilla JavaScript
- **Session Management**: Flask sessions with SESSION_SECRET

### Directory Structure
```
/
├── app.py                  # Main Flask application
├── templates/              # HTML templates
│   ├── index.html         # Main video generation UI
│   ├── admin_login.html   # Admin authentication
│   └── admin.html         # Admin panel for video management
├── static/
│   └── videos/            # Generated videos storage
├── frames/                # Temporary frame storage (auto-cleanup)
└── video_metadata.json    # Video metadata and usage tracking
```

### Key Features
1. **Text-to-Video Generation**: Converts text prompts into 4-6 second videos
2. **Async Image Generation**: Uses aiohttp to generate 10-20 frames concurrently
3. **High Quality**: 1080p resolution at 24fps
4. **Admin Panel**: View, manage, and delete generated videos
5. **Usage Tracking**: Monitor total generations and storage usage
6. **Auto Cleanup**: Temporary frames deleted after video creation

### API Endpoints
- `GET /` - Main video generation interface
- `POST /generate` - Generate video from prompt
- `GET /download/<filename>` - Download generated video
- `GET /admin` - Admin panel (requires authentication)
- `POST /admin/login` - Admin authentication
- `DELETE /admin/delete/<video_id>` - Delete video
- `GET /stats` - Usage statistics

### Admin Access
- Password stored securely in `ADMIN_PASSWORD` environment secret
- Access via `/admin/login`
- Configure ADMIN_PASSWORD in Replit Secrets to enable admin panel

## Recent Changes
- **2025-10-27**: Initial project setup and security fixes
  - Created Flask backend with async image generation using aiohttp
  - Implemented MoviePy video rendering (1080p, 24fps, 4-6 seconds)
  - Built cinematic UI with Tailwind CSS gradient design
  - Added admin panel with video gallery, delete, and usage tracking
  - Configured automatic temp file cleanup after video generation
  - Fixed MoviePy v2.x compatibility:
    - Updated imports (removed .editor module)
    - Replaced .loop() with concatenate_videoclips for duration extension
    - Updated .subclip() to .subclipped() for v2.x API
  - Added URL encoding for Pollinations.ai prompts (handles spaces/special chars)
  - Secured admin panel with ADMIN_PASSWORD environment variable
  - Added configuration validation and error messages for missing secrets

## Known Limitations
- Pollinations.ai may rate limit (HTTP 429) when generating many images rapidly
- The app gracefully handles this by continuing with successfully generated frames

## Configuration
- Server runs on `0.0.0.0:5000`
- Session secret from `SESSION_SECRET` environment variable
- Videos stored in `static/videos/`
- Temporary frames in `frames/` (auto-cleanup)

## User Preferences
None specified yet.
