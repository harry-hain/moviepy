import re

class FileMetadata:
    def __init__(self):
        self.result = {
            "duration": None,
            "bitrate": None,
            "start": None,
            "metadata": {},
            "inputs": [],
            "video_found": False,
            "video_n_frames": None,
            "video_duration": None,
            "audio_found": False,
            "audio_bitrate": None,
        }

    def parse_duration(self, line, duration_tag_separator):
        try:
            time_raw_string = line.split(duration_tag_separator)[-1]
            match_duration = re.search(
                r"([0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9])",
                time_raw_string,
            )
            return convert_to_seconds(match_duration.group(1))
        except Exception:
            raise IOError(
                (
                    "MoviePy error: failed to read the duration of file '%s'.\n"
                    "Here are the file infos returned by ffmpeg:\n\n%s"
                )
                % (self.filename, self.infos)
            )

    def parse_metadata_field_value(self, line):
        raw_field, raw_value = line.split(":", 1)
        return raw_field.strip(" "), raw_value.strip(" ")

    def video_metadata_type_casting(self, field, value):
        if field == "rotate":
            return field, float(value)
        return field, value

    def update_global_data(self, global_data):
        self.result.update(global_data)

def convert_to_seconds(time):
    factors = (1, 60, 3600)

    if isinstance(time, str):
        time = [float(part.replace(",", ".")) for part in time.split(":")]

    if not isinstance(time, (tuple, list)):
        return time

    return sum(mult * part for mult, part in zip(factors, reversed(time)))
