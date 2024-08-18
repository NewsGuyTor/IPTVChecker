# IPTV Stream Checker

![IPTV Stream Checker](https://img.shields.io/badge/IPTV%20Checker-v1.0-blue.svg) ![Python](https://img.shields.io/badge/Python-3.6%2B-brightgreen.svg) ![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Overview

IPTV Stream Checker is a command-line tool designed to check the status of channels in an IPTV M3U8 playlist. It verifies if the streams are alive, captures screenshots, and provides detailed information about video and audio streams, including codec, resolution, and bitrate. 

![IPTV Checker Demo](demo.gif)  <!-- Add a demo GIF or screenshot here -->

## Features

- **Check Stream Status:** Verify if IPTV streams are alive or dead.
- **Capture Screenshots:** Capture screenshots from live streams.
- **Detailed Stream Info:** Retrieve and display video codec, resolution, and audio bitrate.
- **Custom User-Agent:** Uses `IPTVChecker 1.0` as the user agent for HTTP requests.
- **Group Filter:** Option to check specific groups within the M3U8 playlist.

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

- **`--group`**: Specify a group title to check within the playlist.
- **`--timeout`**: Set a timeout in seconds for checking the channel status.
- **`-v` or `--verbose`**: Increase output verbosity. Use `-v` for info level or `-vv` for debug level.

### Example

```bash
python IPTV_checker.py /path/to/your/playlist.m3u8 --group "SPORT HD" --timeout 10 -vv
```

### Output Format

The script will output the status of each channel in the following format:

```bash
4/42 Channel Name - Alive: ✓ ||| Video: 1080p H264 - Audio: 159 kbps AAC
```

## Screenshots

<!-- Add screenshots of the tool in action here -->

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request or open an issue if you have any ideas or feedback.
