import os, re, shutil

from .ramses import Ramses
from .ramSettings import RamSettings
from .utils import intToStr
from .logger import (
    log,
    Log
)

class RamFileManager():
    """A Class to help managing file versions"""

    @staticmethod
    def increment( filePath, stateShortName="v" ): # TODO If in publish or preview folder!
        """Copies and increments a file into the version folder
        
        Returns the filePath of the new file version"""

        if not os.path.isfile( filePath ):
            raise Exception( "Missing File: Cannot increment a file which does not exists: " + filePath )

        # Check File Name
        fileName = os.path.basename( filePath )
        decomposedFileName = RamFileManager.decomposeRamsesFileName( fileName )
        if not decomposedFileName:
            log( Log.MalformedName, LogLevel.Critical )
        
        # Get the versions folder
        fileFolder = os.path.dirname( filePath )
        versionsFolderName = RamSettings.instance().folderNames.versions
        if os.path.basename( fileFolder ) == versionsFolderName:
            versionsFolder = fileFolder
        else:
            versionsFolder = fileFolder + '/' + versionsFolderName

        # If there's no version yet, copy as v1
        if not os.path.isdir( versionsFolder ):
            os.makedirs( versionsFolder )
            newFileName = RamFileManager.composeRamsesFileName( decomposedFileName, True )
            newFilePath = fileFolder + '/' + newFileName
            shutil.copy2( filePath, newFilePath )
            return newFilePath

        # Look for the latest version to increment and save
        foundFiles = os.listdir( versionsFolder )
        highestVersion = 0
        state = 'v'

        for foundFile in foundFiles:
            if not os.path.isfile( versionsFolder + '/' + foundFile ): #This is in case the user has created folders in _versions
                continue

            decomposedFoundFile = RamFileManager.decomposeRamsesFileName(foundFile)

            if decomposedFoundFile == None:
                continue
            if decomposedFoundFile['projectID'] != decomposedFileName['projectID']:
                continue
            if decomposedFoundFile['ramType'] != decomposedFileName['ramType']:
                continue
            if decomposedFoundFile['objectShortName'] != decomposedFileName['objectShortName']:
                continue
            if decomposedFoundFile['ramStep'] != decomposedFileName['ramStep']:
                continue
            if decomposedFoundFile["resourceStr"] != decomposedFileName['resourceStr']:
                continue
            if decomposedFoundFile["version"] == -1:
                continue

            version = decomposedFoundFile["version"]
            if version > highestVersion:
                highestVersion = version
                state = decomposedFoundFile["state"]
        
        newFileName = RamFileManager.buildRamsesFileName(
            decomposedFileName['projectID'],
            decomposedFileName['ramStep'],
            decomposedFileName['extension'],
            decomposedFileName['ramType'],
            decomposedFileName['objectShortName'],
            decomposedFileName['resourceStr'],
            highestVersion + 1,
            state,
        )
        newFilePath = versionsFolder + '/' + newFileName
        shutil.copy2( filePath, newFilePath )
        return newFilePath
    
    @staticmethod
    def composeRamsesFileName( ramsesFileNameDict, increment=False ):
        """Builds a filename from a dict as returned by RamFileManager.decomposeRamsesFileName().
        
        The dict must contain:
            - "projectID" optional
            - "ramType"
            - "objectShortName" optional
            - "ramStep" 
            - "resourceStr" optional
            - "state" optional
            - "version" int optional
            - "extension" optional
        If "extension" does not start with a '.' it will be prepended.

        If increment is true, increments the version by 1
        """

        version = ramsesFileNameDict['version']
        if increment:
            if version <= 0:
                version = 1
            else:
                version = version + 1

        return RamFileManager.buildRamsesFileName(
            ramsesFileNameDict['projectID'],
            ramsesFileNameDict['ramStep'],
            ramsesFileNameDict['extension'],
            ramsesFileNameDict['ramType'],
            ramsesFileNameDict['objectShortName'],
            ramsesFileNameDict['resourceStr'],
            version,
            ramsesFileNameDict['state']
        )

    @staticmethod
    def buildRamsesFileName( project , step , ext , ramType = 'G' , objectShortName = '' , resourceStr = "" , version = -1 , version_prefix = 'v' ):
        """Used to build a filename respecting Ramses' naming conventions.

        The name will look like this:
            projShortName_ramType_objectShortName_stepShortName_resourceStr_versionBlock.extension
        Ramses names follow these rules:
        - ramType can be one of the following letters: A (asset), S (shot), G (general).
        - there is an objectShortName only for assets and shots.
        - resourceStr is optional. It only serves to differentiate the main working file and its resources, that serve as secondary working files.
        - versionBlock is optional. It's made of an optional version prefix ('wip', 'v', 'pub', ...) followed by a version number.
            Version prefixes consist of all the available states' shortnames ( see Ramses.getStates() ) and some additional prefixes ( see Ramses._versionPrefixes ).
        For more information on Ramses' naming conventions (such as length limitation, allowed characters...), refer to the documentation.

        If "ext" does not start with a '.' it will be prepended.

        Args:
            project: str
            step: str
            ext: str
                The Extension. If it does not start with a '.', it will be prepended.
            ramType: str
                One of the following: 'A' (asset), 'S' (shot), 'G' (general)
            objectShortName: str
            resourceStr: str
                Serves to differentiate the main working file and its resources, that serve as secondary working files.
            version: int
            version_prefix: str

        Returns: str
        """

        resourceStr = RamFileManager._fixResourceStr( resourceStr )
        ramsesFileName = project + '_' + ramType

        if ramType in ('A', 'S'):
            ramsesFileName = ramsesFileName + '_' + objectShortName

        ramsesFileName = ramsesFileName + '_' + step

        if resourceStr != '':
            ramsesFileName = ramsesFileName + '_' + resourceStr

        if version != -1:
            ramsesFileName = ramsesFileName + '_' + version_prefix
            ramsesFileName = ramsesFileName + intToStr(version)
        
        if ext != '':
            if not ext.startswith('.'):
                ext = '.' + ext
            ramsesFileName = ramsesFileName + ext

        return ramsesFileName

    @staticmethod
    def decomposeRamsesFileName( ramsesFileName ):
        """Used on files that respect Ramses' naming convention: it separates the name into blocks (one block for the project's shortname, one for the step, one for the extension...)

        A Ramses filename can have all of these blocks:
        - projectID_ramType_objectShortName_ramStep_resourceStr_versionBlock.extension
        - ramType can be one of the following letters: A (asset), S (shot), G (general).
        - there is an objectShortName only for assets and shots.
        - resourceStr is optional. It only serves to differentiate the main working file and its resources, that serve as secondary working files.
        - versionBlock is optional. It's made of two blocks: an optional version prefix, also named state, followed by a version number.
            Version prefixes consist of all the available states' shortnames ( see Ramses.getStates() ) and some additional prefixes ( see Ramses._versionPrefixes ). Eg. 'wip', 'v', ...
        For more information on Ramses' naming conventions (such as length limitation, forbidden characters...), refer to the documentation.

        Arg:
            ramsesFileName: str
        
        Returns: dict or None
            If the file does not match Ramses' naming convention, returns None.
            Else, returns a dictionary made of all the blocks: {"projectId", "ramType", "objectShortName", "ramStep", "resourceStr", "state", "version", "extension"}
        """
        if type(ramsesFileName) != str:
            print("The given filename is not a str.")
            return None

        splitRamsesName = re.match(RamFileManager._getRamsesNameRegEx(), ramsesFileName)

        if splitRamsesName == None:
            return None

        ramType = ''
        objectShortName = ''

        if splitRamsesName.group(2) in ('A', 'S'):
            ramType = splitRamsesName.group(2)
            objectShortName = splitRamsesName.group(3)
        else:
            ramType = splitRamsesName.group(4)

        optionalBlocks = ['', '', '', '']
        for i in range(0, 4):
            if splitRamsesName.group(i + 6) != None:
                optionalBlocks[i] = splitRamsesName.group( i + 6)

        if optionalBlocks[2] == '':
            optionalBlocks[2] = -1
        else:
            optionalBlocks[2] = int(optionalBlocks[2])

        blocks = {
            "projectID": splitRamsesName.group(1),
            "ramType": ramType,
            "objectShortName": objectShortName,
            "ramStep": splitRamsesName.group(5),
            "resourceStr": optionalBlocks[0],
            "state": optionalBlocks[1],
            "version": optionalBlocks[2],
            "extension": optionalBlocks[3],
        }

        return blocks

    @staticmethod
    def _isRamsesItemFoldername( n):
        """Low-level, undocumented. Used to check if a given folder respects Ramses' naming convention for items' root folders.
        
        The root folder should look like this:
            projectID_ramType_objectShortName

        Returns: bool
        """
        if re.match('^([a-z0-9+-]{1,10})_[ASG]_([a-z0-9+-]{1,10})$' , n , re.IGNORECASE): return True
        return False

    @staticmethod
    def _getRamsesNameRegEx():
        """Low-level, undocumented. Used to get a Regex to check if a file matches Ramses' naming convention.
        """
        regexStr = RamFileManager._getVersionRegExStr()

        regexStr = '^([a-z0-9+-]{1,10})_(?:([AS])_([a-z0-9+-]{1,10})|(G))_([a-z0-9+-]{1,10})(?:_((?!(?:' + regexStr + ')?[0-9]+)[a-z0-9+\\s-]+))?(?:_(' + regexStr + ')?([0-9]+))?\\.([a-z0-9.]+)$'

        regex = re.compile(regexStr, re.IGNORECASE)
        return regex

    @staticmethod
    def _getVersionRegExStr():
        """Low-level, undocumented. Used to get a Regex str that can be used to identify version blocks.

        A version block is composed of an optional version prefix and a version number.
        'wip002', 'v10', '1002' are version blocks; '002wip', '10v', 'v-10' are not.\n
        Version prefixes consist of all the available states' shortnames ( see Ramses.getStates() ) and some additional prefixes ( see Ramses._versionPrefixes ).
        """
        
        ramses = Ramses.instance()
        prefixes = ramses.settings().versionPrefixes

        for state in ramses.states():
            prefixes.append( state.shortName() )

        regexStr = ''
        for prefix in prefixes[0:-1]:
            regexStr = regexStr + prefix + '|'
        regexStr = regexStr + prefixes[-1]
        return regexStr

    @staticmethod
    def _fixResourceStr( resourceStr ):
        """Low-level, undocumented. Used to remove all forbidden characters from a resource.

        Returns: str
        """
        forbiddenCharacters = {
            '"' : ' ',
            '_' : '-',
            '[' : '-',
            ']' : '-',
            '{' : '-',
            '}' : '-',
            '(' : '-',
            ')' : '-',
            '\'': ' ',
            '`' : ' ',
            '.' : '-',
            '/' : '-',
            '\\' : '-',
            ',' : ' ' 
            }

        fixedResourceStr = ''
        for char in resourceStr:
            if char in forbiddenCharacters:
                fixedResourceStr = fixedResourceStr + forbiddenCharacters[char]
            else:
                fixedResourceStr = fixedResourceStr + char
        return fixedResourceStr