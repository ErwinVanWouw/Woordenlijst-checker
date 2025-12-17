# Woordenlijst-checker
A handy tool to quickly look-up words in Woordenlijst.org within your active Windows-app

## Introduction
This free and open source tool allows editors, proofreaders, and translators to quickly verify whether a word is included in the Woordenlijst.org database, all without leaving the Windows application they are working in.

## References
The database and application for Woordenlijst.org is developed and managed by [Instituut voor de Nederlandse Taal](https://ivdnt.org/) under the authority of the [Taalunie](https://taalunie.org/). The Woordenlijst-checker tool uses this database but is in no other way affiliated with the Nederlandse Taalunie.

Website official Dutch spelling database: https://woordenlijst.org/  
Website Woordenlijst-checker tool: https://www.blackkite.nl/nieuws/woordenlijst-checker.php

## Installation
Download the latest package under [Releases](../../releases/) and run the program. This has the Python application and all its dependencies bundled into a single package. If Python is installed on your machine, simply download the Python file and run it.

## Key Features
- works in any Windows application
- allows you to modify the default shortcut key F9
- multi-monitor support
- runs completely in the background
- uses hardly any system resources
- shows a verification window for 3 seconds if a word is found
- option to open Woordenlijst.org if a word is not listed

## How to Use
Select the word you want to look up (Ctrl+Shift+Left/Right Arrow). Press F9 and look at your screen.  

If the selected word is found in the Woordenlijst.org database, a small pop-up window will confirm that it is spelled according to the official Dutch spelling. This window automatically disappears after three seconds, and in the meantime, you can continue working as usual.

If the word is absent from the official Dutch word list, a pop-up window will notify you. This dialog window lets you either close it, select an alternative word (if any), or access the Woordenlijst.org website. The word will remain on your Windows clipboard.

## Adjust Shortcut and Popup Location
When you first launch Woordenlijst-checker, a configuration file is created with F9 set as the default shortcut key. If this default shortcut key conflicts with other software on your system, you can modify it. Navigate to the folder where  Woordenlijst-checker is installed, open the config.ini configuration file using Notepad, and replace F9 with your preferred shortcut key (combination).

Would you like the popup window to appear in a different location on your screen or on another monitor? Drag and drop the popup window anywhere on your primary or secondary monitor, and the tool will remember its location. The next time you trigger the tool by pressing F9 the popup window will appear here.

## Demo
https://youtu.be/wGiD9uJ44wc
