#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys
import json
import jsonschema
from verify_ehc import *
from datetime import datetime, timedelta
from json_logic.cert_logic import certLogic
from json_logic.cert_logic.extras import EXTRAS
import time
import pyzbar.pyzbar as pyzbar
import numpy as np
import cv2
import unicodedata
import argparse
import traceback
from playsound import playsound

parser = argparse.ArgumentParser(description='CovPass Check via Webcam (PoC)')
parser.add_argument('-a', '--allowed', type=argparse.FileType('r'), help='list of allowed names')
parser.add_argument('-b', '--booster', action='store_true', help='Check booster notification rules')
parser.add_argument('-B', '--boosterrules', help='Path to directory containing certLogic booster notification rules', default='bnrules')
parser.add_argument('-c', '--count', type=int, help='initial count value', default=0)
parser.add_argument('-d', '--device', type=int,help='webcam device number (/dev/videoX)', default=0)
parser.add_argument('-f', '--fullscreen', action='store_true', help='start in full screen')
parser.add_argument('-F', '--freeze', type=float, help='seconds to freeze image after each new (!) scan', default=0.7)
parser.add_argument('-l', '--log', type=argparse.FileType('a'), help='access log file', default=sys.stderr)
parser.add_argument('-m', '--mirror', action='store_true', help='mirror webcam (flip horizontal)')
parser.add_argument('-r', '--resolution', help='webcam resolution (WxH)', default='1280x720')
parser.add_argument('-R', '--rules', help='Path to directory containing certLogic rules', default='rules')
parser.add_argument('-s', '--sound', action='store_true', help='accoustic notification after each new (!) scan')
parser.add_argument('-S', '--schema', help='JSON schema for payload', default='DCC.combined-schema.json')
parser.add_argument('-t', '--trustlist', type=argparse.FileType('rb'), help='use given trustlist (json) instead of downloading new one')
parser.add_argument('-V', '--valuesets', help='Path to directory containung valueset for certLogic', default='valuesets')
parser.add_argument('-w', '--window', help='window name', default='Yet Another CovPass Checker')

debug = parser.add_argument_group('debug', description='These options are only for debugging & testing and should not be used in production!')
debug.add_argument('-q', '--qrcode', nargs='*', help='Manually process contents of given QR code(s)')
debug.add_argument('-Q', '--qrfile', type=argparse.FileType('r'), help='Manually process file containing contents of QR code(s)')
debug.add_argument('-v', '--verbose', action='store_true', help='verbose output')
debug.add_argument('--skip-verification', action='store_true', help='do not verify certificate')
debug.add_argument('--skip-validation', action='store_true', help='do not validate payload')
debug.add_argument('--skip-uniquecheck', action='store_true', help='do not check if certificate owner is unique')

args = parser.parse_args()


# Webcam 
cap = cv2.VideoCapture(args.device)
w,h = args.resolution.split('x')
cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(w))
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(h))
font_simplex = cv2.FONT_HERSHEY_SIMPLEX
font_duplex = cv2.FONT_HERSHEY_DUPLEX

