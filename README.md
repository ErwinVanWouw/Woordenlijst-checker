# Woordenlijst-checker
A handy tool to quickly look-up words in Woordenlijst.org within your active Windows-app

## Introduction
This free and open source tool allows you to quickly verify whether a word is included in the official 'green' Woordenlijst.org database and if an unofficial 'white' alternative is available, all without leaving the Windows application you are working in.

<ins>Key Features</ins>
- works in any Windows application
- allows you to modify the default shortcut key F9 by clicking the system tray icon
- multi-monitor support
- shows a verification window for 3 seconds if a word is found
- option to open Woordenlijst.org if a word is not listed
- automatically shows the correct article (de/het) and gender for Dutch nouns

## References
The Woordenlijst-checker tool uses the following databases but is in no other way affiliated with the organisations that manage them.

The database and application for [Woordenlijst.org](https://woordenlijst.org/) is developed and managed by [Instituut voor de Nederlandse Taal](https://ivdnt.org/) under the authority of the [Taalunie](https://taalunie.org/).
The database and application for [Onzetaal.nl](https://onzetaal.nl/taalloket/zoek-spelling) is developed and managed by [Genootschap Onze Taal](https://onzetaal.nl) and [Uitgeverij Unieboek Het Spectrum bv](https://www.prisma.nl/).

Dutch website Woordenlijst-checker tool: https://www.blackkite.nl/nieuws/woordenlijst-checker.php

## Installation
Download the latest package under [Releases](../../releases/) and run the program. This has the Python application and all its dependencies bundled into a single package. If Python is installed on your machine, simply download the Python file and run it.

## How to Use
Select the word you want to look up (Ctrl+Shift+Left/Right Arrow). Press F9 and look at your screen.  

If the selected word is found in the Woordenlijst.org database, a small pop-up window will confirm that it is spelled according to the official Dutch spelling. This window automatically disappears after three seconds, and in the meantime, you can continue working as usual. If you want the pop-up to remain on screen, simply click it.

Woordenlijst-checker also shows the grammatical gender of nouns, along with the article(s) that go with it. If a plural form is identical to the infinitive (e.g., harken), this will be indicated in the pop-up window.

If the word is absent from the official Dutch word list, a pop-up window will notify you. This dialog window lets you either close it, select an alternative word (if any), or access the Woordenlijst.org website. If an alternative ‘Witte spelling’ is available on Onzetaal.nl, it will be displayed as well. The word you searched for will remain on your Windows clipboard.

## Adjust Shortcut and Pop-up Location
When you first launch Woordenlijst-checker, a configuration file is created with F9 set as the default shortcut key. If this default shortcut key conflicts with other software on your system, you can modify it. Click the Woordenlijst-checker system tray icon, open 'Instellingen', replace F9 with your preferred shortcut key (combination), and click 'Opslaan'.

Would you like the pop-up window to appear in a different location on your screen or on another monitor? Drag and drop the pop-up window anywhere on your primary or secondary monitor, and the tool will remember its location. The next time you trigger the tool by pressing F9 the pop-up window will appear here. Has the pop-up moved outside the visible area of your screen? Click the Woordenlijst-checker system tray icon, go to Instellingen and click 'Positie resetten'.

Can't see a system tray icon? Windows 10/11 automatically hides newly added tray icons in the overflow (the small ^ arrow next to the clock). Alternatively, you can make it visible via Personalization > Taskbar > Other system tray icons.

## Demo
https://youtu.be/wGiD9uJ44wc

## Support
Need help or support? Go to https://www.blackkite.nl/nieuws/woordenlijst-checker.php
