import subprocess
import os
from datetime import datetime, timezone  # , timedelta

movie_path_in: str = r"f:\TestMovies\CameraTest\CanonG12\MVI_4929.MOV"
movie_path_out: str = ""
video_codec: str = ""

# More info on Exif Tags: https://www.sno.phy.queensu.ca/~phil/exiftool/TagNames/
# ToDo: Folder or File as Input Paramter. If Folder is passed: process all movie files, otherwise only single movie
# IDEA: (Optional) as default: use folder from which script is called
# IDEA: Implement some kind of progress bar, at least when looping through file list
# DONE: Erstellen von _original unterdrücken


def get_metadata(movie_path):
    """Returns metadata as a dictionary."""

    # if exists, use .thm file to extract metadata, otherwise movie directly
    movie_lst = os.path.splitext(movie_path)
    metadata_path = movie_lst[0] + ".thm"

    if not os.path.isfile(metadata_path):
        metadata_path = movie_path

    # get metadata using exiftools (needs to be installed and available in %path%)
    p1 = subprocess.Popen(
        ["exiftool", "-s", "-G1", "-t", "--composite", metadata_path],
        # -s -> returns tags instead of descriptions
        # --composite -> excludes "calculated tags", that may have the same name as real tags in other cameras and thus lead to mapping problems.
        # they can't be written anyway - all the information is contained in other tags.
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    # class "bytes", sequence of bytes, similar to string, but ASCII only and immutable
    metadata_str = p1.communicate()[0].decode("utf-8")
    test_list2D = tuplelist = [[4, 180, 21], [5, 90, 10], [3, 270, 8], [4, 0, 7]]
    metadata_list2D = list(item.split("\t", ) for item in metadata_str.split("\r\n")[:-1])  # last element is empty -> remove
    metadata_dict = {b: (a, c) for a, b, c in metadata_list2D}
    # {Tag:(group, value)} -> dictionary containing a tuple
    return metadata_dict


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

    min_date = min({k: v.replace(tzinfo=None) for (k, v) in dates_dict_tz_removed.items() if v is not None}.values())
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


def compress_movie(movie_path, codec="x265", crf="", speed=""):
    """Compress movie with x265, crf 26 slow (default) or x264 crf 25 verylow if 'codec' x264 is used. 'crf' and 'speed' can also be set manually."""
    codec_ = "libx265" if codec.lower() == "x265" else "libx264" if codec.lower() == "x264" else codec
    crf_ = str(crf) if str(crf) != "" and crf != None else "26" if codec == "x265" else "25"
    # 25 best for x264, 26 equal quality for x265
    preset_ = (" -preset " + speed) if str(speed) != "" and speed != None else " -preset veryslow" if codec == "x264" else " -preset slow"
    movie_lst = os.path.splitext(movie_path)
    movie_cmp = movie_lst[0] + "c" + movie_lst[1]  #".MP4" #movie_lst[1]
    command = 'ffmpeg -i "{0}" -c:v {1} -crf {2}{3} -map_metadata 0 "{4}"'.format(movie_path, codec_, crf_, preset_, movie_cmp)
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
    return {"movie_path_out": movie_cmp, "codec": codec.upper()}


def set_metadata(movie_path, metadata_dict, original_date_dict):
    """Sets most dates to the file modification date of the original movie and restores make/model information."""

    original_date = original_date_dict["original_date"]  # w/ timezone
    original_date_tz = original_date_dict["original_date_tz"]  # w/o timezone

    metadata_predef_dict = {
        "DateTimeOriginal": original_date,
        "FileModifyDate": original_date,
        "FileCreateDate": original_date,
        "CreationDate": original_date,
        "MediaCreateDate": original_date_tz,
        "MediaModifyDate": original_date_tz,
        "CreateDate": original_date_tz,
        "ModifyDate": original_date_tz,
        "TrackCreateDate": original_date_tz,
        "TrackModifyDate": original_date_tz
        # "CompressorName": video_codec,  # not writeable, but correctly set
    }

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
        "ApertureValue": "",
        "AspectRatio": "",
        "Audio": "",
        # "AudioAvgBitrate  ": "", # depending on the format, audio is reencoded. Those values would no longer be correct.
        # "AudioBitrate": "",
        "AutoISO": "",
        "AutoRotate": "",
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
        # ToDo Not a floating point number for ExifIFD:FocalLength
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

    # replacement dict to map tag values unknown in the exiftool database to known values
    metadata_to_replace_dict = {"MeteringMode": ["Evaluative", "Multi-segment"]}  #ToDo: add group

    # list to join to create the final command string in the end
    stringbuilder = ["exiftool"]

    # dictionary of tags that are supposed to be written
    metadata_target_dict: {str, str} = {}

    for key, value in metadata_predef_dict.items():
        if value > "":  # should always be the case
            stringbuilder.append("-" + key + '="' + value + '"')
            metadata_target_dict[key] = value

    for key, value in metadata_to_use_dict.items():
        if (key in metadata_dict):
            if (key in metadata_to_replace_dict) and metadata_dict[key] == metadata_to_replace_dict[key][0]:
                stringbuilder.append("-" + key + '="' + metadata_to_replace_dict[key][1] + '"')
                metadata_target_dict[key] = metadata_to_replace_dict[key][1]
            else:
                stringbuilder.append("-" + metadata_dict[key][0] + ":" + key + '="' + metadata_dict[key][1] + '"')
                # -group:key=value
                metadata_target_dict[key] = metadata_dict[key][1]

    # prevents creation of _original file
    stringbuilder.append("-overwrite_original")
    stringbuilder.append('"' + movie_path + '"')
    # note: the space in " " is actually the seperator!
    command = " ".join(stringbuilder)
    subprocess.check_call(command)
    return metadata_target_dict


def verify_written_metadata(metadata_target_dict, metadata_written_dict):
    metadata_missing_dict = {k: v for (k, v) in metadata_target_dict.items() - [(a, c) for a, (b, c) in metadata_written_dict.items()]}
    # (a,c) for a, (b,c) -> convert (key, (group, value)) to (key, value)

    # print(len(metadata_target_dict))
    # print(len(metadata_written_dict))
    # print(len(metadata_missing_dict))
    return metadata_missing_dict


def set_metadata_without_group(movie_path, metadata_missing_dict):
    stringbuilder = ["exiftool"]
    stringbuilder.append(" -" + " -".join('{}="{}"'.format(k, v) for (k, v) in metadata_missing_dict.items()))
    # Returns a generator object which is then joined.
    # see https://codereview.stackexchange.com/questions/7953/flattening-a-dictionary-into-a-string/7954
    # {!r} would return single quotes, we need double quotes -> default !s (empty {}) used and surrounded in ""

    # prevents creation of _original file
    stringbuilder.append("-overwrite_original")
    stringbuilder.append('"' + movie_path + '"')
    # note: the space in " " is actually the seperator!
    command = " ".join(stringbuilder)
    subprocess.check_call(command)


metadata_dict = get_metadata(movie_path_in)
original_date_dict = get_original_date_and_tz_offset(metadata_dict)
compression_output_dict = compress_movie(movie_path_in)
movie_path_out, video_codec = compression_output_dict["movie_path_out"], compression_output_dict["codec"]
#movie_path_out = r"f:\TestMovies\CameraTest\CanonG12\MVI_4929c.MOV"
metadata_target_dict = set_metadata(movie_path_out, metadata_dict, original_date_dict)
metadata_written_dict = get_metadata(movie_path_out)
metadata_missing_dict = verify_written_metadata(metadata_target_dict, metadata_written_dict)
set_metadata_without_group(movie_path_out, metadata_missing_dict)

input("Press Enter to exit...")