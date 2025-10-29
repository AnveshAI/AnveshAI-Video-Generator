import os
import asyncio
import aiohttp
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from moviepy import ImageSequenceClip, concatenate_videoclips
from PIL import Image
from urllib.parse import quote_plus
import shutil
import random
import time
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'anvesh-ai-video-generator-secret')

FRAMES_DIR = 'frames'
VIDEOS_DIR = 'static/videos'
METADATA_FILE = 'video_metadata.json'
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')

if not ADMIN_PASSWORD:
    print("WARNING: ADMIN_PASSWORD environment variable is not set. Admin panel will be inaccessible.")
    print("Please set the ADMIN_PASSWORD secret in Replit Secrets to enable admin access.")

os.makedirs(FRAMES_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)

def load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return {'videos': [], 'total_generated': 0}

def save_metadata(metadata):
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)

async def generate_image_async(session, prompt, seed, index, max_retries=5):
    encoded_prompt = quote_plus(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={seed}&width=1920&height=1080&nologo=true"
    
    for attempt in range(max_retries):
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    frame_path = os.path.join(FRAMES_DIR, f"frame_{index:03d}.png")
                    with open(frame_path, 'wb') as f:
                        f.write(image_data)
                    print(f"✓ Generated frame {index + 1}")
                    return frame_path
                elif response.status == 429:
                    wait_time = (attempt + 1) * 5
                    print(f"Rate limited on frame {index + 1}, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"Failed to generate frame {index + 1}: {response.status}")
                    await asyncio.sleep(3)
        except Exception as e:
            print(f"Error generating frame {index + 1} (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(3)
    
    print(f"✗ Failed to generate frame {index + 1} after {max_retries} attempts")
    return None

async def generate_frames(prompt, num_frames=15):
    base_seed = random.randint(1, 1000000)
    frame_paths = []
    
    print(f"Starting generation of {num_frames} frames...")
    
    async with aiohttp.ClientSession() as session:
        # Generate frames sequentially to avoid rate limiting
        for i in range(num_frames):
            seed = base_seed + i
            variation_prompt = f"{prompt}, cinematic scene {i+1}"
            frame_path = await generate_image_async(session, variation_prompt, seed, i)
            frame_paths.append(frame_path)
            
            # Add delay between frames to avoid rate limiting
            if i < num_frames - 1:
                await asyncio.sleep(2)
    
    successful_frames = [path for path in frame_paths if path is not None]
    print(f"\n{'='*50}")
    print(f"Generation complete: {len(successful_frames)}/{num_frames} frames successful")
    print(f"{'='*50}\n")
    
    return successful_frames

def create_video(frame_paths, output_filename, fps=24):
    try:
        for frame_path in frame_paths:
            img = Image.open(frame_path)
            img = img.resize((1920, 1080), Image.Resampling.LANCZOS)
            img.save(frame_path)
        
        clip = ImageSequenceClip(frame_paths, fps=fps)
        
        duration = len(frame_paths) / fps
        
        if duration < 4:
            num_loops = int(4 / duration) + 1
            clip = concatenate_videoclips([clip] * num_loops)
            clip = clip.subclipped(0, 4)
        elif duration > 6:
            clip = clip.subclipped(0, 6)
        
        output_path = os.path.join(VIDEOS_DIR, output_filename)
        clip.write_videofile(output_path, fps=fps, codec='libx264', 
                            audio=False, preset='medium', 
                            bitrate='8000k', logger=None)
        
        clip.close()
        return output_path
    except Exception as e:
        print(f"Error creating video: {e}")
        raise

def cleanup_frames():
    if os.path.exists(FRAMES_DIR):
        for file in os.listdir(FRAMES_DIR):
            file_path = os.path.join(FRAMES_DIR, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    metadata = load_metadata()
    return render_template('admin.html', 
                         videos=metadata['videos'], 
                         total_generated=metadata['total_generated'])

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if not ADMIN_PASSWORD:
            return jsonify({'success': False, 'error': 'Admin password not configured. Please set ADMIN_PASSWORD in Replit Secrets.'}), 500
        
        password = request.json.get('password')
        if password and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Invalid password'}), 401
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

@app.route('/admin/delete/<video_id>', methods=['DELETE'])
def delete_video(video_id):
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    metadata = load_metadata()
    video_to_delete = None
    
    for video in metadata['videos']:
        if video['id'] == video_id:
            video_to_delete = video
            break
    
    if video_to_delete:
        video_path = os.path.join(VIDEOS_DIR, video_to_delete['filename'])
        if os.path.exists(video_path):
            os.remove(video_path)
        
        metadata['videos'] = [v for v in metadata['videos'] if v['id'] != video_id]
        save_metadata(metadata)
        return jsonify({'success': True})
    
    return jsonify({'error': 'Video not found'}), 404

@app.route('/generate', methods=['POST'])
def generate_video():
    data = request.json
    prompt = data.get('prompt', '').strip()
    num_frames = data.get('num_frames', 15)
    
    if not prompt:
        return jsonify({'error': 'Prompt is required'}), 400
    
    if num_frames < 10 or num_frames > 20:
        num_frames = 15
    
    try:
        cleanup_frames()
        
        frame_paths = asyncio.run(generate_frames(prompt, num_frames))
        
        if not frame_paths:
            return jsonify({'error': 'Failed to generate frames'}), 500
        
        timestamp = int(time.time())
        output_filename = f'anvesh_video_{timestamp}.mp4'
        
        video_path = create_video(frame_paths, output_filename)
        
        cleanup_frames()
        
        metadata = load_metadata()
        video_id = f'vid_{timestamp}_{random.randint(1000, 9999)}'
        
        video_info = {
            'id': video_id,
            'filename': output_filename,
            'prompt': prompt,
            'num_frames': len(frame_paths),
            'created_at': datetime.now().isoformat(),
            'file_size': os.path.getsize(video_path)
        }
        
        metadata['videos'].insert(0, video_info)
        metadata['total_generated'] += 1
        save_metadata(metadata)
        
        return jsonify({
            'success': True,
            'video_url': f'/static/videos/{output_filename}',
            'download_url': f'/download/{output_filename}',
            'frames_generated': len(frame_paths)
        })
    
    except Exception as e:
        cleanup_frames()
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_video(filename):
    video_path = os.path.join(VIDEOS_DIR, filename)
    if os.path.exists(video_path):
        return send_file(video_path, as_attachment=True, download_name='anvesh_video.mp4')
    return "Video not found", 404

@app.route('/stats')
def stats():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    metadata = load_metadata()
    total_size = sum(v['file_size'] for v in metadata['videos'])
    
    return jsonify({
        'total_videos': len(metadata['videos']),
        'total_generated': metadata['total_generated'],
        'total_storage_mb': round(total_size / (1024 * 1024), 2)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
