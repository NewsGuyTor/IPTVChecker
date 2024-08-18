import requests
import argparse
import signal
import os
import sys
import time
import subprocess
import logging

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
    print("\033[92mUse -h for help on how to use this tool.\n\033[0m")

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

def check_channel_status(url, timeout, retries=6):
    delay = 2  # Initial delay in seconds
    for attempt in range(retries):
        try:
            with requests.get(url, stream=True, timeout=(5, timeout)) as resp:
                if resp.status_code == 429:
                    logging.debug(f"Rate limit exceeded, retrying in {delay} seconds...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                    continue
                elif resp.status_code == 200 and 'video/mp2t' in resp.headers.get('Content-Type', ''):
                    data_received = 0
                    for chunk in resp.iter_content(1024 * 1024):
                        data_received += len(chunk)
                        if data_received > 100 * 1024:
                            return 'Alive'
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

def capture_frame(url, output_path, file_name):
    command = [
        'ffmpeg', '-i', url, '-ss', '00:00:02', '-frames:v', '1',
        os.path.join(output_path, f"{file_name}.png")
    ]
    try:
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        logging.debug(f"Screenshot saved for {file_name}")
        return True
    except subprocess.TimeoutExpired:
        logging.error(f"Timeout when trying to capture frame for {file_name}")
        return False

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

def console_log_entry(current_channel, total_channels, channel_name, status, screen_shot):
    color = "\033[92m" if screen_shot else "\033[91m"
    screenshot_status = '✓' if screen_shot else '✕'
    status_symbol = '✓' if status == 'Alive' else '✕'
    print(f"{color}{current_channel}/{total_channels} {channel_name} - Alive: {status_symbol} - Screenshot: {screenshot_status}\033[0m")
    logging.info(f"{current_channel}/{total_channels} {channel_name} - Status: {status}, Screenshot: {screenshot_status}")

def parse_m3u8_file(file_path, group_title, timeout, log_file):
    base_playlist_name = os.path.basename(file_path).split('.')[0]
    group_name = group_title.replace('|', '').replace(' ', '') if group_title else 'AllGroups'
    output_folder = f"{base_playlist_name}_{group_name}_screenshots"
    os.makedirs(output_folder, exist_ok=True)

    processed_channels, last_index = load_processed_channels(log_file)
    current_channel = last_index

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            total_channels = sum(1 for line in lines if line.startswith('#EXTINF') and (group_title in line if group_title else True))

            logging.info(f"Loading channels from {file_path} with group '{group_title}'...")
            logging.info(f"Total channels matching group '{group_title}': {total_channels}\n")

            for i in range(len(lines)):
                line = lines[i].strip()
                if line.startswith('#EXTINF') and (group_title in line if group_title else True):
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        channel_name = line.split(',', 1)[1].strip() if ',' in line else "Unknown Channel"
                        identifier = f"{channel_name} {next_line}"
                        if identifier not in processed_channels:
                            current_channel += 1
                            status = check_channel_status(next_line, timeout)
                            screenshot_taken = False
                            if status == 'Alive':
                                file_name = f"{current_channel}-{channel_name.replace('/', '-')}"  # Replace '/' to avoid path issues
                                screenshot_taken = capture_frame(next_line, output_folder, file_name)
                            console_log_entry(current_channel, total_channels, channel_name, status, screenshot_taken)
                            processed_channels.add(identifier)
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}. Please check the path and try again.")
    except Exception as e:
        logging.error(f"An unexpected error occurred while processing the file: {str(e)}")

def main():
    print_header()

    parser = argparse.ArgumentParser(description="Check the status of channels in an IPTV M3U8 playlist and capture frames of live channels.")
    parser.add_argument("playlist_path", type=str, help="Path to the M3U8 playlist file")
    parser.add_argument("--group", type=str, default=None, help="Specific group title to check within the playlist")
    parser.add_argument("--timeout", type=float, default=10.0, help="Timeout in seconds for checking channel status")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase output verbosity (1 for info, 2 for debug)")

    args = parser.parse_args()

    setup_logging(args.verbose)
    group_name = args.group.replace('|', '').replace(' ', '') if args.group else 'AllGroups'  # Define group_name based on args.group
    log_file_name = f"{os.path.basename(args.playlist_path).split('.')[0]}_{group_name}_checklog.txt"

    parse_m3u8_file(args.playlist_path, args.group, args.timeout, log_file_name)

if __name__ == "__main__":
    main()
