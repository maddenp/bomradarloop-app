from PIL import Image
import datetime as dt
import imageio
import numpy as np
import time

radar = {
    'Sydney': 'IDR763',
}

def getbg(location):
    fn = f'{radar[location]}.background.png'
    return Image.open(fn).convert('RGBA')

location = 'Sydney'

nimages = 6
radar_interval_min = 6
radar_interval_sec = radar_interval_min * 60
ts_now = int(time.time())
ts_fix = ts_now - (ts_now % radar_interval_sec)
mkdt = lambda n: dt.datetime.fromtimestamp(ts_fix - (radar_interval_sec * n), tz=dt.timezone.utc)
strs = [mkdt(n).strftime('%Y%m%d%H%M') for n in range(nimages-1, -1, -1)]

# print(dt.datetime.fromtimestamp(ts_now, tz=dt.timezone.utc).strftime('%Y%m%d%H%M'))
# print(dt.datetime.fromtimestamp(ts_fix, tz=dt.timezone.utc).strftime('%Y%m%d%H%M'))
# print()
# for x in strs:
#     print(x)

ns = ('0254', '0300', '0306', '0312', '0318', '0324')
bg = getbg(location)
merge = lambda bg, fn: np.array(Image.alpha_composite(bg, Image.open(fn).convert('RGBA')))
images = [merge(bg, f'{radar[location]}.T.20190109{n}.png') for n in ns]
imageio.mimsave('loop.gif', images, fps=2)
