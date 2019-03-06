import subprocess
import re
from datetime import datetime, timedelta

file = r'F:\TestMovies\060_Xperia_190211_171016.MP4'

def get_metadata(file):
    """Returns metadata as a dictionary."""
    p1 = subprocess.Popen(["exiftool", file],stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    metadata_str = p1.communicate()[0].decode("utf-8")  # class 'bytes', sequence of bytes, similar to string, but ASCII only and immutable
    rx = re.compile('\W+\: ') # regex to remove whitespace after the key (before the colon)
    metadata_list = [rx.sub(': ',item) for item in metadata_str.split("\r\n")]
    metadata_dict = dict(item.split(": ") for item in metadata_list[:-1]) # the last item is an ' and can't be split
    return metadata_dict
    
def set_metadata(file, metadata):
    """Sets all the dates to the file modification date of the original movie and restores make/model information."""
    target_date_time_str = metadata['File Modification Date/Time']
    target_date_time_adj_str = datetime.strptime(target_date_time_str[:19], '%Y:%m:%d %H:%M:%S') # [:19] -> remove offset
    make = metadata['Make'] #ToDo: Catch key error when key does not exist -> if key in my_dict and not (my_dict[key] is None):  -> Do that for each key, while reading and writing
    model = metadata['Model']
    software = metadata['Software']
    rotation = metadata['Rotation']
    # handler_vendor_id = metadata['Handler Vendor ID'] # not writeable :(
    
    # it's not required to substract an hour (code below)
    # target_date_time_dt = datetime.strptime(target_date_time_str[:19], '%Y:%m:%d %H:%M:%S') # [:19] -> remove offset
    # target_date_time_adj_str = (target_date_time_dt + timedelta(hours=-1)).strftime('%Y:%m:%d %H:%M:%S')  # some dates need to be adjusted by -1 h and have the timezone information (+01:00) removed
    # print(target_date_time_str)
    # print(target_date_time_adj_str)

    # assemble string beforehand because subprocess introduces spaces between the arguments (between " and the file path)
    command = ('exiftool -FileModifyDate="{0}" -FileCreateDate="{0}" -CreationDate="{0}" '
        '-MediaCreateDate="{1}" -MediaModifyDate="{1}" -CreateDate="{1}" -ModifyDate="{1}" -TrackCreateDate="{1}" -TrackModifyDate="{1}" '
        '-Make="{2}" -Model="{3}" -Software="{4}" -Rotation="{5}" "{6}"'
        .format(target_date_time_str, target_date_time_adj_str, make, model, software, rotation, file))

    # print(command)
    subprocess.check_call(command)

metadata = get_metadata(file)
set_metadata(file, metadata)
# print(metadata)
# print(metadata['File Modification Date/Time'])


