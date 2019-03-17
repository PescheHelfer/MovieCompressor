import subprocess
import re
import os
from datetime import datetime, timezone  # , timedelta

movie_path_in = r'f:\TestMovies\CameraTest\SamsungWB2000\SAM_4763.MP4'

# ToDo: Folder or File as Input Paramter. If Folder is passed: process all movie files, otherwise only single movie
# IDEA: (Optional) as default: use folder from which script is called
# IDEA: Implement some kind of progress bar, at least when looping through file list
# DONE: Erstellen von _original unterdrücken


def get_metadata(movie_path):
    """Returns metadata as a dictionary."""
    p1 = subprocess.Popen(['exiftool', '-s', movie_path],  # -s -> returns tags instead of descriptions
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # class 'bytes', sequence of bytes, similar to string, but ASCII only and immutable
    metadata_str = p1.communicate()[0].decode("utf-8")
    # regex to remove whitespace after the key (before the colon)
    rx = re.compile('\W+\: ')
    metadata_list = [rx.sub(': ', item) for item in metadata_str.split("\r\n")]
    # the last item is an ' and can't be split
    metadata_dict = dict(item.split(": ", maxsplit=1)
                         for item in metadata_list[:-1])
    return metadata_dict


def try_parse_date(string):
    """Converts a datetime from a string of three formats"""  # and returns a datetime object of the format %Y:%m:%d %H:%M:%S"""
    # ToDo: can MIN() handle different lengths of datetime? How does it deal with timezones? Is it necessary to truncate the returned object?
    # Formats to parse:
    # - '2018:08:26 15:56:09.798'
    # - '2018:08:26 14:56:09'
    # - '2019:03:10 20:11:19+01:00'
    try:
        return datetime.strptime(string, "%Y:%m:%d %H:%M:%S")
    except ValueError:
        pass
    try:
        return datetime.strptime(string, "%Y:%m:%d %H:%M:%S.%f")
    except ValueError:
        pass
    try:
        return datetime.strptime(string, "%Y:%m:%d %H:%M:%S%z")
    except ValueError:
        return None


def get_original_date_and_tz_offset(metadata):
    # Bei den meisten Modellen sind nur das "CreationDate" (Apple), "DateTimeOriginal" (einige andere) verlässlich. Jedoch weisen nicht alle
    # Modelle diese Felder auf. Meistens ist auch das "FileModifyDate" verlässlich. Übrige Zeitangaben weichen je Modell um -1h ab, unabhängig von Sommerzeit.
    # Allerdings gibt es auch Fälle, bei denen das FileModifyDate Jahre nach den andern Zeitangaben liegt. Dabei scheint es sich allerdings
    # um Fehler zu handeln (Movies aus 2009 von Menschen, die es noch gar nicht gab) und das FileModifyDate scheint hier korrekt zu sein.
    # Logik: 
    # "CreationDate" oder "DateTimeOriginal" vorhanden? -> dieses nehmen
    #   (Liegt das kleinste Datum mehr als 30 Tage vor dem "FileModifyDate"? -> dieses nehmen) -> verworfen, das wäre falsch!
    # sonst "FileModifyDate" nehmen.
    # TimeZone: wenn vorhanden, aus dem "CreationDate" nehmen
    #   (Liegt das kleinste Datum mehr als 1 Monat vor dem "FileModifyDate", schauen ob es am gleichen Tag ein Feld mit einer TZ gibt,
    #   sonst TZ leer lassen)  -> verworfen, das wäre falsch!
    # Sonst aus dem "FileModifyDate" übernehmen.

    # parse strings and remove timezone to avoid error: TypeError("can't compare offset-naive and offset-aware datetimes")
    dates_dict = {k: try_parse_date(v) for (k, v) in metadata.items()}
    dates_dict_tz_removed = {k: v.replace(tzinfo=None) for (
        k, v) in dates_dict.items() if v is not None}
    dates_dict_tz = {k: v for (
        k, v) in dates_dict.items() if v is not None if v.tzinfo is not None if v.tzinfo.utcoffset(v) is not None}

    min_date = min({k: v.replace(tzinfo=None) for (
        k, v) in dates_dict_tz_removed.items() if v is not None}.values())
    original_date = None
    tz_info = None

    # get datetime
    if 'CreationDate' in dates_dict:
        original_date = dates_dict_tz_removed['CreationDate']
    elif 'DateTimeOriginal' in dates_dict:
        original_date = dates_dict_tz_removed['DateTimeOriginal']
    # elif (dates_dict_tz_removed['FileModifyDate'] - min_date).days > 30:
    #     original_date = min_date
    else:
        original_date = dates_dict_tz_removed['FileModifyDate']

    # get timezone (which could be on an other field)
    if 'CreationDate' in dates_dict_tz:
        tz_info = dates_dict_tz['CreationDate'].tzinfo
    elif 'DateTimeOriginal' in dates_dict_tz:
        tz_info = dates_dict_tz['DateTimeOriginal'].tzinfo
    # elif (dates_dict_tz_removed['FileModifyDate'] - min_date).days > 30:
    #     # get timezone from any field which has the same date like the smallest date
    #     try:
    #         min({k: v for (k, v) in dates_dict_tz.items()
    #              if v.date() == min_date.date()}.values()).tzinfo
    #     except ValueError:
    #         tz_info = None
    else:
        tz_info = dates_dict_tz['FileModifyDate'].tzinfo

    if tz_info != None:
        original_date_tz = original_date.replace(
            tzinfo=tz_info).strftime("%Y:%m:%d %H:%M:%S%z")
        # insert the missing colon in the timezone part
        original_date_tz = original_date_tz[:-2]+':'+original_date_tz[-2:]
    else:
        original_date_tz = original_date.strftime("%Y:%m:%d %H:%M:%S")

    return {'original_date': original_date.strftime("%Y:%m:%d %H:%M:%S"),
            'original_date_tz': original_date_tz}


def compress_movie(movie_path, crf='25', speed='veryslow'):
    _crf = str(crf)
    _preset = '' if speed == '' else (' -preset '+speed)
    movie_lst = os.path.splitext(movie_path)
    movie_cmp = movie_lst[0]+'_c'+movie_lst[1]
    command = 'ffmpeg -i "{0}" -c:v libx264 -crf {1}{2} -map_metadata 0 "{3}"'.format(
        movie_path,  _crf, _preset, movie_cmp)
    # -i              -> input file(s)
    # -c:v            -> select video encoder
    # -c:a            -> select audio encoder (skipping this will simply copy the audio stream without reencoding)
    # -crf            -> Change the CRF value for video. Lower means better quality. 23 is default, and anything below 18 will probably be visually lossless
    # -preset slower  -> slower settings have better quality:compression ratios. Each step about doubles the processing time!
    # -map_metadata 0 -> Map the metadata from file 0 to the output
    # https://trac.ffmpeg.org/wiki/Encode/H.264
    # http://trac.ffmpeg.org/wiki/Encode/AAC
    subprocess.check_call(command)
    # print(command)
    return movie_cmp


def set_metadata(movie_path, metadata):
    """Sets all the dates to the file modification date of the original movie and restores make/model information."""

    target_date_time_str = metadata['File Modification Date/Time']
    # [:19] -> remove offset
    target_date_time_adj_str = target_date_time_str[:19]

    metadata_to_use_dict = {  # ToDo: DateTimeOriginal, e.g. '2018:08:26 15:56:09'
        "File Modification Date/Time": ["-FileModifyDate", target_date_time_str],
        "File Creation Date/Time": ["-FileCreateDate", target_date_time_str],
        "Creation Date": ["-CreationDate", target_date_time_str],
        "Media Create Date": ["-MediaCreateDate", target_date_time_adj_str],
        "Media Modify Date": ["-MediaModifyDate", target_date_time_adj_str],
        "Create Date": ["-CreateDate", target_date_time_adj_str],
        "Modify Date": ["-ModifyDate", target_date_time_adj_str],
        "Track Create Date": ["-TrackCreateDate", target_date_time_adj_str],
        "Track Modify Date": ["-TrackModifyDate", target_date_time_adj_str],
        "Make": ["-Make", ""],
        "Model": ["-Model", ""],
        "Software": ["-Software", ""],
        "Rotation": ["-Rotation", ""],
        "Camera Model Name": ["-Model", ""],
        "Exposure Time": ["-ExposureTime", ""],
        "F Number": ["-FNumber", ""],
        "Exposure Program": ["-ExposureProgram", ""],
        "ISO": ["-ISO", ""],
        "Max Aperture Value": ["-MaxApertureValue", ""],
        "Metering Mode": ["-MeteringMode", ""],
        "Light Source": ["-LightSource", ""],
        "Flash": ["-Flash", ""],
        # ToDo Not a floating point number for ExifIFD:FocalLength
        "Focal Length": ["-FocalLength", ""],
        "Image Quality": ["-ImageQuality", ""],
        "Firmware Version": ["-FirmwareVersion", ""],
        "White Balance": ["-WhiteBalance", ""],
        "Focus Mode": ["-FocusMode", ""],
        "AF Area Mode": ["-AFAreaMode", ""],
        "Image Stabilization": ["-ImageStabilization", ""],
        "Macro Mode": ["-MacroMode", ""],
        "Shooting Mode": ["-ShootingMode", ""]
    }
    # handler_vendor_id = metadata['Handler Vendor ID'] # not writeable :(
    # list to join to create the final command string in the end
    stringbuilder = ["exiftool"]

    for key, value in metadata_to_use_dict.items():
        if(key in metadata):
            stringbuilder.append(
                value[0]+'="'+(metadata[key] if value[1] == "" else value[1])+'"')

    # prevents creation of _original file
    stringbuilder.append('-overwrite_original')
    stringbuilder.append('"'+movie_path+'"')
    # note: the space in " " is actually the seperator!
    command = " ".join(stringbuilder)
    subprocess.check_call(command)


metadata = get_metadata(movie_path_in)
original_date_dict = get_original_date_and_tz_offset(metadata)
print(original_date_dict)

# movie_path_out = compress_movie(movie_path_in)  # , '23', 'slow')
#set_metadata(movie_path_out, metadata)

# print(metadata)
# print(metadata['file Modification Date/Time'])
