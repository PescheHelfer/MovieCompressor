• The only way to preserve the timestamps from iPhone movies is to download them via Windows Foto
• Coping a file using windows explorer overwrites the creation date (Erstelldatum), the modification date (Geändert) remains untouched
• Using TeraCopy does maintains the creation date (Erstelldatum)
• The metadata "Medium erstellt" seems to correspond to the Date ("Datum")
  It is better preserved than the creation date (Erstelldatum), but not as reliable as the modification date
  
--> Use Windows Fotos to download the movies
--> Use TeraCopy to move/copy the movies
--> Use the smallest of all the dates as the "correct" date and apply it to all others

NB: RoboCopy also offers the option to maintain the date, if this has to be automized


modification date returned by: print("last modified: %s" % time.ctime(os.path.getmtime(file)))
Metadata "Medium erstellt" returned by hachoir property "creation_date", but shifted by one hour (time zone thing?)
Metadata "Datum" returned by hachoir property "last_modification", but shifted by -1 hour (time zone thing?)


Getestet:
ffmpeg -i IMG_0185.MOV -metadata creation_time="2022-12-22 22:22:22" -c copy IMG_0185.MOV_mod.avi
-> hat nicht funktioniert, sämtliche Metadaten entfernt:
ffmpeg - i IMG_0185.MOV_mod.avi

ffmpeg -i IMG_0185.MOV -metadata creation_time="2022-12-22 22:22:22" -c copy IMG_0185.MOV_mod.avi
-> gleiches Problem




https://stackoverflow.com/questions/40354172/change-avi-creation-date-with-ffmpeg
https://superuser.com/questions/983804/mp4-video-editing-creation-date-and-other-metadata
https://unix.stackexchange.com/questions/250130/copy-file-creation-date-to-metadata-in-ffmpeg



exiftool (works!)
-----------------
exiftool -MediaCreateDate="2022:02:15 22:22:41+01:00" IMG_0185_test.MOV
exiftool -MediaModifyDate="2022:02:15 22:22:41+01:00" IMG_0185_test.MOV
exiftool -CreationDate="2022:02:15 22:22:41+01:00" IMG_0185_test.MOV
-> Does work, but it's not the date visible in the properties :(

exiftool -CreateDate="2022:02:15 22:22:41+01:00" IMG_0185_test.MOV
-> That's the one :) (Medium erstellt & Datum)

Also set the other dates:
-ModifyDate
-TrackCreateDate
-TrackModifyDate

-FileModifyDate (File Modification Date/Time)
-FileCreateDate (File Creation Date/Time)

Note: +01:00 only for:
File Modification Date/Time
File Creation Date/Time
CreationDate
-> take the correct time and append +01:00 (don't add it)
Observation: if it is added to the other dates, e.g. the CreateDate, one hour will be added! Is the time correct if you don't append +01:00?
exiftool -CreateDate="2022:02:15 22:22:41" IMG_0185_test.MOV
-> no, still offset by 1 h. -> you have to correct it yourself by substracting one hour from the target time:
exiftool -CreateDate="2022:02:15 21:22:41" IMG_0185_test.MOV
-> I suspect it's either GMT or UTC, so in summer 2 hours may need to be substracted!

Because setting the metadata automatically set's the FileModifyDate to current, set it at the same time:
exiftool -CreateDate="2021:02:15 21:22:41" -FileModifyDate="2021:02:15 22:22:41 +01:00" IMG_0185_test.MOV

Copy from the original:
Make                            : Apple
Software                        : 12.1.4
Com Apple Photos Originating Signature: ATCRdt8sqPLeNp58/uTIs4QvB6ud
XMP Toolkit                     : Image::ExifTool 11.28
Creation Date                   : 2022:02:15 22:22:41+01:00
Camera Model Name               : iPhone 8dings
Avg Bitrate                     : 17.3 Mbps
Image Size                      : 1920x1080
Megapixels                      : 2.1
Rotation                        : 0

https://sno.phy.queensu.ca/~phil/exiftool/

ToCheck: Do MP4 files have the same dates, or are there additional ones to set? (missing ones should automatically be skipped)

Setting all the tags at once: http://u88.n24.queensu.ca/exiftool/forum/index.php?topic=8067.0

# first, substract one hour and remove the +01:00 part at the end:
-CreateDate
-ModifyDate
-TrackCreateDate
-TrackModifyDate
http://owl.phy.queensu.ca/~phil/exiftool/exiftool_pod.html#item__2dtagsfromfile_srcfile_or_fmt
http://owl.phy.queensu.ca/~phil/exiftool/exiftool_pod.html#READING-EXAMPLES
Transfer all from file, try:
exiftool -TagsFromFile srcimage.jpg "-all:all>all:all" targetimage.jpg
exiftool -TagsFromFile srcimage.jpg targetimage.jpg
  -x TAG      (-exclude)           Exclude specified tag
  
  exiftool -TagsFromFile src.jpg -all:all dst.jpg

    Copy the values of all writable tags from src.jpg to dst.jpg, preserving the original tag groups.
    
--> Tried all that. Only the using -TagsFromFile without options results in a comparable number of tags to my tool, but without groups
--> Continue with my tool.
