# Woordenlijst-checker
Met deze tool kunt u snel woorden opzoeken in de officiële (groene) en onofficiële (witte) woordenlijst vanuit uw actieve Windows-app

- Windows-breed inzetbaar voor elke app
- De standaard sneltoets F9 is aanpasbaar via het systeemvakpictogram
- Multi-monitor support 
- Toont 3 seconden een verificatievenster als een woord voorkomt
- Toont automatisch het bijbehorende woordsoort
- Mogelijkheid om door te klikken naar Woordenlijst.org als een woord niet voorkomt 

## Installatie
Ga naar [Releases](../../releases/), download het meest recente bestand en voer het programma uit. Het pakket bevat de Python-toepassing en alle benodigde afhankelijkheden in één bestand. Als u Python al op uw computer hebt staan, kunt u ook alleen het Python-bestand downloaden en uitvoeren.

## Gebruik
Selecteer het woord dat u wilt opzoeken (Ctrl+Shift+Pijl links/rechts), druk op F9 en kijk op uw scherm.

Als het geselecteerde woord voorkomt in de database van Woordenlijst.org, verschijnt er een pop-upvenstertje ter verificatie dat u het hebt gespeld volgens de officiële spelling van het Nederlands. Dit venster toont ook de relevante woordsoorten van het gezochte woord en sluit automatisch na drie seconden. Ondertussen kunt u gewoon verdergaan met uw werk. Klik in het pop-upvenster als u wilt dat het zichtbaar blijft.

Als het woord niet in de officiële Woordenlijst van de Nederlandse Taal staat, verschijnt er een dialoogvenster met mogelijke suggesties. Hier kunt u de spelling eventueel aanpassen en opnieuw zoeken. Als er een alternatieve 'Witte spelling' beschikbaar is op Onzetaal.nl, wordt deze ook weergegeven. Het gekopieerde woord blijft op het Windows-klembord staan.

## Aanpassen sneltoets of pop-uppositie 
Bij de eerste keer opstarten creëert Woordenlijst-checker een configuratiebestand met F9 als sneltoets. Als deze sneltoets conflicteert met andere software op uw systeem, kunt u die sneltoets aanpassen. Rechtsklik op het systeemvakpictogram van Woordenlijst-checker, open 'Instellingen', vervang F9 door de gewenste sneltoets en klik op 'Wijzig'.

U kunt ook aanpassen waar de pop-ups op uw scherm verschijnen en op welke monitor (indien van toepassing). Sleep het pop-upvenster naar de gewenste locatie op een scherm. De tool onthoudt de locatie. De volgende keer dat u een woord zoekt, opent het pop-upvenster op deze plek.

Valt het pop-upvenster buiten het zichtbare gebied van uw scherm? Klik op het systeemvakpictogram van Woordenlijst-checker, ga naar Instellingen en klik op 'Reset positie'.

Ziet u geen systeemvakpictogram? Windows 10/11 verbergt nieuw toegevoegde pictogrammen automatisch in de overloopbalk (het pijltje naast de klok). U kunt het pictogram ook zichtbaar maken via Persoonlijke instellingen > Taakbalk > Andere systeemvakpictogrammen.

## Verantwoording
Deze Python-tool maakt gebruik van de volgende databases, maar is op geen enkele andere wijze gelieerd aan aan de organisaties die deze databases beheren.

Het woordenbestand en de applicatie op [Woordenlijst.org](https://woordenlijst.org/) worden ontwikkeld en beheerd door het [Instituut voor de Nederlandse Taal](https://ivdnt.org/) in opdracht van de [Taalunie](https://taalunie.org/). Het woordenbestand en de applicatie op [Onzetaal.nl](https://onzetaal.nl/taalloket/zoek-spelling) worden ontwikkeld en beheerd door [Genootschap Onze Taal](https://onzetaal.nl) en [Uitgeverij Unieboek Het Spectrum bv](https://www.prisma.nl/).

Hulp of ondersteuning nodig? Ga naar [https://www.blackkite.nl/nieuws/woordenlijst-checker.php](https://www.blackkite.nl/nieuws/woordenlijst-checker.php?utm_source=app&utm_medium=desktop&utm_campaign=woordenlijst-checker)

## Privacystatement

Woordenlijst-checker is opensourcesoftware en verzamelt en registreert geen persoonlijke gegevens. Alleen voor het verzenden van de zoekterm maakt de app verbinding met de API. U kunt maximaal 30 checks per minuut uitvoeren.

## Demo
https://youtu.be/wGiD9uJ44wc
