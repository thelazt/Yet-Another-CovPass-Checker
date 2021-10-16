#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys
import json
from verify_ehc import *
from datetime import datetime, timedelta
import time
import pyzbar.pyzbar as pyzbar
import numpy as np
import cv2
import unicodedata
import argparse
from playsound import playsound

parser = argparse.ArgumentParser(description='CovPass Check via Webcam (PoC)')
parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
parser.add_argument('-d', '--device', type=int,help='webcam device number (/dev/videoX)', default=0)
parser.add_argument('-r', '--resolution', help='webcam resolution (WxH)', default='1280x720')
parser.add_argument('-c', '--count', type=int, help='initial count value', default=0)
parser.add_argument('-s', '--sound', action='store_true', help='accoustic notification after each new (!) scan')
parser.add_argument('-f', '--freeze', type=float, help='seconds to freeze image after each new (!) scan', default=0.7)
parser.add_argument('-t', '--trustlist', type=argparse.FileType('rb'), help='use given trustlist (json) instead of downloading new one')
parser.add_argument('-a', '--allowed', type=argparse.FileType('r'), help='list of allowed names')
parser.add_argument('-l', '--log', type=argparse.FileType('a'), help='access log file', default=sys.stderr)
parser.add_argument('-w', '--window', help='window name', default='CovPass Check')
args = parser.parse_args()

# Webcam 
cap = cv2.VideoCapture(args.device)
w,h = args.resolution.split('x')
cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(w))
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(h))
font_simplex = cv2.FONT_HERSHEY_SIMPLEX
font_duplex = cv2.FONT_HERSHEY_DUPLEX
cv2.namedWindow(args.window, cv2.WINDOW_NORMAL)

#cv2.namedWindow(args.window, cv2.WND_PROP_FULLSCREEN)
#cv2.setWindowProperty(args.window, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)


qrcodes={}
process=[]
uniqusers=[]
validusers=args.count
EPOCH = datetime(1970, 1, 1)

certs_table: Dict[str, CertList] = {}
certs: Optional[CertList] = None
if args.trustlist:
    certs = load_hack_certs_json(args.trustlist.read(), args.trustlist.name)
else:
    print("Downloading...")
    certs = download_ehc_certs(['DE', 'AT', 'SE', 'GB', 'NL'], certs_table);
if not certs:
    print("empty trustlist!")
    sys.exit(1)

print("Ready...")

normalize_mapping = [ ('Ä', 'Ae'), ('Ö', 'Oe'), ('Ü', 'Ue'), ('ä', 'ae'), ('ö', 'oe'), ('ü', 'ue'), ('ß', 'ss') ]
def normalize(s):
    for f, t in normalize_mapping:
       s = s.replace(f, t)
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').strip()

def validate(ehc_msg, ehc_payload):
    try:
        issued_at = EPOCH + timedelta(seconds=ehc_payload[6])

        expires_at_int = ehc_payload.get(4)
        if expires_at_int is not None and datetime.utcnow() > datetime(1970, 1, 1) + timedelta(seconds=expires_at_int):
            print('Expired!')
            return False;

        if certs is not None:
            return verify_ehc(ehc_msg, issued_at, certs, False)
    except:
        print('Failed', sys.exc_info())
    return False

class Color:
    RED = (41,20,141)
    GREEN = (119,155,0)
    YELLOW = (19,147,201)
    BLUE = (101,56,0)

def highlight_object(frame, obj, text, color):
    points = obj.polygon
    # If the points do not form a quad, find convex hull
    if len(points) > 4 : 
        hull = cv2.convexHull(np.array([point for point in points], dtype=np.float32))
        hull = list(map(tuple, np.squeeze(hull)))
    else:
        hull = points;
    # Number of points in the convex hull
    n = len(hull)
     
    # Draw the convext hull
    for j in range(0, n):
       cv2.line(frame, hull[j], hull[ (j+1) % n], color, 3)
    # Text
    x = obj.rect.left
    y = obj.rect.top
    cv2.putText(frame, text, (x, y - 10), font_simplex, 1, color, 2, cv2.LINE_AA)

