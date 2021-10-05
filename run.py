# -*- coding: utf-8 -*-
from __future__ import print_function

import sys
import json
from verify_ehc import *
from datetime import datetime, timedelta
import time
import pyzbar.pyzbar as pyzbar
import numpy as np
import cv2

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,480)
font_simplex = cv2.FONT_HERSHEY_SIMPLEX
font_duplex = cv2.FONT_HERSHEY_DUPLEX

qrcodes={}
process=[]
validusers=0

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

print("Downloading...")
certs_table: Dict[str, CertList] = {}
certs: Optional[CertList] = download_ehc_certs(['DE', 'AT', 'SE', 'GB', 'NL'], certs_table);
if not certs:
    print("empty trust list!")
    sys.exit(1)

print("Ready...")

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

if not(cap.isOpened()):
    cap.open(device)
while(cap.isOpened()):
    # Capture frame-by-frame
    ret, frame = cap.read()
    # Our operations on the frame come here
    im = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    decodedObjects = pyzbar.decode(im)

    for decodedObject in decodedObjects: 
         # Check barcode
        if decodedObject.type == 'QRCODE':

            # Is qr code known?
            qrcode = decodedObject.data.decode('ascii')
            if qrcode in qrcodes:
                if qrcodes[qrcode]['valid']:
                    color = (119,155,0)
                else:
                    color = (41,20,141)
                text = qrcodes[qrcode]['name']
            else:
                # Add to process list
                process.append(qrcode)
                color = (101,56,0)
                text = '???'

            points = decodedObject.polygon
            # If the points do not form a quad, find convex hull
            if len(points) > 4 : 
                hull = cv2.convexHull(np.array([point for point in points], dtype=np.float32))
                hull = list(map(tuple, np.squeeze(hull)))
            else:
                hull = points;
            # Number of points in the convex hull
            n = len(hull)
            # Draw the convext hull
            for j in range(0,n):
               cv2.line(frame, hull[j], hull[ (j+1) % n], color, 3)
            # Text
            x = decodedObject.rect.left
            y = decodedObject.rect.top
            cv2.putText(frame, text, (x, y - 10), font_simplex, 1, color, 2, cv2.LINE_AA)

    # Full counter
    cv2.putText(frame, str(validusers), (10, 60), cv2.FONT_HERSHEY_DUPLEX, 2, (119,155,0), 4, cv2.LINE_AA)
    # Display the resulting frame
    cv2.imshow('frame',frame)

    # Check unprocessed qr codes
    for ehc_code in process:
        print("New qr code", ehc_code)
        qrcodes[ehc_code] = {}
        try:
            ehc_msg = decode_ehc(ehc_code)
            ehc_payload = cbor2.loads(ehc_msg.payload)
            qrcodes[ehc_code]['name'] = ehc_payload[-260][1]['nam']['gn'] + ' ' + ehc_payload[-260][1]['nam']['fn']
            qrcodes[ehc_code]['valid'] = validate(ehc_msg, ehc_payload)
            if qrcodes[ehc_code]['valid']:
                print(qrcodes[ehc_code]['name'], file=sys.stderr)
                validusers = validusers + 1
        except:
            qrcodes[ehc_code]['valid'] = False
            if not 'name' in qrcodes[ehc_code]:
                qrcodes[ehc_code]['name'] = '(Invalid EHC QR)'
            print('Failed', sys.exc_info())
    process.clear()

    key = cv2.waitKey(1)
    if key & 0xFF == ord('q'):
        break

# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()
