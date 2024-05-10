from moviepy import convert_to_seconds
import re


def extract_start_time(line):
    """Extracts the start time from a line containing duration information."""
    start_match = re.search(r"start: (\d+\.?\d+)", line)
    return float(start_match.group(1)) if start_match else None


def extract_bitrate(line):
    """Extracts the bitrate from a line containing duration information."""
    bitrate_match = re.search(r"bitrate: (\d+) kb/s", line)
    return int(bitrate_match.group(1)) if bitrate_match else None


def parse_fps(line):
    """Parses number of FPS from a line of the `ffmpeg -i` command output."""
    return float(re.search(r" (\d+.?\d*) fps", line).group(1))


def parse_tbr(line):
    """Parses number of TBS from a line of the `ffmpeg -i` command output."""
    s_tbr = re.search(r" (\d+.?\d*k?) tbr", line).group(1)
    if s_tbr[-1] == "k":
        tbr = float(s_tbr[:-1]) * 1000
    else:
        tbr = float(s_tbr)
    return tbr
