Yet Another CovPass Checker
===========================

Im WS21/22 müssen an der FAU min. 10% der Teilnehmer von Lehrveranstaltungen bis
zu 50 Teilnehmern getestet werden
([Quelle](https://www.fau.de/corona/3g-regel/#collapse_4)).

Wie wäre es, wenn wir einfach am Eingang einen Notebook mit Webcam hinstellen,
und Studis selbstständig ihren Code scannen lassen?

![Bildschirmausgabe](screenshot.jpg)

Auf dem Bildschirm wird die Webcamausgabe angezeigt, erkannte QR Codes werden
farblich markiert:

 * blau: Noch nicht verarbeitet
 * grün (mit Namen): Erfolgreich verifizierter QR-Code
 * gelb (mit Namen): verifizierter QR-Code eines nicht angemeldeten Teilnehmers (siehe unten)
 * rot: Invalider QR-Code oder ungültiger Ausweis

Die Anzahl der erfolgreichen (eindeutigen) Eingaben wird oben links in der Ecke
angezeigt (im Beispiel: 2) -- im Idealfall entspricht es der Anzahl der Personen
im Raum.


**Problem:** (Personal)Ausweise werden nicht kontrolliert.

Somit könnte z.B. von der Oma der Impfausweis im Handy abgespeichert und
vorgezeigt werden.

*Mögliche Lösung:* Automatischer Abgleich mit den Personendaten aus dem
dazugehörigen Waffelkurs.
Dazu einfach eine Datei mit zeilenweise Nachname und Vorname (getrennt durch ein
`;`) der angemeldeter Teilnehmer erstellen -- schon werden Namen, welche sich
nicht auf der Liste befinden, in gelber Farbe angezeigt und nicht mit gezählt.

Nicht perfekt, aber besser als nichts.


Zum Beenden die Taste `q` drücken.


Benutzung
---------

Rekursiv (mit Submodule) klonen, Abhängigkeiten installieren und ausführen, z.B.:

    git clone git@gitlab.cs.fau.de:heinloth/covpass-check.git --recursive
    cd covpass-check
    sudo apt install zenity libzbar0
    pip3 install -r requirements.txt
    python3 get_rules.py
    python3 webcam.py

Weitere Informationen via

    python3 webcam.py -h

Für akustische Teilnehmerbeschränkung bei einer geringen Webcamauflösung
beispielsweise

    python3 webcam.py -a students.csv -s -r 640x480 -l log.txt

Für den Übungsbetrieb einfach die Teilnehmerliste(n) der Veranstaltung(en) im
oben beschriebenen`.csv` Format in den Unterordner `attendees` legen und schlicht

    ./start.sh

ausführen (bei Bedarf die Parameter in der Variable `PARAMS` anpassen).

Das Skript hält eine Kontaktliste für 2 Wochen im Unterordner `contacts` bereit
(ältere Listen werden automatisch gelöscht).


Weiterführende Informationen
----------------------------

 * https://github.com/panzi/verify-ehc
 * https://github.com/Digitaler-Impfnachweis/certification-apis
 
Audiodateien von
 * https://notificationsounds.com/
