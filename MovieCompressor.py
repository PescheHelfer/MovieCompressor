import argparse
import yaml
import os
import sys
import subprocess
from datetime import datetime, timezone  # , timedelta
from colorama import Fore, Style, init
init()  # colorama

# ---- Variables ---- #
path_exif = ""
path_ffmpeg = ""

# both are defined in config.yml


# ---- Classes ---- #
class SmartFormatter(argparse.HelpFormatter):
    """Enables multiline help messages
    https://stackoverflow.com/questions/3853722/python-argparse-how-to-insert-newline-in-the-help-text"""

    def _split_lines(self, text, width):
        if text.startswith('R|'):
            return text[2:].splitlines()
        # this is the RawTextHelpFormatter._split_lines
        return argparse.HelpFormatter._split_lines(self, text, width)


# ---- Functions ---- #
def print_info(string):
    print(Fore.CYAN + string + Fore.RESET + Style.NORMAL)


def print_error(string):
    print(Fore.RED + string + Fore.RESET + Style.NORMAL)


def input_color(string):
    print(Fore.YELLOW)
    inp = input(string)
    print(Fore.RESET + Style.NORMAL)
    return inp


def try_parse_date(string):
    """Converts a datetime from a string of three formats"""  # and returns a datetime object of the format %Y:%m:%d %H:%M:%S"""
    # Formats to parse:
    # - "2018:08:26 15:56:09.798"
    # - "2018:08:26 14:56:09"
    # - "2019:03:10 20:11:19+01:00"
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


def try_parse_time(string):
    """Converts a datetime from a string of three formats"""  # and returns a datetime object of the format %Y:%m:%d %H:%M:%S"""
    # Formats to parse:
    # - "15:56:09.798"
    # - "14:56:09"

    try:
        return datetime.strptime(string, "%H:%M:%S.%f")
    except ValueError:
        pass
    return datetime.strptime(string, "%H:%M:%S")  # shall fail if invalid time for check_valid_time to work properly


def check_valid_time(string):
    try:
        try_parse_time(string)
        return string
    except ValueError:
        msg = "Not a valid time: '{0}'.".format(string)
        raise argparse.ArgumentTypeError(msg)


def check_valid_path(path, error_msg_appendix=""):
    if os.path.isfile(path) or os.path.isdir(path):
        return path
    else:
        msg = "Not a valid file or directory path: '{0}'{1}".format(path, ("\r\n" + error_msg_appendix) if error_msg_appendix != "" else "")
        print_error(msg)
        quit()
        #raise argparse.ArgumentTypeError(msg)


def check_valid_tune(codec, tune):
    x264_tunes = ["film", "animation", "grain", "stillimage", "fastdecode", "zerolatency", "psnr", "ssim"]
    x265_tunes = ["psnr", "ssim", "grain", "zerolatency", "fastdecode"]

    if tune in ["", "HQ"]:
        return
    elif codec == "x264" and tune not in x264_tunes:
        print_error("Valid tunes for x264: {}".format(", ".join(x264_tunes)))
        quit()
    elif codec == "x265" and tune not in x265_tunes:
        print_error("Valid tunes for x265: {}".format(", ".join(x265_tunes)))
        quit()
    else:
        return


def check_valid_transpose(transpose):
    if transpose in ["", "0", "1", "2", "3", "4"]:
        return transpose
    else:
        print_error("""Valid transpose values are:
        '' – No rotation
        0  – Rotate by 90 degrees counter-clockwise and flip vertically
        1  – Rotate by 90 degrees clockwise
        2  – Rotate by 90 degrees counter-clockwise
        3  – Rotate by 90 degrees clockwise and flip vertically
        4  – Rotate by 180 degrees (not an ffmpeg option)""")
        quit()


def set_HQ_settings(args):
    # preset for higher quality, especially movies in dark szenes that suffer from too much denoising
    # x264 -crf 22 -preset veryslow -tune film
    # -tune will always be film, because the parameter is "abused" to take a custom tune and cannot be used twice
    # note: the codec can not be overridden and is always x264 when -t HQ is used
    # other parameters can be overridden by the user, e.g. --crf
    args.codec = "x264"
    args.crf = 22 if (args.crf == None or args.crf == "") else args.crf
    args.speed = "veryslow" if (args.speed == None or args.speed == "") else args.speed
    args.tune = "film"
    return args


