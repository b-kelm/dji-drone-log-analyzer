# Drohnen-Flugdaten Analyse und Visualisierung

Diese Streamlit-Anwendung dient zur Analyse und Visualisierung von Flugdaten Ihrer Drohne, die als CSV-Datei exportiert wurden. Sie ermöglicht die Darstellung verschiedener Flugparameter über die Zeit sowie die Visualisierung der Flugroute auf einer Satellitenkarte.

## Datenvorbereitung

**Wichtig:** Um das korrekte CSV-Format für diese Anwendung zu erhalten, müssen die Flugdaten (typischerweise .DAT-Dateien) von Ihrer Drohne zunächst mit dem Tool **CsvView** von [https://datfile.net/CsvView/intro.html](https://datfile.net/CsvView/intro.html) exportiert werden. Dieses Tool konvertiert die binären Logdateien der Drohne in das benötigte CSV-Format.

Die CSV-Datei sollte folgende Spalten (oder ähnliche) für die volle Funktionalität enthalten:
* Eine Zeitspalte (standardmäßig wird "Clock:Tick#" in Mikrosekunden erwartet und von der App in Sekunden umgerechnet).
* Spalten für Breitengrad (Latitude, z.B. "GPS:Lat").
* Spalten für Längengrad (Longitude, z.B. "GPS:Long").
* Optional eine Spalte für den Gierwinkel/Kurs der Drohne (Yaw, 0-360°, z.B. "IMU_ATTI(1):yaw360:C") für die Ausrichtungsanzeige auf der Karte.
* Weitere numerische Flugparameter, die Sie im Zeitverlauf analysieren möchten.

## Benutzung der Anwendung

1.  **CSV-Datei hochladen:** Nutzen Sie die Schaltfläche "Wählen Sie eine CSV-Datei" in der linken Seitenleiste, um Ihre vorbereitete CSV-Datei hochzuladen.
2.  **Zeitbereich anpassen:** In der Seitenleiste können Sie den globalen Zeitbereich für die Analyse einschränken. Die Zeit wird standardmäßig in Sekunden angezeigt (nach Umrechnung aus Mikrosekunden).
3.  **Parameter für Zeit-Plot auswählen:** Wählen Sie in der Seitenleiste die Parameter aus, die im Liniendiagramm über der Zeit dargestellt werden sollen.
4.  **Karten-Parameter konfigurieren:**
    * Wählen Sie die korrekten Spalten für Breitengrad, Längengrad und optional für den Yaw-Winkel in der Seitenleiste aus. Die Anwendung versucht, Standardnamen wie "GPS:Lat", "GPS:Long" und "IMU_ATTI(1):yaw360:C" vorauszwählen.
    * Verwenden Sie den Slider unter der Karte, um einen bestimmten Zeitpunkt auszuwählen. Die Position und Ausrichtung der Drohne zu diesem Zeitpunkt wird auf der Karte hervorgehoben.
5.  **Interaktion:**
    * Das Zeitdiagramm ist interaktiv (zoomen, verschieben).
    * Die Karte kann gezoomt und verschoben werden. Ein Tooltip auf der Karte zeigt Details zum ausgewählten Punkt.

## Hauptfunktionen

* **Interaktiver Zeit-Plot:** Visualisierung beliebig vieler ausgewählter Flugparameter über die Zeit.
* **Kartenansicht:**
    * Darstellung der Flugroute auf einer Satellitenkarte (mit Straßen).
    * Anzeige der Drohnenposition zu einem per Slider wählbaren Zeitpunkt als grüner Punkt.
    * Optional: Anzeige der Drohnenausrichtung (Yaw) durch einen gelben Pfeil am grünen Punkt.
    * Hoher Zoomfaktor für Detailansicht der Position.
* **Daten-Vorschau:** Anzeige der ersten Zeilen der geladenen CSV-Datei.
* **Flexible Spaltenauswahl:** Anpassung der Zeit-, GPS- und Yaw-Spalten an Ihre CSV-Struktur.

## Hinweis zur Satellitenkarte

Für die Darstellung der Satellitenkartenansicht wird der Dienst Mapbox verwendet. In einigen Fällen oder für erweiterte Nutzung könnte ein Mapbox API-Key notwendig sein. Falls die Satellitenkarte nicht korrekt lädt, müssen Sie ggf. einen kostenlosen API-Key von Mapbox erstellen und diesen als Umgebungsvariable `MAPBOX_API_KEY` auf Ihrem System setzen.

---

Viel Erfolg bei der Analyse Ihrer Flugdaten!