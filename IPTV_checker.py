import requests
import argparse
import signal
import os
import sys
import time
import subprocess
import logging
import shutil

def print_header():
    header_text = """
\033[96m██╗██████╗ ████████╗██╗   ██╗     ██████╗██╗  ██╗███████╗ ██████╗██╗  ██╗███████╗██████╗   
██║██╔══██╗╚══██╔══╝██║   ██║    ██╔════╝██║  ██║██╔════╝██╔════╝██║ ██╔╝██╔════╝██╔══██╗  
██║██████╔╝   ██║   ██║   ██║    ██║     ███████║█████╗  ██║     █████╔╝ █████╗  ██████╔╝  
██║██╔═══╝    ██║   ╚██╗ ██╔╝    ██║     ██╔══██║██╔══╝  ██║     ██╔═██╗ ██╔══╝  ██╔══██╗  
██║██║        ██║    ╚████╔╝     ╚██████╗██║  ██║███████╗╚██████╗██║  ██╗███████╗██║  ██║  
╚═╝╚═╝        ╚═╝     ╚═══╝       ╚═════╝╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝  
\033[0m    
""" 
    print(header_text)
    print("\033[93mWelcome to the IPTV Stream Checker!\n\033[0m")
    print("\033[93mUse -h for help on how to use this tool.\033[0m")

def setup_logging(verbose_level):
    if verbose_level == 1:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    elif verbose_level >= 2:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(level=logging.CRITICAL)  # Only critical errors will be logged by default.

def handle_sigint(signum, frame):
    logging.info("Interrupt received, stopping...")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_sigint)

def check_channel_status(url, timeout, retries=6, extended_timeout=None):
    headers = {
        'User-Agent': 'IPTVChecker 1.0'
    }
    min_data_threshold = 1024 * 500  # 500KB minimum threshold
    initial_timeout = 5
    max_timeout = timeout

    def attempt_check(current_timeout):
        accumulated_data = 0
        stable_connection = True
        for attempt in range(retries):
            try:
                with requests.get(url, stream=True, timeout=(initial_timeout, current_timeout), headers=headers) as resp:
                    if resp.status_code == 429:
                        logging.debug(f"Rate limit exceeded, retrying...")
                        time.sleep(2)
                        continue
                    elif resp.status_code == 200:
                        content_type = resp.headers.get('Content-Type', '')
                        logging.debug(f"Content-Type: {content_type}")

                        if 'video/mp2t' in content_type or '.ts' in url or 'application/vnd.apple.mpegurl' in content_type:
                            for chunk in resp.iter_content(1024 * 1024):  # 1MB chunks
                                if not chunk:
                                    stable_connection = False
                                    break

                                accumulated_data += len(chunk)
                                if accumulated_data >= min_data_threshold:
                                    logging.debug(f"Data received: {accumulated_data} bytes")
                                    return 'Alive'

                            logging.debug(f"Data received: {accumulated_data} bytes")
                            if not stable_connection:
                                logging.debug("Unstable connection detected")
                                return 'Dead'
                        else:
                            logging.debug(f"Content-Type not recognized as stream: {content_type}")
                            return 'Dead'
                    else:
                        logging.debug(f"HTTP status code not OK: {resp.status_code}")
                        return 'Dead'
            except requests.ConnectionError:
                logging.error("Connection error occurred")
                return 'Dead'
            except requests.Timeout:
                logging.error("Timeout occurred")
                return 'Dead'
            except requests.RequestException as e:
                logging.error(f"Request failed: {str(e)}")
                return 'Dead'

        logging.error("Maximum retries exceeded for checking channel status")
        return 'Dead'

    # First attempt with the initial timeout
    status = attempt_check(timeout)

    # If the channel is detected as dead and extended_timeout is specified, retry with extended timeout
    if status == 'Dead' and extended_timeout:
        logging.info(f"Channel initially detected as dead. Retrying with an extended timeout of {extended_timeout} seconds.")
        status = attempt_check(extended_timeout)

    # Final Verification using ffmpeg/ffprobe for streams marked alive
    if status == 'Alive':
        try:
            command = [
                'ffmpeg', '-i', url, '-t', '5', '-f', 'null', '-'
            ]
            ffmpeg_result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
            if ffmpeg_result.returncode != 0:
                logging.debug(f"ffmpeg failed to read stream; marking as dead")
                status = 'Dead'
        except subprocess.TimeoutExpired:
            logging.error(f"Timeout when trying to verify stream with ffmpeg for {url}")
            status = 'Dead'

    return status


