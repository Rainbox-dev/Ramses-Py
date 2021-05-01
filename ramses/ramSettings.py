import os
import platform
import json
from .ramState import RamState
from .logger import log

class FolderNames():
    preview = "_preview"
    versions = "_versions"
    publish = "_published"
    userConfig = "Config"
    stepTemplates = "Templates"

class RamSettings:
    """Gets and saves settings used by Ramses.

    To get a setting, just get the corresponding attribute.

    To change a setting temporarily, just set the corresponding attribute. If you want the change to be permanent (i.e. keep the setting for the next sessions), call the save() method.

    By default, settings are saved in a ramses_addons_settings.json file, in the user’s OS specific settings folder:

        Linux: ~/.config/RxLaboratory/Ramses/Config
        Windows: %appdata%/RxLaboratory/Ramses/Config
        MacOS: ?

    There is only one instance of RamSettings, available with the Ramses.instance.settings() method
    """
    
    def __init__( self ):
        # Default Values
        self.autoConnect = True # Wether to always try to (re)connect to the Daemon if offline.
        self.ramsesClientPath = "" # Location of the Ramses Client executable file (.exe on Windows, .app on MacOS, .appimage or binary on Linux)
        self.ramsesClientPort = 18185 # Listening port of the Ramses Daemon

        # Set the path to the settings file (os-specific)
        system = platform.system()
        if system == 'Windows':
            self._folderPath = os.path.expandvars('${APPDATA}/RxLaboratory/Ramses/Config')
            if not os.path.isdir( self._folderPath ): 
                os.makedirs( self._folderPath )
            self._filePath = self._folderPath + '/ramses_addons_settings.json'
        else:
            self._folderPath = ''
            self._filePath = ''

        # Get settings from file
        if os.path.isfile( self._filePath ):
            with open(self._filePath, 'r') as settingsFile:
                settingsStr = settingsFile.read()
                settingsDict = json.loads( settingsStr )
                if settingsDict['autoConnect'] is not None:
                    self.autoConnect = settingsDict['autoConnect']
                if settingsDict['clientPath'] is not None:
                    self.ramsesClientPath = settingsDict['clientPath']
                if settingsDict['clientPort'] is not None:
                    self.ramsesClientPort = settingsDict['clientPort']

        # Not Documented: these are not settings to be customized (yet)
        self.folderNames = FolderNames()
        self.defaultStates = [
            RamState("No", "NO", 1.0, [25,25,25]), # Very dark gray
            RamState("To Do", "TODO", 0.0, [85, 170, 255]), # Blue
            RamState("Work in progress", "WIP", 0.5,  [255,255,127]), # Light Yellow
            RamState("OK", "OK", 1.0, [0, 170, 0]), # Green
        ]

    def folderPath(self):
        return self._folderPath

    def filePath(self):
        return self._filePath

    def save( self ):
        """Saves the current settings to the disk.
        """
        log("I'm saving your settings...")

        settingsDict = {
            'autoConnect': self.autoConnect,
            'clientPath': self.ramsesClientPath,
            'clientPort': self.ramsesClientPort
        }

        if self._filePath == '':
            raise "Invalid path for the settings, I can't save them, sorry."
        
        with open(self._filePath, 'w') as settingsFile:
            settingsFile.write( json.dumps( settingsDict, indent=4 ) )

        log("Settings saved!")
