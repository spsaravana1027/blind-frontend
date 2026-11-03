import os
import urllib.request
import json

base_api = 'https://api.github.com/repos/HuskyLens/HUSKYLENSUploader/contents/driver/windows%2010/CP210x_Universal_Windows_Driver'
dest_dir = r'd:\iot-blind\cp210x_driver'

def download_folder(api_url, local_path):
    os.makedirs(local_path, exist_ok=True)
    req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        items = json.loads(resp.read().decode())
    for item in items:
        p = os.path.join(local_path, item['name'])
        if item['type'] == 'file':
            print("Downloading:", item['name'])
            urllib.request.urlretrieve(item['download_url'], p)
        elif item['type'] == 'dir':
            download_folder(item['url'], p)

download_folder(base_api, dest_dir)
print('Done downloading driver files to:', dest_dir)

