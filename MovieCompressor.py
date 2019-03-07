import subprocess
import re
import os
from datetime import datetime, timedelta

movie = r'F:\TestMovies\096_Pana_P1200692.MP4'


# ToDo: Folder or File as Input Paramter. If Folder is passed: process all movie files, otherwise only single movie
# ToDo: (Optional) as default: use folder from which script is called
# ToDo: Implement some kind of progress bar, at least when looping through file list
# ToDo: Best practice: variable naming in different scopes (ok to have same name globaly as within the function? Use underscores?)
# ToDo: Änderungsdatum wird irgendwann nach applien der Metadaten doch noch auf heute gesetzt. Andere Reihenfolge wählen? Separt ausführen?
# ToDo: Erstellen von _original unterdrücken

def get_metadata(movie):
    """Returns metadata as a dictionary."""
    p1 = subprocess.Popen(["exiftool", movie],stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    metadata_str = p1.communicate()[0].decode("utf-8")  # class 'bytes', sequence of bytes, similar to string, but ASCII only and immutable
    rx = re.compile('\W+\: ') # regex to remove whitespace after the key (before the colon)
    metadata_list = [rx.sub(': ',item) for item in metadata_str.split("\r\n")]
    metadata_dict = dict(item.split(": ") for item in metadata_list[:-1]) # the last item is an ' and can't be split
    return metadata_dict

def compress_movie(movie):
    movie_lst = os.path.splitext(movie)
    movie_cmp = movie_lst[0]+'_cmp'+movie_lst[1]
    command = 'ffmpeg -i "'+movie+'" -c:v libx264 -crf 23 -c:a aac -map_metadata 0 "'+movie_cmp+'"'
   # print(command)
    subprocess.check_call(command)
    return movie_cmp

def set_metadata(movie_cmp, metadata):
    """Sets all the dates to the file modification date of the original movie and restores make/model information."""
    
    target_date_time_str = metadata['File Modification Date/Time']
    target_date_time_adj_str = target_date_time_str[:19] # [:19] -> remove offset

    metadata_to_use_dict = {
		"File Modification Date/Time" : ["-FileModifyDate",target_date_time_str],
		"File Creation Date/Time" : ["-FileCreateDate",target_date_time_str],
		"Creation Date" : ["-CreationDate",target_date_time_str],
		"Media Create Date" : ["-MediaCreateDate",target_date_time_adj_str],
		"Media Modify Date" : ["-MediaModifyDate",target_date_time_adj_str],
		"Create Date" : ["-CreateDate",target_date_time_adj_str],
        "Modify Date" : ["-ModifyDate",target_date_time_adj_str],
        "Track Create Date" : ["-TrackCreateDate",target_date_time_adj_str],
        "Track Modify Date" : ["-TrackModifyDate",target_date_time_adj_str],
        "Make" : ["-Make",""],
        "iModel" : ["-Model",""],
        "Software" : ["-Software",""],
        "Rotation" : ["-Rotation",""]

	}
    # handler_vendor_id = metadata['Handler Vendor ID'] # not writeable :(
    stringbuilder = ["exiftool"] # list to join to create the final command string in the end

    for key, value in metadata_to_use_dict.items():
        if(key in metadata):
            stringbuilder.append(value[0]+'="'+(metadata[key] if value[1]=="" else value[1])+'"')

    stringbuilder.append('"'+movie_cmp+'"')
    command = " ".join(stringbuilder) # note: the space in " " is actually the seperator!
    subprocess.check_call(command)

metadata = get_metadata(movie)
movie_cmp = compress_movie(movie)
set_metadata(movie_cmp, metadata)
# print(metadata)
# print(metadata['file Modification Date/Time'])


