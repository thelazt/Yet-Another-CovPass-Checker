#!/bin/bash
# Parameter: akkustische Mitteilung, vollbild, spiegeln
PARAMS="-s -f -m -Q qrcodes.txt"


# Wechsle in Skriptverzeichnis
cd "$(dirname "${BASH_SOURCE[0]}")"

# Dateieinstellungen
TRUSTLIST='trustlist.json'
TRUSTLIST_MAX_AGE='7 days'
# Teilnehmerliste
ATTENDEEDIR='attendees'
# Kontaktliste
CONTACTDIR='contacts'
CONTACTLIST_MAX_AGE='15 days'


# Lade Wurzelzertifikate
export CH_TOKEN='0795dc8b-d8d0-4313-abf2-510b12d50939'
export FR_TOKEN='eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJqUG0zZ1BzUlZaMWRRUmhHOG1HMGhFN3Jlb2ZXTTNINzJCV1RtajdJcFd3In0.eyJleHAiOjE2ODUxODU5MDYsImlhdCI6MTYyMjExMzkwNiwianRpIjoiOTdjODgyM2EtNjlhZS00NzA4LWE4N2UtNzYxM2NhNGU3ODU5IiwiaXNzIjoiaHR0cHM6Ly9hdXRoLm1lc3NlcnZpY2VzLmluZ3JvdXBlLmNvbS9hdXRoL3JlYWxtcy9QSU5HIiwiYXVkIjoiYWNjb3VudCIsInN1YiI6ImVhMWY1NWVlLTUxMGMtNGMxNi05MWQ4LTE1MjI4OGJhZDViYSIsInR5cCI6IkJlYXJlciIsImF6cCI6InRhY3YtY2xpZW50LWxpdGUiLCJzZXNzaW9uX3N0YXRlIjoiNjk5ODExY2YtODFlZS00ZmNkLTk4NDctY2FkMGJmYjZhOTdiIiwiYWNyIjoiMSIsInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJST0xFX1ZFUklGWV9DT05UUk9MXzJERE9DX0wxIiwiUk9MRV9WRVJJRllfQ09OVFJPTF8yRERPQ19CMiIsIm9mZmxpbmVfYWNjZXNzIiwidW1hX2F1dGhvcml6YXRpb24iXX0sInJlc291cmNlX2FjY2VzcyI6eyJhY2NvdW50Ijp7InJvbGVzIjpbIm1hbmFnZS1hY2NvdW50IiwibWFuYWdlLWFjY291bnQtbGlua3MiLCJ2aWV3LXByb2ZpbGUiXX19LCJzY29wZSI6ImVtYWlsIHByb2ZpbGUgb2ZmbGluZV9hY2Nlc3MiLCJzaXJlbiI6IjAwMDAwMDAwMCIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwicHJlZmVycmVkX3VzZXJuYW1lIjoidGFjdi1tb2JpbGUtbGl0ZSIsImdpdmVuX25hbWUiOiIiLCJmYW1pbHlfbmFtZSI6IiJ9.mpfrIP8ayElTm7yoVayCF11oYrDQEnauk9hbbVBw8idAiE6OsMlWNloZtUbbnwrJZsMX3_NoEyzkiB3HNbxyhPWp7eRZ7qhn8XjZVgg6sVytXqcVZo9R5-Q9JftMKv7JelsY3PsaOo5x-pYOX30ancPRjd78TeenorGopsVN_LLRLQpenfgjjgwx-srZnLa-TFYTcbSvXozfJT7uk5CHyz_MIFLM7pl9Zdt66yTGBkLIyOLFsV5vPeH5SYvgRNDYdxZy4XMo6Gyfz0lAI9Xfcjs20NBoOQMV4JREH4Z-IcJJXeszC9QeA1-tRmxujqIRuyvBal7msLy7Zimd2q7i3Q' 

if [[ ! -f 'DE.pem' ]] ; then
	python3 verify_ehc.py --download-all-root-certs
fi

CERTS="FR,GB" 
for ROOT_CERT in *.pem ; do
	if [[ ${#ROOT_CERT} -eq 6 ]] ; then
		COUNTRY=${ROOT_CERT%.pem}
		#openssl x509 -text -in $ROOT_CERT
		CERTS+=",$COUNTRY"
		export ${COUNTRY}_ROOT_CERT=$ROOT_CERT
	fi
done

# Cache Trustlist
if [[ ! -f "$TRUSTLIST" ]] ; then
	echo "Downloading (new) trust list"
	python3 verify_ehc.py --certs-from $CERTS --save-certs $TRUSTLIST 
elif [[ $(date --date="$TRUSTLIST_MAX_AGE ago" +%s) -gt $(date -r "$TRUSTLIST" +%s || echo 0) ]]; then
	echo "Downloading (new) trust list in background"
	bash -c "python3 verify_ehc.py --certs-from $CERTS --save-certs tmp-$TRUSTLIST && mv -f tmp-$TRUSTLIST $TRUSTLIST && echo done" &
fi

# Wähle Teilnehmerliste aus (oder `Abbrechen` für keine)
CONTACTLOGFILE="$(date +%Y%m%d%H%M)"
if [[ -d "$ATTENDEEDIR" ]] && compgen -G $ATTENDEEDIR/*.csv > /dev/null ; then
	ALLOW=$(cd "$ATTENDEEDIR" && ls *.csv | zenity --list --title="Teilnehmerliste" --column="Datei" )
	if [[ -n "$ALLOW" ]] ; then
		PARAMS+=" -a $ATTENDEEDIR/$ALLOW"
		CONTACTLOGFILE="${ALLOW%.csv}-${CONTACTLOGFILE}"
	fi
fi

mkdir -p ${CONTACTDIR}
# Lösche alte Kontaktlisten
MAXDATE=$(date --date="$CONTACTLIST_MAX_AGE ago" +%Y%m%d%H%M)
for f in $CONTACTDIR/* ; do
	if [[ $f =~ ([0-9]{12})\. && ${BASH_REMATCH[1]} -le $MAXDATE ]] ; then
		rm -f $f
	fi
done

# Starte Webcamanwendung (Beenden mit `q`)
python3 webcam.py ${PARAMS} -t $TRUSTLIST -l "${CONTACTDIR}/${CONTACTLOGFILE}.log" >/dev/null 2>&1


