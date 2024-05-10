import re


def extract_stream_info(line):
    """Extracts stream information from a streamline."""
    main_info_match = re.search(r"^Stream\s#(\d+):(\d+)(?:\[\w+])?\(?(\w+)?\)?:\s(\w+):", line.lstrip())
    if not main_info_match:
        return None
    input_number, stream_number, language, stream_type = main_info_match.groups()
    default = "default" in line

    return {
        "input_number": int(input_number),
        "stream_number": int(stream_number),
        "stream_type": stream_type.lower(),
        "language": language or None,
        "default": default
    }


def extract_chapter_info(line):
    """Extracts chapter information from a chapter line."""
    chapter_match = re.search(r"^ {4}Chapter #(\d+):(\d+): start (\d+\.?\d+?), end (\d+\.?\d+?)", line)
    if not chapter_match:
        return None
    input_number, chapter_number, start, end = chapter_match.groups()
    return {
        "input_number": int(input_number),
        "chapter_number": int(chapter_number),
        "start": float(start),
        "end": float(end)
    }