def get_metadata(movie_path):
    """Returns metadata as a dictionary."""

    # if exists, use .thm file to extract metadata, otherwise movie directly
    movie_lst = os.path.splitext(movie_path)
    metadata_path = movie_lst[0] + ".thm"

    if not os.path.isfile(metadata_path):  #ToDo: What happens with captial .THM?
        metadata_path = movie_path

    # get metadata using exiftools
    p1 = subprocess.Popen(
        [path_exif, "-s", "-G1", "-t", "--composite", metadata_path],
        # -s -> returns tags instead of descriptions
        # --composite -> excludes "calculated tags", that may have the same name as real tags in other cameras and thus lead to mapping problems.
        # they can't be written anyway - all the information is contained in other tags.
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    # class "bytes", sequence of bytes, similar to string, but ASCII only and immutable
    metadata_str = p1.communicate()[0].decode("iso-8859-1")
    # test_list2D = tuplelist = [[4, 180, 21], [5, 90, 10], [3, 270, 8], [4, 0, 7]]
    metadata_list2D = list(item.split("\t", ) for item in metadata_str.split("\r\n")[:-1])  # last element is empty -> remove
    metadata_dict = {b: (a, c) for a, b, c in metadata_list2D}
    # {Tag:(group, value)} -> dictionary containing a tuple
    return metadata_dict


def get_original_date_and_tz_offset(metadata_dict):
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

    # parse strings and remove timezone to avoid error: TypeError("can"t compare offset-naive and offset-aware datetimes")
    dates_dict = {k: try_parse_date(v[1]) for (k, v) in metadata_dict.items()}
    dates_dict_tz_removed = {k: v.replace(tzinfo=None) for (k, v) in dates_dict.items() if v is not None}
    dates_dict_tz = {k: v for (k, v) in dates_dict.items() if v is not None if v.tzinfo is not None if v.tzinfo.utcoffset(v) is not None}

    # min_date = min({k: v.replace(tzinfo=None) for (k, v) in dates_dict_tz_removed.items() if v is not None}.values())
    original_date = None
    tz_info = None

    # get datetime
    if "CreationDate" in dates_dict:
        original_date = dates_dict_tz_removed["CreationDate"]
    elif "DateTimeOriginal" in dates_dict:
        original_date = dates_dict_tz_removed["DateTimeOriginal"]
    # elif (dates_dict_tz_removed["FileModifyDate"] - min_date).days > 30:
    #     original_date = min_date
    else:
        original_date = dates_dict_tz_removed["FileModifyDate"]

    # get timezone (which could be on an other field)
    if "CreationDate" in dates_dict_tz:
        tz_info = dates_dict_tz["CreationDate"].tzinfo
    elif "DateTimeOriginal" in dates_dict_tz:
        tz_info = dates_dict_tz["DateTimeOriginal"].tzinfo
    # elif (dates_dict_tz_removed["FileModifyDate"] - min_date).days > 30:
    #     # get timezone from any field which has the same date like the smallest date
    #     try:
    #         min({k: v for (k, v) in dates_dict_tz.items()
    #              if v.date() == min_date.date()}.values()).tzinfo
    #     except ValueError:
    #         tz_info = None
    else:
        tz_info = dates_dict_tz["FileModifyDate"].tzinfo

    if tz_info != None:
        original_date_tz = original_date.replace(tzinfo=tz_info).strftime("%Y:%m:%d %H:%M:%S%z")
        # insert the missing colon in the timezone part
        original_date_tz = original_date_tz[:-2] + ":" + original_date_tz[-2:]
    else:
        original_date_tz = original_date.strftime("%Y:%m:%d %H:%M:%S")

    return {"original_date": original_date.strftime("%Y:%m:%d %H:%M:%S"), "original_date_tz": original_date_tz}

def parse_gps_string(gps_string):
    # Convert UserData	GPSCoordinates	46 deg 30' 28.80" N, 9 deg 52' 16.32" E into standard GPS key value pairs
    # Split the input string by comma to separate latitude and longitude
    lat_str, lon_str = gps_string.split(", ")
    
    # Split each part by spaces to extract the degree, minute, and second components
    lat_parts = lat_str.split(" ")
    lon_parts = lon_str.split(" ")

    # Extracting latitude components
    latitude = f"{lat_parts[0]} {lat_parts[1]} {lat_parts[2]} {lat_parts[3]}"
    latitude_ref = lat_parts[4]  # This will be 'N' or 'S'

    # Extracting longitude components
    longitude = f"{lon_parts[0]} {lon_parts[1]} {lon_parts[2]} {lon_parts[3]}"
    longitude_ref = lon_parts[4]  # This will be 'E' or 'W'

    # Map the reference directions to full names
    latitude_ref_full = "North" if latitude_ref == 'N' else "South"
    longitude_ref_full = "East" if longitude_ref == 'E' else "West"

    return latitude, latitude_ref_full, longitude, longitude_ref_full

def parse_location_string(location_string):
    # Convert Keys:Location of the format +47.4044+8.5442/ into standart GPS key value pairs 
    # Remove trailing '/' characters
    location_string = location_string.strip('/')

    if location_string:
        # Split the string into latitude and longitude parts
        # Latitude will start with '+' or '-', and longitude will follow after the next '+' or '-'
        lat_str = location_string[1:].split('+')[0].split('-')[0]
        lon_str = location_string[len(lat_str) + 2:]  # +2 to account for the +/- sign and split
        
        # Determine the direction based on the sign
        lat_sign = location_string[0]
        lon_sign = location_string[len(lat_str) + 1]
        
        latitude_ref = 'North' if lat_sign == '+' else 'South'
        longitude_ref = 'East' if lon_sign == '+' else 'West'

        # Convert decimal degrees to degrees, minutes, seconds format
        def decimal_to_dms(degree):
            d = int(degree)
            m = int((degree - d) * 60)
            s = (degree - d - m / 60) * 3600
            return f'{d} deg {m}\' {s:.2f}"'

        # Convert latitude and longitude from decimal degrees to DMS
        latitude = decimal_to_dms(float(lat_str))
        longitude = decimal_to_dms(float(lon_str))

        return latitude, latitude_ref, longitude, longitude_ref
    else:
        return (None,) * 4

def compress_movie(movie_path, clip_from=None, clip_to=None, codec="x265", crf="", speed="", tune="", transpose="", stabilize=False):
    """Compress movie with x265, crf 25 slow (default) or x264 crf 24 verylow if 'codec' x264 is used. 'crf' and 'speed' can also be set manually."""

    # parse clipping information
    ss_ = "" if clip_from == None or clip_from == "" else (" -ss " + clip_from)
    if clip_to != None and clip_to != "":
        t1 = try_parse_time(("00:00:00" if clip_from == None else clip_from))
        t2 = try_parse_time(clip_to)
        delta = t2 - t1
        t_ = " -t " + '{:d}.{:d}'.format(delta.seconds, int(delta.microseconds / 1000))  # -> see https://pyformat.info/#string_truncating
    # int(/1000) to only return .600 intead of .600000
    else:
        t_ = ""

    codec_ = "libx265" if codec.lower() == "x265" else "libx264" if codec.lower() == "x264" else codec
    crf_ = str(crf) if str(crf) != "" and crf != None else "25" if codec == "x265" else "24"
    # 24 best for x264, 25 equal quality for x265
    preset_ = (" -preset " + speed) if str(speed) != "" and speed != None else " -preset veryslow" if codec == "x264" else " -preset slow"
    tune_ = (" -tune " + tune) if str(tune) != "" and tune != None else ""
    transpose_ = ""
    if str(transpose) == "":
        pass
    elif str(transpose) != "4":
        transpose_ = ' -vf "transpose={}"'.format(transpose)
    elif str(transpose) == "4":
        transpose_ = ' -vf "transpose=2,transpose=2"'

    movie_lst = os.path.splitext(movie_path)
    analyzed_video_path = os.path.dirname(movie_path) + "\\analyzed_video.MP4"  # declared here so that it can be used for deletion after encoding
    transforms_path = os.getcwd() + "\\transforms.trf"  # when started from the

    # writing with exiftool to mkv or avi is not yet supported -> convert to MP4
    movie_cmp = movie_lst[0] + codec.lower() + (movie_lst[1].upper()
                                                if movie_lst[1].upper() not in [".AVI", ".MKV", ".MPG", ".MPEG", ".WMV"] else ".MP4")

    # manual override to brighten a movie, ToDo: implement as additional parameter
    # -----------------------------------
    # command = '''{0}{1} -i "{2}"{3} -c:v {4} -crf {5}{6}{7}{8} -vf "curves=master='0/0.1 0.1/0.6 0.3/0.9 0.7/1', eq=saturation=0.8, hqdn3d=8:8:20:20" -map_metadata 0 "{9}"'''.format(path_ffmpeg, ss_, movie_path, t_, codec_, crf_, preset_,
    #                                                                                       tune_, transpose_, movie_cmp)

    # rescale
    # -------
    # https://superuser.com/questions/624563/how-to-resize-a-video-to-make-it-smaller-with-ffmpeg
    # command = '{0}{1} -i "{2}"{3} -s 640x360 -c:v {4} -crf {5}{6}{7}{8} {9} -map_metadata 0 "{10}"'.format(path_ffmpeg, ss_, movie_path, t_, codec_, crf_,
    #                                                                                             preset_, tune_, transpose_, stabilize_, movie_cmp)

    # crop
    # ----
    # https://video.stackexchange.com/questions/4563/how-can-i-crop-a-video-with-ffmpeg
    # command = '''{0}{1} -i "{2}"{3} -c:v {4} -crf {5}{6}{7}{8} -vf "crop=1440:810:240:135" -map_metadata 0 "{9}"'''.format(path_ffmpeg, ss_, movie_path, t_, codec_, crf_, preset_,
    #                                                                                       tune_, transpose_, movie_cmp)

    # increase audio volume, noise reduction and convert to mono (-ac 1)  (don't use noise reduction unless necessary, it causes the voice to sound dull.)
    # ------------------------------------------------------------------
    # https://trac.ffmpeg.org/wiki/AudioVolume     (use volume=6 for PowerPoint-Videos by K.)
    # command = '{0}{1} -i "{2}"{3} -c:v {4} -crf {5}{6}{7}{8} {9} -af "volume=6, highpass=f=200, lowpass=f=3000" -ac 1 -map_metadata 0 "{10}"'.format(path_ffmpeg, ss_, movie_path, t_, codec_, crf_,
    #                                                                                            preset_, tune_, transpose_, stabilize_, movie_cmp)

    # fade in volume and audio (3 sec)
    # --------------------------------
    # https://dev.to/dak425/add-fade-in-and-fade-out-effects-with-ffmpeg-2bj7

    # command = '{0}{1} -i "{2}"{3} -c:v {4} -crf {5}{6}{7}{8} {9} -af "afade=t=in:st=0:d=3" -map_metadata 0 "{10}"'.format(path_ffmpeg, ss_, movie_path, t_, codec_, crf_,
    #                                                                                           preset_, tune_, transpose_, '-vf "fade=t=in:st=0:d=3"', movie_cmp)

    stabilize_ = ""
    if stabilize:
        command_preproc = '{0} -i "{1}" -vf vidstabdetect=stepsize=6:shakiness=7:accuracy=15:show=1 "{2}"'.format(
            path_ffmpeg, movie_path, analyzed_video_path)
        subprocess.check_call(command_preproc)  # generate "analyzed_video.mp4" for movie to be processed
        stabilize_args = 'vidstabtransform,unsharp=5:5:0.8:3:3:0.4'
        if transpose_ != "":
            transpose_ = ' -vf "{0},{1}'.format(
                stabilize_args,
                transpose_[6:])  # add the vidstab arguments in front of the already existing -vf transpose arguments. Vidstab MUST be first!
        else:
            stabilize_ = ' -vf "{}"'.format(stabilize_args)

    # main encoding step
    # ------------------
    command = '{0}{1} -i "{2}"{3} -c:v {4} -crf {5}{6}{7}{8} {9} -map_metadata 0 "{10}"'.format(path_ffmpeg, ss_, movie_path, t_, codec_, crf_,
                                                                                                preset_, tune_, transpose_, stabilize_, movie_cmp)

    # -i              -> input file(s)
    # -c:v            -> select video encoder
    # -c:a            -> select audio encoder (skipping this will simply copy the audio stream without reencoding)
    # -crf            -> Change the CRF value for video. Lower means better quality. 23 is default, and anything below 18 will probably be visually lossless
    # -preset slower  -> slower settings have better quality:compression ratios. Each step about doubles the processing time!
    # -map_metadata 0 -> Map the metadata from file 0 to the output
    # -ss 00:01:00 before -i -> fast seek, start of cut
    # -to 00:02:00 with -copyts -> cut till time in original movie
    # -copyts         -> makes -to correspond to time in original movie, without it, the reference would be the new start defined by -ss
    #                    (-ss + -to would would correspond to the end cut of the original movie)
    #                    Note: Works as indicated, but leads to wrong times being shown in VLC: e.g. if the original movie was cut from 2 to 4 sec,
    #                    VLC will start showing 0 sec and end showing 4 sec, while actually only sec were played
    #                    Omitting -copyts solves this problem, but requires calculation of the proper -to parameter:
    #                    -to = desired -to minus -ss
    # -vf             -> various video filters (e.g. transpose, vistab, unsharp)
    # https://trac.ffmpeg.org/wiki/Encode/H.264
    # http://trac.ffmpeg.org/wiki/Encode/AAC
    # http://ffmpeg.org/ffmpeg-all.html
    # https://superuser.com/questions/138331/using-ffmpeg-to-cut-up-video
    print_info("ffmpeg command: {}".format(command))
    subprocess.check_call(command)

    if stabilize:
        try:
            os.remove(analyzed_video_path)
        except Exception as err:
            print_error("Could not remove {0} due to the following error:\r\n{1}.\r\nClean up manually if necessary.".format(
                analyzed_video_path, err))
        try:
            os.remove(transforms_path)
        except Exception as err:
            print_error("Could not remove {0} due to the following error:\r\n{1}.\r\nClean up manually if necessary.".format(transforms_path, err))
    return {"movie_path_out": movie_cmp, "codec": codec.upper()}


def set_metadata(movie_path, metadata_dict):
    """ Restores make/model information. (Currently not possible for most of the cases in movies)"""

    metadata_to_use_dict = {
        "AccelerometerX": "",
        "AccelerometerY": "",
        "AccelerometerZ": "",
        "AccessorySerialNumber": "",
        "AccessoryType": "",
        "AdvancedSceneMode": "",
        "AdvancedSceneType": "",
        "AESetting": "",
        "AFAreaMode": "",
        "AFPoint": "",
        # "Aperture": "", # not writeable, but transferred by FFMPEG
        "AndroidCaptureFPS": "",
        #"AndroidManufacturer": "", # not writable, convert to UserData
        #"AndroidModel": "", # not writable, convert to UserData
        "AndroidVersion": "",
        "ApertureValue": "",
        "AspectRatio": "",
        "Audio": "",
        # "AudioAvgBitrate  ": "", # depending on the format, audio is reencoded. Those values would no longer be correct.
        # "AudioBitrate": "",
        "AutoISO": "",
        "AutoRotate": "",
        "Author": "",
        "AvgBytesPerSec": "",
        "BitsPerSample": "",
        "BlueBalance": "",
        "BMPVersion": "",
        "CameraISO": "",
        "CameraOrientation": "",
        "CameraTemperature": "",
        "CameraType": "",
        "CanonExposureMode": "",
        "CanonFirmwareVersion": "",
        "CanonImageSize": "",
        "CanonImageType": "",
        "CanonModelID": "",
        "CircleOfConfusion": "",
        "CleanApertureDimensions": "",
        "ClearRetouch": "",
        "ClearRetouchValue": "",
        #"ColorComponents": "", # not writeable
        "ColorEffect": "",
        #"ColorRepresentation": "", # Can't convert IPTC:ColorRepresentation (not in PrintConv): 'nclx 1 1 1'  (does not exist in database)
        "ColorSpace": "",
        "ColorTempKelvin": "",
        "ComAndroidVersion": "",
        "ComApplePhotosOriginatingSignatur": "",
        "ContinuousDrive": "",
        "Contrast": "",
        "ContrastMode": "",
        "ControlMode": "",
        "ConversionLens": "",
        "DiffractionCorrection": "",
        "DigitalZoom": "",
        "DigitalZoomRatio": "",
        "DOF": "",
        "DriveMode": "",
        "Encoder": "",
        "ExifImageHeight": "",
        "ExifImageWidth": "",
        "ExposureCompensation": "",
        "ExposureMode": "",
        "ExposureProgram": "",
        "ExposureTime": "",
        "FileSource": "",
        "FirmwareRevision": "",
        "FirmwareVersion": "",
        "FNumber": "",
        "FocalLength": "",
        # "FocalLength35efl": "", # not writeable, but transferred by FFMPEG
        "FocalLengthIn35mmFormat": "",
        "FocalPlaneResolutionUnit": "",
        "FocalPlaneXResolution": "",
        "FocalPlaneXSize": "",
        "FocalPlaneYResolution": "",
        "FocalPlaneYSize": "",
        "FocalType": "",
        "FocalUnits": "",
        "FocusContinuous": "",
        "FocusDistanceLower": "",
        "FocusDistanceUpper": "",
        "FocusMode": "",
        "FocusRange": "",
        "Format": "",
        "FOV": "",
        "FrameCount": "",
        "GainControl": "",
        "GenBalance": "",
        "GenFlags": "",
        "GenGraphicsMode": "",
        "GenMediaVersion": "",
        "GenOpColor": "",
        "GPSAltitude": "",
        "GPSAltitudeRef": "",
        "GPSCoordinates": "",
        "GPSLatitude": "",
        "GPSLongitude": "",
        "GPSPosition": "",
        "HDR": "",
        "HDRShot": "",
        "HyperfocalDistance": "",
        "ImageQuality": "",
        "ImageStabilization": "",
        "ImageUniqueID": "",
        # "Information": "", # not writeable
        "IntelligentContrast": "",
        "IntelligentD-Range": "",
        "IntelligentResolution": "",
        "InternalNDFilter": "",
        "InternalSerialNumber": "",
        "ISO": "",
        #"LayoutFlags": "", # not writeable, transferred by FFMPEG
        "Lens": "",
        #"Lens35efl": "", # not writeable
        "LensID": "",
        "LensSerialNumber": "",
        "LensType": "",
        "LightSource": "",
        "LightValue": "",
        # "Location": "", # not writeable, but transformed to Longitude / Latitude in my code
        # "Location-eng": "", # not writeable
        "LocationInformation": "",
        "LongExposureNoiseReduction": "",
        "MacroMode": "",
        "Make": "",
        "MakerNoteVersion": "",
        "MaxAperture": "",
        "MaxApertureValue": "",
        "MaxFocalLength": "",  # not set, bug in EXIFTOOL or possible not writeable (silently)
        "MeasuredEV": "",
        # "MediaTimeScale": "", # not writeable, recalculated
        "MeteringMode": "",
        "MinAperture": "",
        "MinFocalLength": "",  # not set, bug in EXIFTOOL or possible not writeable (silently)
        "Model": "",
        "MyColorMode": "",
        "NDFilter": "",
        "NoiseReduction": "",
        "NumAFPoints": "",
        "NumChannels": "",
        "NumColors": "",
        "NumImportantColors": "",
        "OpticalZoomCode": "",
        "OpticalZoomMode": "",
        "Orientation": "",
        "PhotoStyle": "",
        "PitchAngle": "",
        "ProgramISO": "",
        "Quality": "",
        "RedBalance": "",
        "RollAngle": "",
        "Rotation": "",
        #"SamsungModel": "", # not writable, convert to UserData
        "Saturation": "",
        "ScaleFactor35efl": "",
        "SceneCaptureType": "",
        "SceneMode": "",
        "SceneType": "",
        "SensingMethod": "",
        "SensitivityType": "",
        "Sharpness": "",
        "ShootingMode": "",
        #"ShutterSpeed": "", # not writeable, transferred by FFMPEG
        "ShutterSpeedValue": "",
        "ShutterType": "",
        "SlowShutter": "",
        "Software": "",
        "SpotMeteringMode": "",
        "TargetAperture": "",
        "TargetExposureTime": "",
        "TimeLapseShotNumber": "",
        # "TimeScale": "", # not writeable, recalculated
        "TimeSincePowerOn": "",
        "TouchAE": "",
        "Vendor": "",
        # "VendorID": "", # not writeable. Not so nice: Camera brand replaced by FFMPEG :(
        "WBBlueLevel": "",
        "WBGreenLevel": "",
        "WBRedLevel": "",
        "WBShiftAB": "",
        "WBShiftCreativeControl": "",
        "WBShiftGM": "",
        "WBShiftIntelligentAuto": "",
        "WhiteBalance": "",
        "WorldTimeLocation": "",
        "YCbCrPositioning": "",
        "YCbCrSubSampling": ""
    }

    # generate GPS key value pairs based on GPSCoordinates UserData, will be written to XMP-exif
    if "GPSCoordinates" in metadata_dict and "GPSLatitude" not in metadata_dict:
        latitude, latitude_ref, longitude, longitude_ref = parse_gps_string(metadata_dict["GPSCoordinates"][1])
        metadata_dict["GPSLatitude"] = ('GPS', latitude)
        metadata_dict["GPSLatitudeRef"] = ('GPS', latitude_ref)
        metadata_dict["GPSLongitude"] = ('GPS', longitude)
        metadata_dict["GPSLongitudeRef"] = ('GPS', longitude_ref)
    
    # generate GPS key value pairs based on Keys:Location will be written to XMP-exif
    if "Location" in metadata_dict and metadata_dict["Location"][1] != '':
        latitude, latitude_ref, longitude, longitude_ref = parse_location_string(metadata_dict["Location"][1])
        if not any(var is None for var in [latitude, longitude]):
            metadata_dict["GPSLatitude"] = ('GPS', latitude)
            metadata_dict["GPSLatitudeRef"] = ('GPS', latitude_ref)
            metadata_dict["GPSLongitude"] = ('GPS', longitude)
            metadata_dict["GPSLongitudeRef"] = ('GPS', longitude_ref)
            if "GPSCoordinates" not in metadata_dict:
                metadata_dict["GPSCoordinates"] = ('UserData', latitude + " " + latitude_ref[0] + ", " + longitude + " " + longitude_ref[0])

    # transform Keys:Location into a writable format (setting the escape characters differently)
    if "GPSCoordinates" in metadata_dict and metadata_dict["GPSCoordinates"][1] != '':
        metadata_dict["GPSCoordinates"] = ('UserData', metadata_dict["GPSCoordinates"][1].replace(r"\'", "'").replace('"', r'\"'))

   
    # replacement dict to map tag values unknown in the exiftool database to known values
    metadata_to_replace_dict = {"MeteringMode": ["Evaluative", "Multi-segment"]}  #ToDo: add group

    # copy some unwritable Android and Samsung Keys important to determine the make to UserData
    if "AndroidManufacturer" in metadata_dict:
        metadata_dict["Make"] = ("UserData", metadata_dict["AndroidManufacturer"][1])
    if "AndroidModel" in metadata_dict:
        metadata_dict["Model"] = ("UserData", metadata_dict["AndroidModel"][1])
    if "SamsungModel" in metadata_dict:
        metadata_dict["Make"] = ("UserData", "samsung") # Samsung uses lowercase for the make in images
        metadata_dict["Model"] = ("UserData", metadata_dict["SamsungModel"][1])

    # list to join to create the final command string in the end
    stringbuilder = [path_exif]

    # dictionary of tags that are supposed to be written
    metadata_target_dict: {str, str} = {}
    match_cnt = 0

    for key in metadata_to_use_dict:
        if (key in metadata_dict):
            if (key in metadata_to_replace_dict) and metadata_dict[key] == metadata_to_replace_dict[key][0]:
                stringbuilder.append("-" + key + '="' + metadata_to_replace_dict[key][1] + '"')
                metadata_target_dict[key] = metadata_to_replace_dict[key][1]
            else:
                stringbuilder.append("-" + metadata_dict[key][0] + ":" + key + '="' + metadata_dict[key][1] + '"')
                # -group:key=value
                metadata_target_dict[key] = metadata_dict[key][1]
            match_cnt += 1

    if match_cnt == 0:
        print_info("No metadata found other than dates ...")
        return  # returns None and exits the function

    # prevents creation of _original file
    stringbuilder.append("-overwrite_original")
    stringbuilder.append('"' + movie_path + '"')
    # note: the space in " " is actually the seperator!
    command = " ".join(stringbuilder)
    print_info("Trying to write makershift tags with groups ...")
    try:
        subprocess.check_call(command)  # throws error if only one tag shall be written but is write protected. No reason to abort.
    # Improve: Replace check_call with subprocess.Popen to capture the output message and check for "Warning" and "Nothing to do".
    except subprocess.CalledProcessError as e:
        if e.output == None:
            pass
        else:
            raise
    return metadata_target_dict


def verify_written_metadata(metadata_target_dict, metadata_written_dict):
    if metadata_target_dict == None:
        return

    metadata_missing_dict = {k: v for (k, v) in metadata_target_dict.items() - [(a, c) for a, (b, c) in metadata_written_dict.items()]}
    # (a,c) for a, (b,c) -> convert (key, (group, value)) to (key, value)

    # print(len(metadata_target_dict))
    # print(len(metadata_written_dict))
    # print(len(metadata_missing_dict))
    return metadata_missing_dict


def set_metadata_without_group(movie_path, metadata_missing_dict):
    if metadata_missing_dict == None:
        return

    stringbuilder = [path_exif]
    stringbuilder.append(" -" + " -".join('{}="{}"'.format(k, v) for (k, v) in metadata_missing_dict.items()))
    # Returns a generator object which is then joined.
    # see https://codereview.stackexchange.com/questions/7953/flattening-a-dictionary-into-a-string/7954
    # {!r} would return single quotes, we need double quotes -> default !s (empty {}) used and surrounded in ""

    # prevents creation of _original file
    stringbuilder.append("-overwrite_original")
    stringbuilder.append('"' + movie_path + '"')
    # note: the space in " " is actually the seperator!
    command = " ".join(stringbuilder)
    print_info("Trying to write makershift tags without groups ...")
    try:
        subprocess.check_call(command)  # throws error if only one tag shall be written but is write protected. No reason to abort.
    # Improve: Replace check_call with subprocess.Popen to capture the output message and check for "Warning" and "Nothing to do".
    except subprocess.CalledProcessError as e:
        if e.output == None:
            pass
        else:
            raise


def set_metadata_dates(movie_path, metadata_missing_dict, original_date_dict):
    """"Sets most dates to the file modification date of the original movie. Must be set at the end, otherwise FileModifyDate maybe reset to today"""

    stringbuilder = ["exiftool"]
    original_date = original_date_dict["original_date"]  # w/o timezone
    original_date_tz = original_date_dict["original_date_tz"]  # w/ timezone

    metadata_predef_dict = {
        "DateTimeOriginal": original_date,
        "FileModifyDate": original_date,
        "FileCreateDate": original_date,
        "CreationDate": original_date,
        "MediaCreateDate": original_date_tz,
        "MediaModifyDate": original_date_tz,
        # "CreateDate": original_date_tz, # Wird in Windows immer um 1-2 h verschoben als "Datum" und "Medium erstellt" angezeigt, unabhängig von dem TZ-Shift
        # Ohne diesen Tag wird das "Datum" basierend auf einem andern Tag korrekt angezeigt.
        "ModifyDate": original_date_tz,
        "TrackCreateDate": original_date_tz,
        "TrackModifyDate": original_date_tz
        # "CompressorName": video_codec,  # not writeable, but correctly set
    }

    for key, value in metadata_predef_dict.items():
        if value > "":  # should always be the case
            stringbuilder.append("-" + key + '="' + value + '"')

    stringbuilder.append("-overwrite_original")
    stringbuilder.append('"' + movie_path + '"')
    command = " ".join(stringbuilder)
    print_info(Fore.YELLOW + "Writing date tags ...")
    subprocess.check_call(command)


def process_movie(movie_path, clip_from, clip_to, codec, crf, speed, tune, transpose, stabilize, transfer_metadata, target_path):  # clip_from = "00:00:04", clip_to= "00:00:06"

    # movie_path_in: str
    movie_path_out: str = ""
    # video_codec: str = ""

    metadata_dict = get_metadata(movie_path)
    original_date_dict = get_original_date_and_tz_offset(metadata_dict)
    if not transfer_metadata:
        compression_output_dict = compress_movie(movie_path, clip_from, clip_to, codec, crf, speed, tune, transpose, stabilize)
    movie_path_out = target_path if transfer_metadata else compression_output_dict["movie_path_out"]
    # movie_path_out, video_codec = compression_output_dict["movie_path_out"], compression_output_dict["codec"]
    metadata_target_dict = set_metadata(movie_path_out, metadata_dict)
    metadata_written_dict = get_metadata(movie_path_out)
    metadata_missing_dict = verify_written_metadata(metadata_target_dict, metadata_written_dict)
    set_metadata_without_group(movie_path_out, metadata_missing_dict)
    set_metadata_dates(movie_path_out, metadata_dict, original_date_dict)  # must be set at the end to avoid setting the FileModifyDate to today


def process_movies(
    movie_path, clip_from=None, clip_to=None, codec="x265", crf="", speed="", tune="", transpose="", stabilize=False, transfer_metadata=False, target_path=""):  # clip_from = "00:00:04", clip_to= "00:00:06"
    """movie path is file: compresses the single movie and adds as much metadata from the original as possible\r\n
    movie path is directory: compresses all movies in the directory and adds as much metadata from the originals as possible"""

    suffix = ("x264", "x265")  # to check for already processed movies, used by endswith()

    if transfer_metadata:
        # if target_path is not a full path, combine it with the directory from movie_path
        if(os.path.isfile(movie_path) and not os.path.isabs(target_path)):
            # Combine with the directory part of movie_path
            movie_directory = os.path.dirname(movie_path)
            target_path = os.path.join(movie_directory, target_path)

        if (
            os.path.isfile(movie_path)
            and os.path.splitext(movie_path)[1].upper() in [".MOV", ".MKV", ".MP4", ".AVI", ".MPG", ".MPEG", ".WMV"]
            and os.path.isfile(target_path)
            and os.path.splitext(target_path)[1].upper() in [".MOV", ".MKV", ".MP4", ".AVI", ".MPG", ".MPEG", ".WMV"]
        ):
            print_info('\nAbout to transfer metadata from movie\n"{}" to \n"{}"'.format(movie_path, target_path))
            inp = input_color("\nProceed (y/n)? ")

            if inp == "y":
                print_info("Transferring ...")
                process_movie(movie_path, clip_from, clip_to, codec, crf, speed, tune, transpose, stabilize, transfer_metadata, target_path)
            else:
                print_info("Quitting...\n")
                quit()
        else:
            print_error("\nFile or target file not recognized as movie (.MOV, .MKV, .MP4, .AVI, .MPG, .MPEG, .WMV).\nQuitting...")
            quit()

    elif os.path.isdir(movie_path):
        movies_lst: [str] = []
        for file in os.listdir(movie_path):
            file_lst = os.path.splitext(file)
            if file_lst[1].upper() in [".MOV", ".MKV", ".MP4", ".AVI", ".MPG", ".MPEG", ".WMV"] and not file_lst[0].lower().endswith(suffix):
                movies_lst.append(file)

        if len(movies_lst) == 0:
            print_error("\nNo movies found in directory.\nQuitting...")
            quit()
        else:
            print_info("\nThe following movies were found:\n")
            print_info("\n".join(movies_lst))
            inp = input_color("\nProceed (y/n)? ")

            if inp == "y":
                for movie in movies_lst:
                    print_info("Processing {} ...".format(movie))
                    process_movie(os.path.join(movie_path, movie), clip_from, clip_to, codec, crf, speed, tune, transpose, stabilize, transfer_metadata, target_path)
            else:
                print_info("Quitting...\n")
                quit()

    elif (
        os.path.isfile(movie_path)
        and os.path.splitext(movie_path)[1].upper() in [".MOV", ".MKV", ".MP4", ".AVI", ".MPG", ".MPEG", ".WMV"]
        and not os.path.splitext(movie_path)[0].lower().endswith(suffix)
    ):
        print_info('\nAbout to process movie\n"{}"'.format(movie_path))
        inp = input_color("\nProceed (y/n)? ")

        if inp == "y":
            print_info("Processing ...")
            process_movie(movie_path, clip_from, clip_to, codec, crf, speed, tune, transpose, stabilize, transfer_metadata, target_path)
        else:
            print_info("Quitting...\n")
            quit()

    else:
        print_error("\nFile not recognized as movie (.MOV, .MKV, .MP4, .AVI, .MPG, .MPEG, .WMV).\nQuitting...")
        quit()


# ---- Procedural Code ---- #
# print ("current directory: {}".format(os.getcwd()))
# change the working directory to the directory of the script (as opposed to that of the movie) to be able to load the config file:
# os.chdir(os.path.dirname(sys.argv[0]))
# it's better to keep the movie path in order to address individual movies. Pass the full program path to config.yml instead:

# Load the configuration file
with open(os.path.dirname(sys.argv[0]) + "\\config.yml", 'r') as ymlfile:  # os.path.dirname(sys.argv[0]) -> path where the python script lives
    cfg = yaml.safe_load(ymlfile)

path_exif = check_valid_path(cfg['paths']['exif'], "Please check the config file (config.yml) and install exiftool if necessary.")
path_ffmpeg = check_valid_path(cfg['paths']['ffmpeg'], "Please check the config file (config.yml) and install ffmpeg if necessary.")

# Handling the command line arguments
parser = argparse.ArgumentParser(description="Compress a specific movie or all movies in a directory", formatter_class=SmartFormatter)
parser.add_argument("path", type=check_valid_path, help="Path to the movie or a directory containing movies")
parser.add_argument("--clip_from", type=check_valid_time, help="Start time from which the movie is to be copied [format 00:00:00 or 00:00:00.0]")
parser.add_argument("--clip_to", type=check_valid_time, help="End time up to which the movie is to be copied [format 00:00:00 or 00:00:00.0]")
parser.add_argument("-c", "--codec", choices=["x265", "x264"], default="x265", help="Codec to be used for encoding")
parser.add_argument("--crf", type=int, help="Constant Rate Factor to be used. By default (empty) 25 is used for x265 and 24 for x264")
parser.add_argument(
    "-s",
    "--speed",
    choices=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
    default="",
    help="Encoding preset to be used. By default (empty) 'slow' is used for x265 and 'veryslow' for x264")
parser.add_argument(
    "-t",
    "--tune",
    ##   type=check_valid_tune,    not required, check done implicitly
    choices=["film", "animation", "grain", "stillimage", "fastdecode", "zerolatency", "psnr", "ssim", "HQ"],
    default="",
    help="Set tune option (different options for x264 and x265). Empty by default.")
parser.add_argument(
    "-r",
    "--transpose",
    type=check_valid_transpose,
    choices=["0", "1", "2", "3", "4"],
    default="",
    help="""R|Set transpose/rotation option (ffmpeg):
    0 – Rotate by 90 degrees counter-clockwise and flip vertically
    1 – Rotate by 90 degrees clockwise
    2 – Rotate by 90 degrees counter-clockwise
    3 – Rotate by 90 degrees clockwise and flip vertically
    4 – Rotate by 180 degrees (not an ffmpeg option)""")
parser.add_argument(
    "-z",
    "--stabilize",
    action="store_true",
    help="Flag to activate stabilization (deshaking). -z/--stabilize: stabilization on. If nothing is passed, stabilization is off.",
)
parser.add_argument(
    "-m", "--transfer_metadata", action="store_true", help="Flag to transfer metadata from the the source movie (path) to a target movie (target_path)."
)
# parser.add_argument("--target_path", type=check_valid_path, help="Path to the movie to which metadata from the source movie (path) shall be transferred. Only relevant if -m is set.")
parser.add_argument("--target_path", help="Path to the movie to which metadata from the source movie (path) shall be transferred. Only relevant if -m is set.")

args = parser.parse_args()
# Debugging
# args = parser.parse_args(["f:\\Libraries\\Pesche\\Pictures\\Digicams\\2024\\Test\\MicroTest\\", "-s", "veryfast", "-c", "x264"])#, "-r0", "-z"])

print("Arguments: {}".format(args))

check_valid_tune(args.codec, args.tune)

if args.tune == "HQ":
    args = set_HQ_settings(args)

process_movies(args.path, args.clip_from, args.clip_to, args.codec, args.crf, args.speed, args.tune, args.transpose, args.stabilize, args.transfer_metadata, args.target_path)

# print(results)

# input_path = r"f:\TestMovies\FolderTest"
# process_movies(input_path)

# input("Press Enter to exit...")
