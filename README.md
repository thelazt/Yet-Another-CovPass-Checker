CovPass Check
=============

Im WS21/22 müssen min. 10% der Teilnehmer von Lehrveranstaltungen bis zu 50 Teilnehmern getestet werden.

Wie wäre es, wenn wir einfach am Eingang einen Notebook mit Webcam hinstellen, und Studis selbstständig ihren Code scannen lassen?

![Bildschirmausgabe](screenshot.jpg)

Auf dem Bildschirm wird die Webcamausgabe angezeigt, erkannte QR Codes werden farblich markiert:

 * blau: Noch nicht verarbeitet
 * grün (mit Namen): Erfolgreich verifizierter QR-Code
 * rot: Invalider QR-Code oder ungültiger Ausweis

Die Anzahl der erfolgreichen (eindeutigen) Eingaben wird oben links in der Ecke angezeigt (im Beispiel: 2) -- im Idealfall entspricht es der Anzahl der Personen im Raum.


Nachteile
---------

**[Personal]Ausweise werden nicht kontrolliert**

Somit könnte z.B. von der Oma der Impfausweis im Handy verwendet werden.

Mögliche Lösung: Automatischer Abgleich mit den Personendaten aus dem dazugehörigen Waffelkurs. Sollte ausreichen (und ist sehr einfach zu implementieren).

...


Benutzung
---------

Rekursiv (mit Submodule) klonen, Abhängigkeiten installieren und ausführen:

    git clone git@gitlab.cs.fau.de:heinloth/covpass-check.git --recursive
    pip3 install -r requirements.txt
    python3 run.py



Weiterführende Informationen
----------------------------

 * https://github.com/panzi/verify-ehc
 * https://github.com/Digitaler-Impfnachweis/certification-apis
