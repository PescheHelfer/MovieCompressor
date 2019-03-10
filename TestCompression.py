import subprocess
#import re
import os
import time

movie_path_in = r'F:\TestMovies\P1090370.MP4'


def test_movie_compression(movie_path, crf, speed='', aac=''):
    _crf = str(crf)
    _preset = '' if speed == '' else (' -preset '+speed)
    _aac = '' if aac == '' else (' -c:a '+aac)
    movie_lst = os.path.splitext(movie_path)
    movie_cmp = '{0}_crf{1}{2}{3}{4}'.format(
        movie_lst[0]
        , _crf
        , '' if speed == '' else ('_'+speed)
        , '' if aac == '' else ('_'+aac.replace('-','').replace(':','').replace(' ','_'))
        , movie_lst[1])
    command = 'ffmpeg -i "{0}" -c:v libx264 -crf {1}{2}{3} "{4}"'.format(
        movie_path, _crf, _preset, _aac, movie_cmp)
    # -i              -> input file(s)
    # -c:v            -> select video encoder
    # -c:a            -> select audio encoder (skipping this will simply copy the audio stream without reencoding)
    # -crf            -> Change the CRF value for video. Lower means better quality. 23 is default, and anything below 18 will probably be visually lossless
    # -map_metadata 0 -> Map the metadata from file 0 to the output
    # https://trac.ffmpeg.org/wiki/Encode/H.264
    # http://trac.ffmpeg.org/wiki/Encode/AAC

    print(command)
    t = time.time()
    subprocess.check_call(command)
    print('Elapsed_time:{}'.format(time.time() - t))
    return movie_cmp


# print(test_movie_compression(movie_path_in, 23))
# print(test_movie_compression(movie_path_in, 23, 'slow'))
# print(test_movie_compression(movie_path_in, 23, 'slow', 'aac'))
# print(test_movie_compression(movie_path_in, 24, 'slow'))
# print(test_movie_compression(movie_path_in, 25, 'slow'))
# print(test_movie_compression(movie_path_in, 25, 'slower'))
# print(test_movie_compression(movie_path_in, 25, 'veryslow'))
# print(test_movie_compression(movie_path_in, 26, 'slow'))
# print(test_movie_compression(movie_path_in, 27, 'slow'))
# print(test_movie_compression(movie_path_in, 27, 'slower'))
# print(test_movie_compression(movie_path_in, 30, 'slow'))
# print(test_movie_compression(movie_path_in, 30, 'slower'))
# print(test_movie_compression(movie_path_in, 30, 'veryslow'))

print(test_movie_compression(movie_path_in, 25, 'slow', 'aac -b:a 160k'))
print(test_movie_compression(movie_path_in, 25, 'slow', 'aac -b:a 128k'))
print(test_movie_compression(movie_path_in, 25, 'slow', 'aac -q:a 2'))
print(test_movie_compression(movie_path_in, 25, 'slow', 'aac -q:a 1'))