import os
import shutil
import sys
import subprocess
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def check_ffmpeg():
    """Verify FFmpeg is installed and NVIDIA GPU is available."""
    try:
        # Check FFmpeg installation
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        
        # Check NVIDIA GPU availability
        result = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True)
        if 'h264_nvenc' not in result.stdout:
            raise RuntimeError("NVIDIA GPU encoder not available")
        
    except subprocess.CalledProcessError:
        logging.error("FFmpeg is not installed or accessible")
        sys.exit(1)
    except RuntimeError as e:
        logging.error(str(e))
        sys.exit(1)

def check_disk_space(directory, required_space):
    """Check if there's enough disk space available."""
    try:
        total, used, free = shutil.disk_usage(directory)
        if free < required_space:
            raise RuntimeError(f"Insufficient disk space. Need {required_space/1e9:.2f}GB, "
                             f"but only {free/1e9:.2f}GB available")
    except Exception as e:
        logging.error(f"Error checking disk space: {str(e)}")
        sys.exit(1)

def split_video(input_file, output_dir):
    """Split video into chunks smaller than 8GB using FFmpeg."""
    try:
        file_size = os.path.getsize(input_file)
        if file_size <= 8589934592/2:  # 8GB in bytes
            logging.info(f"File {input_file} is already under 8GB. Skipping.")
            return

        filename = Path(input_file).stem
        extension = Path(input_file).suffix
        output_pattern = os.path.join(output_dir, f"{filename}_part%03d{extension}")

        # Calculate segment size to ensure each part is under 8GB
        # Using 7.5GB to provide some safety margin
        segment_size = 4 * 1024 * 1024 * 1024  # 7.5GB in bytes
        segment_duration = (segment_size / file_size) * get_video_duration(input_file)

        cmd = [
            'ffmpeg', '-i', input_file,
            '-c', 'copy',  # Copy both video and audio streams without re-encoding
            '-f', 'segment',
            '-segment_time', str(int(segment_duration)),
            '-reset_timestamps', '1',
            output_pattern
        ]

        logging.info(f"Starting to split: {input_file}")
        subprocess.run(cmd, check=True)
        logging.info(f"Successfully split: {input_file}")

    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg error while processing {input_file}: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error processing {input_file}: {str(e)}")
        sys.exit(1)

def get_video_duration(input_file):
    """Get video duration in seconds using FFprobe."""
    try:
        cmd = [
            'ffprobe', 
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            input_file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout)
    except (subprocess.CalledProcessError, ValueError) as e:
        logging.error(f"Error getting video duration: {str(e)}")
        sys.exit(1)

def process_directory(directory):
    """Process all video files in the directory."""
    try:
        # Create split directory
        split_dir = os.path.join(directory, 'split')
        os.makedirs(split_dir, exist_ok=True)

        # Get list of video files
        video_files = []
        for ext in ['.mp4', '.mov']:
            video_files.extend(Path(directory).glob(f'*{ext}'))

        if not video_files:
            logging.warning("No video files found in the directory")
            return

        # Process each video file
        for video_file in video_files:
            # Check disk space (estimate 2x file size needed)
            check_disk_space(split_dir, os.path.getsize(video_file) * 2)
            split_video(str(video_file), split_dir)

    except PermissionError:
        logging.error(f"Permission denied accessing directory: {directory}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error processing directory: {str(e)}")
        sys.exit(1)

def get_directory():
    while True:
        directory = input("Please enter the directory path: ").strip()
        
        # Check if the directory exists
        if os.path.isdir(directory):
            return directory
        else:
            print("Invalid directory path. Please try again.")

if __name__ == "__main__":
    # Verify FFmpeg and GPU availability
    check_ffmpeg()
    
    # Get and validate directory
    directory_path = get_directory()
    
    # Process videos
    logging.info(f"Starting video processing in: {directory_path}")
    process_directory(directory_path)
    logging.info("Processing complete")