# IPTV Stream Checker

![IPTV Stream Checker](https://img.shields.io/badge/IPTV%20Checker-v1.0-blue.svg) ![Python](https://img.shields.io/badge/Python-3.6%2B-brightgreen.svg) ![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Overview

IPTV Stream Checker is a command-line tool designed to check the status of channels in an IPTV M3U8 playlist. It verifies if the streams are alive, captures screenshots, provides detailed information about video and audio streams, and identifies any potential issues like low framerates or mislabeled channels.

<img width="794" alt="screenshot" src="https://github.com/user-attachments/assets/ffa84de1-f644-44b5-9d7d-92e32652a2be">

## Features

- **Check Stream Status:** Verify if IPTV streams are alive or dead.
- **Split Playlist:** Split into separate playlists for working and dead channels.
- **Capture Screenshots:** Capture screenshots from live streams.
- **Group Filter:** Option to check specific groups within the M3U8 playlist.
- **Detailed Stream Info:** Retrieve and display video codec, resolution, framerate, and audio bitrate.
- **Low Framerate Detection:** Identifies and lists channels with framerates at 30fps or below.
- **Mislabeled Channel Detection:** Detects channels with resolutions that do not match their labels (e.g., "1080p" labeled as "4K").
- **Custom User-Agent:** Uses `IPTVChecker 1.0` as the user agent for HTTP requests.

## Installation

### Prerequisites

- **Python 3.6+**
- **ffmpeg** and **ffprobe**: Required for capturing screenshots and retrieving stream information.

### Clone the Repository

```bash
git clone https://github.com/NewsGuyTor/IPTVChecker.git
cd IPTVChecker
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### Basic Command

```bash
python IPTV_checker.py /path/to/your/playlist.m3u8
```

### Options

- **`-group` or `-g`**: Specify a group title to check within the playlist.
- **`-timeout` or `-t`**: Set a timeout in seconds for checking the channel status.
- **`-extended` or `-e [seconds]`**: Enable an extended timeout check for channels detected as dead. If specified without a value, defaults to 10 seconds. This option allows you to retry dead channels with a longer timeout.
- **`-split` or `-s`**: Create separate playlists for working and dead channels.
- **`-v`**: Increase output verbosity to `INFO` level.
- **`-vv`** or **`-debug`**: Increase output verbosity to `DEBUG` level.

### Examples

1. **Standard Check**:
   ```bash
   python IPTV_checker.py /path/to/your/playlist.m3u8 -group "SPORT HD"
   ```

2. **Check with Extended Timeout of 10 Seconds and debug**:
   ```bash
   python IPTV_checker.py /path/to/your/playlist.m3u8 -group "SPORT HD" -extended 15 -vv
   ```

3. **Split Playlists into Working and Dead Channels**:
   ```bash
   python IPTV_checker.py /path/to/your/playlist.m3u8 -group "SPORT HD" -split
   ```

### Output Format

The script will output the status of each channel in the following format:

```bash
1/5 ✓ Channel Name | Video: 1080p60 H264 - Audio: 159 kbps AAC
```

### Low Framerate Channels

After processing, the script lists any channels with framerates of 30fps or below:

```bash
Low Framerate Channels:
1/5 EGGBALL TV HD - 25fps
```

### Mislabeled Channels

The script also detects channels with incorrect labels:

```bash
Mislabeled Channels:
3/5 Sports5 FHD - Expected 1080p, got 4K
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request or open an issue if you have any ideas or feedback.