def capture_frame(url, output_path, file_name):
    command = [
        'ffmpeg', '-y', '-i', url, '-ss', '00:00:02', '-frames:v', '1',
        os.path.join(output_path, f"{file_name}.png")
    ]
    try:
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        logging.debug(f"Screenshot saved for {file_name}")
        return True
    except subprocess.TimeoutExpired:
        logging.error(f"Timeout when trying to capture frame for {file_name}")
        return False


def get_stream_info(url):
    command = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 
        'stream=codec_name,width,height,r_frame_rate', '-of', 'default=noprint_wrappers=1', url
    ]
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        output = result.stdout.decode()
        codec_name = None
        width = height = None
        fps = None
        for line in output.splitlines():
            if line.startswith("codec_name="):
                codec_name = line.split('=')[1].upper()
            elif line.startswith("width="):
                width = int(line.split('=')[1])
            elif line.startswith("height="):
                height = int(line.split('=')[1])
            elif line.startswith("r_frame_rate="):
                fps_data = line.split('=')[1]
                if fps_data and '/' in fps_data:
                    numerator, denominator = map(int, fps_data.split('/'))
                    fps = round(numerator / denominator)

        # Determine resolution string with FPS
        resolution = "Unknown"
        if width and height:
            if width >= 3840 and height >= 2160:
                resolution = "4K"
            elif width >= 1920 and height >= 1080:
                resolution = "1080p"
            elif width >= 1280 and height >= 720:
                resolution = "720p"
            else:
                resolution = "SD"

        resolution_fps = f"{resolution}{fps}" if resolution != "Unknown" and fps else resolution

        return f"{resolution_fps} {codec_name}" if codec_name and resolution_fps else "Unknown", resolution, fps
    except subprocess.TimeoutExpired:
        logging.error(f"Timeout when trying to get stream info for {url}")
        return "Unknown", "Unknown", None

def get_audio_bitrate(url):
    command = [
        'ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries',
        'stream=codec_name,bit_rate', '-of', 'default=noprint_wrappers=1', url
    ]
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        output = result.stdout.decode()
        audio_bitrate = None
        codec_name = None
        for line in output.splitlines():
            if line.startswith("bit_rate="):
                bitrate_value = line.split('=')[1]
                if bitrate_value.isdigit():
                    audio_bitrate = int(bitrate_value) // 1000  # Convert to kbps
                else:
                    audio_bitrate = 'N/A'
            elif line.startswith("codec_name="):
                codec_name = line.split('=')[1].upper()

        return f"{audio_bitrate} kbps {codec_name}" if codec_name and audio_bitrate else "Unknown"
    except subprocess.TimeoutExpired:
        logging.error(f"Timeout when trying to get audio bitrate for {url}")
        return "Unknown"

def check_label_mismatch(channel_name, resolution):
    channel_name_lower = channel_name.lower()

    mismatches = []

    # Compare resolution ignoring the framerate part
    if "4k" in channel_name_lower or "uhd" in channel_name_lower:
        if resolution != "4K":
            mismatches.append(f"\033[91mExpected 4K, got {resolution}\033[0m")
    elif "1080p" in channel_name_lower or "fhd" in channel_name_lower:
        if resolution != "1080p":
            mismatches.append(f"\033[91mExpected 1080p, got {resolution}\033[0m")
    elif "hd" in channel_name_lower:
        if resolution not in ["1080p", "720p"]:
            mismatches.append(f"\033[91mExpected 720p or 1080p, got {resolution}\033[0m")
    elif resolution == "4K":
        mismatches.append(f"\033[91m4K channel not labeled as such\033[0m")

    return mismatches

def load_processed_channels(log_file):
    processed_channels = set()
    last_index = 0
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            for line in f:
                parts = line.strip().split(' - ')
                if len(parts) > 1:
                    index_part = parts[0].split()[0]
                    if index_part.isdigit():
                        last_index = max(last_index, int(index_part))
                    processed_channels.add(parts[1])
    return processed_channels, last_index

def write_log_entry(log_file, entry):
    with open(log_file, 'a') as f:
        f.write(entry + "\n")

