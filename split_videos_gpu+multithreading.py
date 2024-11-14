import os
import subprocess
import shutil
from concurrent.futures import ThreadPoolExecutor

def get_video_files(directory):
    """Scans the directory for video files."""
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv']
    video_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(ext) for ext in video_extensions):
                video_files.append(os.path.join(root, file))
    return video_files

def split_video(file_path):
    """Splits the video into chunks of not more than 48GB and moves them to a subfolder."""
    try:
        file_size_gb = os.path.getsize(file_path) / (1024 ** 3)
        #max_chunk_size_gb = 48
        max_chunk_size_gb = 16
        if file_size_gb > max_chunk_size_gb:
            print(f"Splitting video: {file_path}")

            # Create subfolder 'split' in the video file's directory
            base_dir = os.path.dirname(file_path)
            split_dir = os.path.join(base_dir, 'split')
            os.makedirs(split_dir, exist_ok=True)

            # Get video duration
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
            duration = float(result.stdout)

            # Calculate number of chunks and duration of each chunk
            num_chunks = int(file_size_gb // max_chunk_size_gb) + 1
            chunk_duration = duration / num_chunks

            base_output_path = os.path.splitext(os.path.basename(file_path))[0]
            for i in range(num_chunks):
                start_time = i * chunk_duration
                output_filename = f"{base_output_path}_part{i+1}{os.path.splitext(file_path)[1]}"
                output_path = os.path.join(split_dir, output_filename)

                subprocess.run(
                    ["ffmpeg", "-hwaccel", "cuda", "-i", file_path, "-ss", str(start_time), "-t", str(chunk_duration),
                     "-c:v", "h264_nvenc", "-c:a", "copy", output_path]
                )


                print(f"Created chunk: {output_path}")
        else:
            print(f"Video {file_path} is less than 48GB, no splitting needed.")
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def main(directory):
    video_files = get_video_files(directory)
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        executor.map(split_video, video_files)

if __name__ == "__main__":
    directory = input("Enter the directory path to scan for videos: ")
    main(directory)
