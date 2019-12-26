# MovieCompressor

Purpose
-------
Compresses movies maintaing as much of the metadata as possible, especially dates. Intended for short movies shot in holidays etc. to save space. Depending on the camera model used, the movies can be reduced in size by several factors without significant loss of quality.

Credits
-------
The tool is based on the [FFmpeg project](https://www.ffmpeg.org/) and [ExifTool](https://exiftool.org/) by Phil Harvey.

Prerequisites
-------------
- Python 3.7 and packages according to Conda environment CondaEnv_MovieCompressor.yml
- [FFmpeg](https://www.ffmpeg.org/)
- [ExifTool](https://exiftool.org/)

Limitations
-----------
- Not all exif tags are writable. Write protected tags can not be transferred to the compressed movie.
- I could only test the tool with the camera models and smartphones available to me. Other models may use Exif tags that I did not consider.

Setup
-----
The following procedure only works for Windows. For other operating systems they must be adapted accordingly.
1. Rename config.yml.example to config.yml
2. Edit config.yml and adjust the paths to FFmpeg and ExifTool
3. Edit MovieCompressor.bat and adjust `python f:\Libraries\Pesche\Docs_Pesche\Coding\Python\MovieCompressor\MovieCompressor.py %params%` to your installation path
4. Optional: copy/move MovieCompressor.bat to a directory where you keep command line tools
5. Either add the install directory or the directory where you keep command line tools to [Path in Windows Environment Variables](https://www.computerhope.com/issues/ch000549.htm) so that it can be called from anywhere

Usage
-----
1. Open a command line prompt in the folder containing your movies. 
2. Type `MovieCompressor`

A list of all processable movies will be displayed. Proceed with 'y' or abort with 'n'.

To compress a single movie, use the full path to the movie, e.g. `MovieCompressor "D:\MyMovies\20191201\Xmas\SomeMovie.mp4"`

By default, all movies will be processed with the following settings:<br />
`-c:v libx265 -crf 25 -preset slow`

Those settings can be changed by passing arguments to the command line. Use `MovieCompressor -h` to display the following help.

```
positional arguments:
  path                  Path to the movie or a directory containing movies

optional arguments:
  -h, --help            show this help message and exit
  --clip_from CLIP_FROM
                        Start time from which the movie is to be copied
                        [format 00:00:00 or 00:00:00.0]
  --clip_to CLIP_TO     End time up to which the movie is to be copied
                        [format 00:00:00 or 00:00:00.0]
  -c or --codec {x265,x264}
                        Codec to be used for encoding
  --crf CRF             Constant Rate Factor to be used.
                        By default (empty) 25 is used for x265 and 24 for x264
  -s or --speed {ultrafast,superfast,veryfast,faster,fast,medium,slow,slower,veryslow}
                        Encoding preset to be used. By default (empty) 'slow'
                        is used for x265 and 'veryslow' for x264
  -t or --tune {film,animation,grain,stillimage,fastdecode,zerolatency,psnr,ssim,HQ}
                        Set tune option (different options for x264 and x265).
                        Empty by default.
                        HQ is a x preset for difficult low light movies and overrides other arguments:
                            x264, crf=22, speed=veryslow, tune=film
  -r or --transpose {0,1,2,3,4}
                        Set transpose/rotation option (ffmpeg):
                            0 – Rotate by 90 degrees counter-clockwise and flip vertically
                            1 – Rotate by 90 degrees clockwise
                            2 – Rotate by 90 degrees counter-clockwise
                            3 – Rotate by 90 degrees clockwise and flip vertically
                            4 – Rotate by 180 degrees (not an ffmpeg option)```