def console_log_entry(current_channel, total_channels, channel_name, status, video_info, audio_info, max_name_length, use_padding):
    color = "\033[92m" if status == 'Alive' else "\033[91m"
    status_symbol = '✓' if status == 'Alive' else '✕'
    if use_padding:
        name_padding = ' ' * (max_name_length - len(channel_name) + 3)  # +3 for additional spaces
    else:
        name_padding = ''
    if status == 'Alive':
        print(f"{color}{current_channel}/{total_channels} {status_symbol} {channel_name}{name_padding} | Video: {video_info} - Audio: {audio_info}\033[0m")
        logging.info(f"{current_channel}/{total_channels} {status_symbol} {channel_name}{name_padding} | Video: {video_info} - Audio: {audio_info}")
    else:
        if use_padding:
            # Include the | for dead links only when padding is added
            print(f"{color}{current_channel}/{total_channels} {status_symbol} {channel_name}{name_padding} |\033[0m")
            logging.info(f"{current_channel}/{total_channels} {status_symbol} {channel_name}{name_padding} |")
        else:
            print(f"{color}{current_channel}/{total_channels} {status_symbol} {channel_name}\033[0m")
            logging.info(f"{current_channel}/{total_channels} {status_symbol} {channel_name}")

def parse_m3u8_file(file_path, group_title, timeout, log_file, extended_timeout, split=False, rename=False):
    base_playlist_name = os.path.basename(file_path).split('.')[0]
    group_name = group_title.replace('|', '').replace(' ', '') if group_title else 'AllGroups'
    output_folder = f"{base_playlist_name}_{group_name}_screenshots"
    os.makedirs(output_folder, exist_ok=True)

    processed_channels, last_index = load_processed_channels(log_file)
    current_channel = last_index
    mislabeled_channels = []
    low_framerate_channels = []
    max_name_length = 0
    use_padding = True

    working_channels = []
    dead_channels = []

    # Get console width
    console_width = shutil.get_terminal_size((80, 20)).columns

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            total_channels = sum(1 for line in lines if line.startswith('#EXTINF') and (group_title in line if group_title else True))

            logging.info(f"Loading channels from {file_path} with group '{group_title}'...")
            logging.info(f"Total channels matching group '{group_title}': {total_channels}\n")

            # Calculate the maximum channel name length and check if the formatted line will fit in the console width
            for i in range(len(lines)):
                line = lines[i].strip()
                if line.startswith('#EXTINF') and (group_title in line if group_title else True):
                    if i + 1 < len(lines):
                        channel_name = line.split(',', 1)[1].strip() if ',' in line else "Unknown Channel"
                        max_name_length = max(max_name_length, len(channel_name))

            # Estimate if the line will fit in the console width
            max_line_length = max_name_length + len("1/5 ✓ | Video: 1080p50 H264 - Audio: 160 kbps AAC") + 3  # 3 for extra padding
            if max_line_length > console_width:
                use_padding = False

            renamed_lines = []
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith('#EXTINF') and (group_title in line if group_title else True):
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        channel_name = line.split(',', 1)[1].strip() if ',' in line else "Unknown Channel"
                        identifier = f"{channel_name} {next_line}"
                        if identifier not in processed_channels:
                            current_channel += 1
                            status = check_channel_status(next_line, timeout, extended_timeout=extended_timeout)
                            video_info = "Unknown"
                            audio_info = "Unknown"
                            fps = None
                            if status == 'Alive':
                                video_info, resolution, fps = get_stream_info(next_line)
                                audio_info = get_audio_bitrate(next_line)
                                mismatches = check_label_mismatch(channel_name, resolution)
                                if fps is not None and fps <= 30:
                                    low_framerate_channels.append(f"{current_channel}/{total_channels} {channel_name} - \033[91m{fps}fps\033[0m")
                                if mismatches:
                                    mislabeled_channels.append(f"{current_channel}/{total_channels} {channel_name} - \033[91m{', '.join(mismatches)}\033[0m")
                                file_name = f"{current_channel}-{channel_name.replace('/', '-')}"  # Replace '/' to avoid path issues
                                capture_frame(next_line, output_folder, file_name)
                                
                                if rename:
                                    # Create the new channel name in the desired format
                                    renamed_channel_name = f"{channel_name} ({resolution} {video_info.split()[-1]} | {audio_info})"
                                    extinf_parts = line.split(',', 1)
                                    if len(extinf_parts) > 1:
                                        extinf_parts[1] = renamed_channel_name
                                        line = ','.join(extinf_parts)

                                if split:
                                    working_channels.append((line, next_line))
                            else:
                                if split:
                                    dead_channels.append((line, next_line))
                            console_log_entry(current_channel, total_channels, channel_name, status, video_info, audio_info, max_name_length, use_padding)
                            processed_channels.add(identifier)

                        # Add the processed (renamed) line and the corresponding URL to the list
                        renamed_lines.append(line)
                        renamed_lines.append(next_line)
                        i += 1  # Skip the next line because it's already processed
                    else:
                        # If there's no URL following the EXTINF line, just add it
                        renamed_lines.append(line)
                else:
                    # If it's not an EXTINF line, just keep it as is
                    renamed_lines.append(line)
                i += 1

            if split:
                working_playlist_path = f"{base_playlist_name}_working.m3u8"
                dead_playlist_path = f"{base_playlist_name}_dead.m3u8"
                with open(working_playlist_path, 'w', encoding='utf-8') as working_file:
                    working_file.write("#EXTM3U\n")
                    for entry in working_channels:
                        working_file.write(entry[0] + "\n")
                        working_file.write(entry[1] + "\n")
                with open(dead_playlist_path, 'w', encoding='utf-8') as dead_file:
                    dead_file.write("#EXTM3U\n")
                    for entry in dead_channels:
                        dead_file.write(entry[0] + "\n")
                        dead_file.write(entry[1] + "\n")
                logging.info(f"Working channels playlist saved to {working_playlist_path}")
                logging.info(f"Dead channels playlist saved to {dead_playlist_path}")
            elif rename:  # Save the renamed playlist directly if split is not enabled
                renamed_playlist_path = f"{base_playlist_name}_renamed.m3u8"
                with open(renamed_playlist_path, 'w', encoding='utf-8') as renamed_file:
                    renamed_file.write("#EXTM3U\n")
                    for line in renamed_lines:
                        renamed_file.write(line + "\n")
                logging.info(f"Renamed playlist saved to {renamed_playlist_path}")

            if low_framerate_channels:
                print("\n\033[93mLow Framerate Channels:\033[0m")
                for entry in low_framerate_channels:
                    print(f"{entry}")
                logging.info("Low Framerate Channels Detected:")
                for entry in low_framerate_channels:
                    logging.info(entry)

            if mislabeled_channels:
                print("\n\033[93mMislabeled Channels:\033[0m")
                for entry in mislabeled_channels:
                    print(f"{entry}")
                logging.info("Mislabeled Channels Detected:")
                for entry in mislabeled_channels:
                    logging.info(entry)

    except FileNotFoundError:
        logging.error(f"File not found: {file_path}. Please check the path and try again.")
    except Exception as e:
        logging.error(f"An unexpected error occurred while processing the file: {str(e)}")