def highlight_ehc(frame, obj, qrcode):
     if qrcode['valid']:
         if qrcode['unique'] and (len(allowed) == 0 or qrcode['allowed']):
             col = Color.GREEN
         else:
             col = Color.YELLOW
     else:
         col = Color.RED
     highlight_object(frame, obj, qrcode['name'], col)

def wait(millis = 1):
    if millis > 0:
        key = cv2.waitKey(millis)
        if key & 0xFF == ord('q'):
            cap.release()
            cv2.destroyAllWindows()
            sys.exit(0)

allowed=[]
if args.allowed:
    for line in args.allowed.readlines():
        allowed.append(normalize(line).split(";"))

if not cap.isOpened():
    cap.open(WEBCAM_DEVICE)

while cap.isOpened():
    # Capture frame-by-frame
    ret, frame = cap.read()
    # Our operations on the frame come here
    im = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    objs = pyzbar.decode(im)

    for obj in objs: 
         # Check barcode
        if obj.type == 'QRCODE':
            # Is qr code known?
            ehc_code = obj.data.decode('ascii')
            if ehc_code in qrcodes:
                highlight_ehc(frame, obj, qrcodes[ehc_code])
            else:
                # Add to process list
                process.append((obj, ehc_code))
                highlight_object(frame, obj, '', Color.BLUE)

    # Full counter
    cv2.putText(frame, str(validusers), (10, 60), cv2.FONT_HERSHEY_DUPLEX, 2, Color.GREEN, 4, cv2.LINE_AA)
    # Display the resulting frame
    cv2.imshow(args.window, frame)

    # Check unprocessed qr codes
    for obj, ehc_code in process:
        print("New qr code", ehc_code)
        qrcodes[ehc_code] = {}
        try:
            ehc_msg = decode_ehc(ehc_code)
            ehc_payload = cbor2.loads(ehc_msg.payload)
            print("Payload ", ehc_payload[-260][1])
            gn = normalize(ehc_payload[-260][1]['nam']['gn'])
            fn = normalize(ehc_payload[-260][1]['nam']['fn'])
            qrcodes[ehc_code]['name'] = gn + ' ' + fn
            uid = ehc_payload[-260][1]['nam']['fnt'] + '<<<' + ehc_payload[-260][1]['nam']['gnt']  + '<<<<' + ehc_payload[-260][1]['dob']
            qrcodes[ehc_code]['uid'] = uid
            if uid in uniqusers:
                print(uid, "not unique!")
                qrcodes[ehc_code]['unique'] = False
            else:
                uniqusers.append(uid)
                qrcodes[ehc_code]['unique'] = True
            qrcodes[ehc_code]['valid'] = validate(ehc_msg, ehc_payload)
            if qrcodes[ehc_code]['valid']:
                if len(allowed) > 0:
                    qrcodes[ehc_code]['allowed'] = False
                    gnt = ehc_payload[-260][1]['nam']['gnt'].replace('<',' ')
                    fnt = ehc_payload[-260][1]['nam']['fnt'].replace('<',' ')
                    for a in allowed:
                        if (fn in a[0] and gn in a[1]) or (fnt in a[0].upper() and gnt in a[1].upper()):
                            qrcodes[ehc_code]['allowed'] = True
                            break

                if len(allowed) == 0 or qrcodes[ehc_code]['allowed']:
                    validusers = validusers + 1
                    note = ''
                else:
                    note = '(not allowed)'
                print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), qrcodes[ehc_code]['name'], note, file=args.log)
        except:
            qrcodes[ehc_code]['valid'] = False
            if not 'name' in qrcodes[ehc_code]:
                qrcodes[ehc_code]['name'] = '(Invalid EHC QR)'
            print('Failed', sys.exc_info())

        highlight_ehc(frame, obj, qrcodes[ehc_code])
        cv2.imshow(args.window, frame)

        if args.sound:
            playsound('ok.mp3' if qrcodes[ehc_code]['valid'] and (len(allowed) == 0 or qrcodes[ehc_code]['allowed']) else 'error.mp3', False)
        wait(int(args.freeze * 1000))

    process.clear()
    wait(1)

# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()
