import subprocess
import re
import os
# from datetime import datetime, timedelta

movie_path_in = r'F:\TestMovies\P1140826.MP4'

# ToDo: Folder or File as Input Paramter. If Folder is passed: process all movie files, otherwise only single movie
# ToDo: (Optional) as default: use folder from which script is called
# ToDo: Implement some kind of progress bar, at least when looping through file list
# DONE: Erstellen von _original unterdrücken


def get_metadata(movie_path):
    """Returns metadata as a dictionary."""
    p1 = subprocess.Popen(["exiftool", movie_path],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # class 'bytes', sequence of bytes, similar to string, but ASCII only and immutable
    metadata_str = p1.communicate()[0].decode("utf-8")
    # regex to remove whitespace after the key (before the colon)
    rx = re.compile('\W+\: ')
    metadata_list = [rx.sub(': ', item) for item in metadata_str.split("\r\n")]
    # the last item is an ' and can't be split
    metadata_dict = dict(item.split(": ", maxsplit=1) for item in metadata_list[:-1])
    return metadata_dict


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
    #print(command)
    return movie_cmp


def set_metadata(movie_path, metadata):
    """Sets all the dates to the file modification date of the original movie and restores make/model information."""

    target_date_time_str = metadata['File Modification Date/Time']
    # [:19] -> remove offset
    target_date_time_adj_str = target_date_time_str[:19]

    metadata_to_use_dict = {
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
        "iModel": ["-Model", ""],
        "Software": ["-Software", ""],
        "Rotation": ["-Rotation", ""]

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
movie_path_out = compress_movie(movie_path_in) #, '23', 'slow')
set_metadata(movie_path_out, metadata)
# print(metadata)
# print(metadata['file Modification Date/Time'])
