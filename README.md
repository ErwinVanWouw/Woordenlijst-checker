# Woordenlijst-checker
Een handige tool om snel woorden op te zoeken in Woordenlijst.org vanuit uw actieve Windows-app

*Scroll down for English*

## Introductie
Met deze gratis tool kunt u controleren of een woord is opgenomen in de officiële 'groene' database van Woordenlijst.org en of er een onofficieel 'wit' alternatief bestaat zonder uw actieve Windows-app te verlaten.

- Windows-breed inzetbaar voor elke app 
- De standaard sneltoets F9 is aanpasbaar via het systeemvakpictogram
- Multi-monitor support 
- Toont 3 seconden een verificatievenster als een woord voorkomt
- Mogelijkheid om door te klikken naar Woordenlijst.org als een woord niet voorkomt 
- Toont automatisch het juiste lidwoord en het geslacht van zelfstandige naamwoorden

## Verantwoording
Deze Python-tool maakt gebruik van de volgende databases, maar is op geen enkele andere wijze gelieerd aan aan de organisaties die deze databases beheren. U kunt maximaal 30 checks per minuut uitvoeren.

Het woordenbestand en de applicatie op [Woordenlijst.org](https://woordenlijst.org/) worden ontwikkeld en beheerd door het [Instituut voor de Nederlandse Taal](https://ivdnt.org/) in opdracht van de [Taalunie](https://taalunie.org/). Het woordenbestand en de applicatie op [Onzetaal.nl](https://onzetaal.nl/taalloket/zoek-spelling) worden ontwikkeld en beheerd door [Genootschap Onze Taal](https://onzetaal.nl) en [Uitgeverij Unieboek Het Spectrum bv](https://www.prisma.nl/).

Website *Woordenlijst-checker*: https://www.blackkite.nl/nieuws/woordenlijst-checker.php

## Privacystatement

*Woordenlijst-checker* is opensourcesoftware en verzamelt en registreert geen persoonlijke gegevens. Alleen voor het verzenden van de zoekterm maakt de app verbinding met de API.

## Installatie
Ga naar [Releases](../../releases/), download het meest recente bestand en voer het programma uit. Het pakket bevat de Python-toepassing en alle benodigde afhankelijkheden in één bestand. Als u Python al op uw computer hebt staan, kunt u ook alleen het Python-bestand downloaden en uitvoeren.

## Gebruik
Selecteer het woord dat u wilt opzoeken (Ctrl+Shift+Pijl links/rechts), druk op F9 en kijk op uw scherm.

Als het geselecteerde woord voorkomt in de database van Woordenlijst.org, verschijnt er een pop-upvenstertje ter verificatie dat u het hebt gespeld volgens de officiële spelling van het Nederlands. Dit venstertje verdwijnt na drie seconden automatisch weer. Ondertussen kunt u gewoon verdergaan met uw werk. Klik in het pop-upvenster als u wilt dat het zichtbaar blijft.

*Woordenlijst-checker* toont ook het woordgeslacht van het opgevraagde zelfstandig naamwoord, samen met het lidwoord of de lidwoorden die erbij horen. Als een meervoudsvorm gelijk is aan de infinitief (bv. harken), dan wordt dit vermeld in het pop-upvenster.

Als het woord niet in de officiële Woordenlijst van de Nederlandse Taal staat, verschijnt er een dialoogvenster met mogelijke suggesties. Als er een alternatieve 'Witte spelling' beschikbaar is op Onzetaal.nl, wordt deze ook weergegeven. Het gekopieerde woord blijft op het Windows-klembord staan.

## Aanpassen sneltoets of pop-uppositie 
Bij de eerste keer opstarten creëert *Woordenlijst-checker* een configuratiebestand met F9 als standaard sneltoets. Als deze standaard sneltoets conflicteert met andere software op uw systeem, kunt u die sneltoets aanpassen. Rechtsklik op het systeemvakpictogram van Woordenlijst-checker, open 'Instellingen', vervang F9 door de gewenste sneltoets en klik op 'Opslaan'.

U kunt aanpassen waar de pop-ups op uw scherm verschijnen en op welke monitor (indien van toepassing). Sleep het pop-upvenster naar de gewenste locatie op een scherm. De tool onthoudt de locatie. De volgende keer dat u een woord zoekt, opent het pop-upvenster op deze plek.

Valt het pop-upvenster buiten het zichtbare gebied van uw scherm? Klik op het systeemvakpictogram van *Woordenlijst-checker*, ga naar Instellingen en klik op 'Positie resetten'.

Ziet u geen systeemvakpictogram? Windows 10/11 verbergt nieuw toegevoegde pictogrammen automatisch in de overloopbalk (het pijltje naast de klok). U kunt het pictogram ook zichtbaar maken via **Persoonlijke instellingen > Taakbalk > Andere systeemvakpictogrammen**.

## Demo
https://youtu.be/wGiD9uJ44wc

## Support
Hulp of ondersteuning nodig? Ga naar https://www.blackkite.nl/nieuws/woordenlijst-checker.php


==========================
==========================


# English
*Woordenlijst-checker* is a handy tool to quickly look-up words in Woordenlijst.org within your active Windows-app

## Introduction
This free tool allows you to quickly verify whether a word is included in the official 'green' Woordenlijst.org database and if an unofficial 'white' alternative is available, all without leaving the Windows application you are working in.

- Works in any Windows application
- Allows you to modify the default shortcut key F9 by clicking the system tray icon
- Multi-monitor support
- Shows a verification window for 3 seconds if a word is found
- Option to open Woordenlijst.org if a word is not listed
- Automatically shows the correct article (de/het) and gender for Dutch nouns

## References
The *Woordenlijst-checker* tool uses the following databases but is in no other way affiliated with the organisations that manage them. Use of the app is restricted to 30 checks per minute.

The database and application for [Woordenlijst.org](https://woordenlijst.org/) is developed and managed by [Instituut voor de Nederlandse Taal](https://ivdnt.org/) under the authority of the [Taalunie](https://taalunie.org/).
The database and application for [Onzetaal.nl](https://onzetaal.nl/taalloket/zoek-spelling) is developed and managed by [Genootschap Onze Taal](https://onzetaal.nl) and [Uitgeverij Unieboek Het Spectrum bv](https://www.prisma.nl/).

Dutch website *Woordenlijst-checker*: https://www.blackkite.nl/nieuws/woordenlijst-checker.php

# Privacy statement

*Woordenlijst-checker* is open-source software and does not collect or store any personal data. The app only connects to the API to submit the search term.

## Installation
Download the latest package under [Releases](../../releases/) and run the program. This has the Python application and all its dependencies bundled into a single package. If Python is installed on your machine, simply download the Python file and run it.

## How to Use
Select the word you want to look up (Ctrl+Shift+Left/Right Arrow). Press F9 and look at your screen.  

If the selected word is found in the Woordenlijst.org database, a small pop-up window will confirm that it is spelled according to the official Dutch spelling. This window automatically disappears after three seconds, and in the meantime, you can continue working as usual. If you want the pop-up to remain on screen, simply click it.

*Woordenlijst-checker* also shows the grammatical gender of nouns, along with the article(s) that go with it. If a plural form is identical to the infinitive (e.g., harken), this will be indicated in the pop-up window.

If the word is absent from the official Dutch word list, a pop-up window will notify you. This dialog window lets you either close it, select an alternative word (if any), or access the Woordenlijst.org website. If an alternative ‘Witte spelling’ is available on Onzetaal.nl, it will be displayed as well. The word you searched for will remain on your Windows clipboard.

## Adjust Shortcut and Pop-up Location
When you first launch *Woordenlijst-checker*, a configuration file is created with F9 set as the default shortcut key. If this default shortcut key conflicts with other software on your system, you can modify it. Click the *Woordenlijst-checker* system tray icon, open 'Instellingen', replace F9 with your preferred shortcut key (combination), and click 'Opslaan'.

Would you like the pop-up window to appear in a different location on your screen or on another monitor? Drag and drop the pop-up window anywhere on your primary or secondary monitor, and the tool will remember its location. The next time you trigger the tool by pressing F9 the pop-up window will appear here. Has the pop-up moved outside the visible area of your screen? Click the *Woordenlijst-checker* system tray icon, go to Instellingen and click 'Positie resetten'.

Can't see a system tray icon? Windows 10/11 automatically hides newly added tray icons in the overflow (the small ^ arrow next to the clock). Alternatively, you can make it visible via **Personalization > Taskbar > Other system tray icons**.

## Demo
https://youtu.be/wGiD9uJ44wc

## Support
Need help or support? Go to https://www.blackkite.nl/nieuws/woordenlijst-checker.php
