#!/usr/bin/env python

import sys

import PIL.ExifTags
import PIL.Image

image_path = sys.argv[1]
img = PIL.Image.open(image_path)

exif_data = img._getexif()

exif = {PIL.ExifTags.TAGS[k]: v for k, v in img._getexif().items() if k in PIL.ExifTags.TAGS}

for k, v in exif.items():
    if k != "MakerNote":
        print(k, v)
