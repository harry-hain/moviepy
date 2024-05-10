def parse_metadata_field_value(line):
    """Returns a tuple with a metadata field-value pair given a ffmpeg `-i` command output line."""
    raw_field, raw_value = line.split(":", 1)
    return raw_field.strip(" "), raw_value.strip(" ")


def video_metadata_type_casting(field, value):
    """Cast needed video metadata fields to other types than the default str."""
    if field == "rotate":
        return field, float(value)
    return field, value