def main():
    print_header()

    parser = argparse.ArgumentParser(description="Check the status of channels in an IPTV M3U8 playlist and capture frames of live channels.")
    parser.add_argument("playlist", type=str, help="Path to the M3U8 playlist file")
    parser.add_argument("-group", "-g", type=str, default=None, help="Specific group title to check within the playlist")
    parser.add_argument("-timeout", "-t", type=float, default=10.0, help="Timeout in seconds for checking channel status")
    parser.add_argument("-v", action="count", default=0, help="Increase output verbosity (-v for info, -vv for debug)")
    parser.add_argument("-extended", "-e", type=int, nargs='?', const=10, default=None, help="Enable extended timeout check for dead channels. Default is 10 seconds if used without specifying time.")
    parser.add_argument("-split", "-s", action="store_true", help="Create separate playlists for working and dead channels")
    parser.add_argument("-rename", "-r", action="store_true", help="Rename alive channels to include video and audio info")

    args = parser.parse_args()

    # Set up logging based on verbosity level
    if args.v == 1:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    elif args.v >= 2:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(level=logging.CRITICAL)  # Only critical errors will be logged by default.

    group_name = args.group.replace('|', '').replace(' ', '') if args.group else 'AllGroups'
    log_file_name = f"{os.path.basename(args.playlist).split('.')[0]}_{group_name}_checklog.txt"

    parse_m3u8_file(args.playlist, args.group, args.timeout, log_file_name, extended_timeout=args.extended, split=args.split, rename=args.rename)

if __name__ == "__main__":
    main()