if args.fullscreen:
    cv2.namedWindow(args.window, cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty(args.window, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
else:
    cv2.namedWindow(args.window, cv2.WINDOW_NORMAL)

certs: Optional[CertList] = None
if args.trustlist:
    certs = load_hack_certs_json(args.trustlist.read(), args.trustlist.name)
else:
    print("Downloading...")
    certs_table: Dict[str, CertList] = {}
    certs = download_ehc_certs(['DE', 'AT', 'SE', 'GB', 'NL'], certs_table);
if not certs:
    print("empty trustlist!")
    sys.exit(1)

def normalize(s):
    for f, t in [ ('Ä', 'Ae'), ('Ö', 'Oe'), ('Ü', 'Ue'), ('ä', 'ae'), ('ö', 'oe'), ('ü', 'ue'), ('ß', 'ss') ]:
       s = s.replace(f, t)
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').strip()

valuesets = { }
if not args.skip_validation:
    for file in os.listdir(args.valuesets):
        with open(args.valuesets + '/' + file) as f:
            v = json.loads(f.read())
            valuesets[v['valueSetId']] = v['valueSetValues']
    if not valuesets:
        print("no valuesets - run get_rules.py!")
        sys.exit(1)

schema = { }
if os.path.exists(args.schema):
    with open(args.schema) as f:
        schema = json.loads(f.read())
else:
    print('Schema ' + args.schema + ' not found!')

EPOCH = datetime(1970, 1, 1)
def verify(ehc_msg, ehc_payload):
    global certs, EPOCH
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

# https://github.com/eu-digital-green-certificates/dgc-business-rules-testdata/tree/main/DE
def validate_rule(path, data, valid_if):
    with open(path) as f:
        rule = json.loads(f.read())
        if certLogic({'before':[{'now':[]},rule['ValidFrom']]}, None, EXTRAS) or certLogic({'after':[{'now':[]},rule['ValidTo']]}, None, EXTRAS):
            if args.verbose:
                print('Skip ' + rule['Identifier']);
            return True
        elif args.verbose:
            print('Checking ' + rule['Identifier']);
        if certLogic(rule['Logic'], data) != valid_if:
            print(rule['Identifier'] + ' failed: ' + rule['Description'][0]['desc'])
            return False
    return True

def validate(payload):
    # Try to validate payload
    if schema:
        try:
            jsonschema.validate(payload, schema)
        except jsonschema.exceptions.ValidationError as error:
            print('Payload does not match schema: ' + str(error))
            return False
        if args.verbose:
            print('Payload matches schema');

    # Data for certLogic
    data = {
        'payload': payload,
        'external': {
            'validationClock': certLogic({'formatTime':{'now':''}}, None, EXTRAS),
            'valueSets': valuesets
        }
    }

    # Check against all available rules
    for file in os.listdir(args.rules):
        if not validate_rule(args.rules + '/' + file, data, True):
           return False

    # Check against all available booster rules, if required
    if args.booster:
        for file in os.listdir(args.boosterrules):
            # "Booster Notification" rules --> valid if False (= no notification)
            if not validate_rule(args.boosterrules + '/' + file, data, False):
                return False

    # All good.
    return True

uniqusers = []
validusers = args.count
def process(ehc_code):
    global args, validusers, uniqusers, allowed
    if args.verbose:
        print("New qr code", ehc_code)
    result = { 'valid': False }
    try:
        ehc_msg = decode_ehc(ehc_code)
        ehc_payload = cbor2.loads(ehc_msg.payload)
        payload_data = ehc_payload[-260][1]
        if args.verbose:
            print("Payload ", payload_data)
        gn = normalize(payload_data['nam']['gn'])
        fn = normalize(payload_data['nam']['fn'])
        result['name'] = gn + ' ' + fn

        # check if unique
        if args.skip_uniquecheck:
            result['unique'] = True
        else:
            uid = payload_data['nam']['fnt'] + '<<<' + payload_data['nam']['gnt']  + '<<<<' + payload_data['dob']
            result['uid'] = uid
            if uid in uniqusers:
                print(uid, "not unique!")
                result['unique'] = False
            else:
                uniqusers.append(uid)
                result['unique'] = True

        # verify certificate and validate payload
        if (args.skip_verification or verify(ehc_msg, ehc_payload)) and (args.skip_validation or validate(payload_data)):
            result['valid'] = True

            # check if allowed
            if len(allowed) > 0:
                result['allowed'] = False
                gnt = payload_data['nam']['gnt'].replace('<',' ')
                fnt = payload_data['nam']['fnt'].replace('<',' ')
                for a in allowed:
                    if (a[0] in fn and a[1] in gn) or (a[0].upper() in fnt and a[1].upper() in gnt):
                        result['allowed'] = True
                        break

            if len(allowed) == 0 or result['allowed']:
                validusers = validusers + 1
                note=''
            else:
                note='(not in list)'
            print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), result['name'], note, file=args.log)
    except:
        if not 'name' in result:
            result['name'] = '(Invalid EHC QR)'
        print(traceback.format_exc())
    return result

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
    global cv2
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

qrcodes = {}
if args.qrcode:
    for ehc_code in args.qrcode:
        qrcodes[ehc_code] = process(ehc_code)
if args.qrfile:
    for ehc_code in args.qrfile:
        qrcodes[ehc_code] = process(ehc_code)

if args.verbose:
    print("Ready...")

process_queue = []
while cap.isOpened():
    # Capture frame-by-frame
    ret, frame = cap.read()
    # mirror
    if args.mirror:
        frame = cv2.flip(frame, 1)
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
                # Add to process queue
                process_queue.append((obj, ehc_code))
                highlight_object(frame, obj, '', Color.BLUE)

    # Full counter
    cv2.putText(frame, str(validusers), (10, 60), cv2.FONT_HERSHEY_DUPLEX, 2, Color.GREEN, 4, cv2.LINE_AA)
    # Display the resulting frame
    cv2.imshow(args.window, frame)

    # Check unprocessed qr codes
    for obj, ehc_code in process_queue:
        qrcodes[ehc_code] = process(ehc_code)

        # Graphical highlight of code
        highlight_ehc(frame, obj, qrcodes[ehc_code])
        cv2.imshow(args.window, frame)

        # Play sound
        if args.sound:
            playsound('ok.mp3' if qrcodes[ehc_code]['valid'] and (len(allowed) == 0 or qrcodes[ehc_code]['allowed']) else 'error.mp3', False)

        # Freeze output (for a short time)
        wait(int(args.freeze * 1000))

    process_queue.clear()
    wait()

# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()
