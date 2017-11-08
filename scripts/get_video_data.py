import sys

import subprocess

print(sys.argv)
video_url = sys.argv[1]
print(video_url)

ffprobe_cmd = 'ffprobe -i "{}"'.format(video_url)
result = subprocess.check_output(ffprobe_cmd, shell=True, stderr=subprocess.STDOUT)
try:
    result = result.decode('utf-8')
except UnicodeDecodeError as e:
    try:
        result = result.decode('utf-16')
    except UnicodeDecodeError as e:
        result = result.decode('latin-1')

lines = result.split("\n")
width, height = None, None
for line in lines:
    if 'SAR' in line:
        data = line.split(', ')[3]
        r1, r2 = map(int, data.split(' ')[0].split('x'))
        o1, o2 = map(int, data.rstrip(']').split(' ')[-1].split(':'))
        portrait = o1 < o2
        width, height = (r2, r1) if portrait else (r1, r2)
    elif 'Stream #0:0' in line:
        data = line.split(', ')[3]
        r1, r2 = map(int, data.split(' ')[0].split('x'))
        width, height = r1, r2
print(width, height)
