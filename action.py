# Dropzone Action Info
# Name: CloudApp
# Description: Upload file to CloudApp
# Handles: Files
# Creator: Just4test
# URL: https://github.com/just4test
# Events: Clicked, Dragged
# OptionsNIB: Login
# KeyModifiers: Command, Option, Control, Shift
# SkipConfig: No
# RunsSandboxed: Yes
# Version: 1.0
# MinDropzoneVersion: 3.5
# PythonPath: /usr/local/bin/python3

import sys
if not ('packages' in sys.path):
    sys.path.insert(0, 'packages')

import os
import requests
from requests.auth import HTTPDigestAuth
from requests_toolbelt import (MultipartEncoder, MultipartEncoderMonitor)

USERNAME = os.environ['username']
PASSWORD = os.environ['password']


import time

def readable_size(size):
    K = 1024
    M = K * K
    G = M * K
    if size > 10 * G:
        return '{:.0f} GB'.format(size / G)
    if size > G:
        return '{:.1f} GB'.format(size / G)
    if size > 10 * M:
        return '{:.0f} MB'.format(size / M)
    if size > 1024 * 1024:
        return '{:.1f} MB'.format(size / M)
    if size > 1024 * 10:
        return '{:.0f} KB'.format(size / K)
    if size > 1024:
        return '{:.1f} KB'.format(size / K)
    return '{} B'.format(size)

class ProgressPercentage:
    def __init__(self, filepath):
        self._filepath = filepath
        self._size = float(os.path.getsize(filepath))
        self._seen_so_far = 0
        self._lock = threading.Lock()
    def __call__(self, bytes_amount):
        # To simplify we'll assume this is hooked up
        # to a single filename.
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            dz.percent(percentage)

def upload(filepath):
    foldpath, filename = os.path.split(filepath)
    def show_err(title, info, response):
        print('{}: {}\n{}\n{}'.format(title, info, response, response.text))
        dz.error(title, info)

    # Create upload token
    dz.begin("Requesting upload token for [ {} ]...".format(filename))
    filesize = os.path.getsize(filepath)

    r = requests.post('https://my.cl.ly/v3/items',
    auth=HTTPDigestAuth(USERNAME, PASSWORD),
    json={'name': filename, 'file_size': filesize})

    try:
        temp = r.json()
        # print(yaml.dump(temp, default_flow_style=False))
    except Exception:
        # print(r.text)
        pass

    if r.status_code == 401:
        show_err('CloudApp Auth Failed', 'Please check your Username and Password.\n' +
            'To edit them, right click CloudApp icon in Dropzone Pannel, and chose Edit.', r)
        exit(1)
    if r.status_code == 422 and 'errors' in temp:
        info = ''
        for err in temp['errors']:
            if err == 'file_size':
                info += 'File is too large. It has {}.\n'.format(readable_size(file_size))
        show_err('Upload Failed', info, r)
        exit(1)
    if not (200 <= r.status_code <= 299):
        show_err('Upload Failed',
            'Error when creating upload token. Status code {}.'.format(r.status_code), r)
        exit(1)

    # Upload data
    dz.begin("Uploading [ {} ]...".format(filename))
    dz.determinate(True)

    # file must be the last fields, or else error occerd.
    fields = [(k, v) for k, v in temp['s3'].items()]
    fields.append(('file', (filename, open(filepath, 'rb'))))
    progress = 0
    def progress_callback(monitor):
        temp = int(monitor.bytes_read / filesize * 100)
        nonlocal progress
        if progress != temp:
            progress = temp
            dz.begin("Uploading [ {} ]... {} / {}"
            .format(filename, readable_size(monitor.bytes_read), readable_size(filesize)))
            dz.percent(temp)

    m = MultipartEncoder(fields=fields)
    m = MultipartEncoderMonitor(m, progress_callback)
    r2 = requests.post(temp['url'], data=m, headers={'Content-Type': m.content_type}, allow_redirects=False)
    if r2.status_code != 303:
        show_err('Upload Failed', 'Error when transferring data. Status code {}.'.format(r.status_code), r)
        exit(1)

    # Finish upload
    redirect_url = r2.headers['Location']
    # print(redirect_url)

    r3 = requests.get(redirect_url, auth=HTTPDigestAuth(USERNAME, PASSWORD))
    if r3.status_code != 200:
        show_err('Upload Failed',
            'Error when finishing upload. Status code {}.'.format(r.status_code), 3)
        exit(1)

    return r3.json()


def dragged():
    if len(items) == 1:
        result = upload(items[0])
        dz.url(result['share_url'])
        dz.finish(result['share_url'])
    else:
        temp = ''
        for item in items:
            result = upload(item)
            temp += '{}\n\t{}\n'.format(result['name'], result['share_url'])
        dz.text(temp)
        dz.finish('Files info in your clipboard.')
