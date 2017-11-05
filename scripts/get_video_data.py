import os
import sys

import subprocess

print(sys.argv)
video_url = sys.argv[1]
print(video_url)

ffprobe_cmd = 'ffprobe -i "{}"'.format(video_url)
result = subprocess.check_output(ffprobe_cmd, shell=True, stderr=subprocess.STDOUT)
lines = result.decode('utf8').split("\n")
for line in lines:
    if 'SAR' in line:
        data = line.split(', ')[3]
        r1, r2 = map(int, data.split(' ')[0].split('x'))
        o1, o2 = map(int, data.rstrip(']').split(' ')[-1].split(':'))
        portrait = o1 < o2
        width, height = (r2, r1) if portrait else (r1, r2)
        print(width, height)
