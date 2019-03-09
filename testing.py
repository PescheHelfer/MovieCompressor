import hachoir  # not used, exiftool is the way to go
import subprocess
import datetime
import os.path
import time
import re

file = r'F:\TestMovies\IMG_0185.MOV'

p1 = subprocess.Popen(["exiftool", file], stdout=subprocess.PIPE)
# class 'bytes', sequence of bytes, similar to string, but ASCII only and immutable
output = p1.communicate()[0]
output_str = output.decode("utf-8")

# regex to remove whitespace after the key (before the colon)
rx = re.compile('\W+\: ')

output_list = [rx.sub(': ', item) for item in output_str.split("\r\n")]
# the last item is an ' and can't be split
output_dict = dict(item.split(": ") for item in output_list[:-1])

output_dict['File Creation Date/Time']

# ExifTools Parameter
# -overwrite_original_in_place (in which case the contents of the output file are used to overwrite the original, and the output file is deleted).


# hachoir not the way to go, use exiftools intead (see above)
def get_media_properties(filename):

    result = subprocess.Popen(['hachoir-metadata', filename, '--raw'],  # '--level=3'],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    results = result.stdout.read().decode('utf-8').split('\r\n')

    print(results)

    properties = {}

    for item in results:

        if item.startswith('- duration: '):
            duration = item.lstrip('- duration: ')
            if '.' in duration:
                t = datetime.datetime.strptime(
                    item.lstrip('- duration: '), '%H:%M:%S.%f')
            else:
                t = datetime.datetime.strptime(
                    item.lstrip('- duration: '), '%H:%M:%S')
            seconds = (t.microsecond / 1e6) + t.second + \
                (t.minute * 60) + (t.hour * 3600)
            properties['duration'] = round(seconds)

        if item.startswith('- width: '):
            properties['width'] = int(item.lstrip('- width: '))

        if item.startswith('- height: '):
            properties['height'] = int(item.lstrip('- height: '))

    return properties


properties = get_media_properties(file)

print(properties)
# creation_date und last_moditifaction entsprechen dem (falschen) Ursrungsdatum (Ursprung -> Medium erstellt), nicht den korrigierten Datumsangaben des Files
# DONE: Wie kommt man an die Datumsangaben des Files ran? -> see below


# get creation and modification date of the file (the one I corrected, not the same as the one from metadata)
print("last modified: %s" % time.ctime(os.path.getmtime(file)))
print("created: %s" % time.ctime(os.path.getctime(file)))
