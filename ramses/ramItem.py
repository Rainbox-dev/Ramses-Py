import os

from .ramses import Ramses
from .ramObject import RamObject
from .ramStatus import RamStatus
from .ramStep import RamStep
from .ramSettings import FolderNames, ItemType, RamSettings
from .file_manager import RamFileManager
from .daemon_interface import RamDaemonInterface
from .logger import log, Log, LogLevel
from .utils import getObjectShortName

# Keep the daemon at hand
daemon = RamDaemonInterface.instance()

class RamItem( RamObject ):
    """
    Base class for RamAsset and RamShot.
    An item of the project, either an asset or a shot.
    """

    @staticmethod
    def fromDict( itemDict ):
        """Builds a RamItem from dict like the ones returned by the RamDaemonInterface"""

        i = RamItem(
            itemDict['name'],
            itemDict['shortName'],
            itemDict['folder'],
            itemDict['itemType']
        )
        return i

    @staticmethod
    def fromPath( fileOrFolderPath ): #TODO
        from .ramShot import RamShot
        from .ramAsset import RamAsset
        """Returns a RamAsset or RamShot instance built using the given path.
        The path can be any file or folder path from the asset 
        (a version file, a preview file, etc)

        Args:
            path (str)

        Returns:
            RamAsset or RamShot
        """

        #TODO Test general items
        #TODO Test from (step) folders and not only files

        saveFilePath = RamFileManager.getSaveFilePath( fileOrFolderPath )
        if saveFilePath is None:
            log( Log.PathNotFound, LogLevel.Critical )
            return None

        saveFolder = os.path.dirname( saveFilePath )
        itemFolder = saveFolder
        itemFolderName = os.path.basename( itemFolder )

        if not RamFileManager._isRamsesItemFoldername( itemFolderName ): # We're probably in a step subfolder
            itemFolder = os.path.dirname( saveFolder )
            itemFolderName = os.path.basename( itemFolder )
            if not RamFileManager._isRamsesItemFoldername( itemFolderName ): # Still wrong: consider it's a general item
                saveFileName = os.path.basename( saveFilePath )
                decomposedFileName = RamFileManager.decomposeRamsesFileName( saveFileName )
                if not decomposedFileName: # Wrong name, we can't do anything more
                    log (Log.MalformedName, LogLevel.Debug)
                    return None
                return RamItem(
                    itemName=decomposedFileName['resourceStr'],
                    itemShortName=decomposedFileName['objectShortName'],
                    itemFolder=saveFolder
                )

        

        folderBlocks = itemFolderName.split( '_' )
        typeBlock = folderBlocks[ 1 ]
        shortName = folderBlocks[ 2 ]

        if typeBlock == ItemType.ASSET: 
            # Get the group name
            assetGroupFolder = os.path.dirname( itemFolder )
            assetGroup = os.path.basename( assetGroupFolder )
            return RamAsset(
                assetName=shortName,
                assetShortName=shortName,
                assetFolder=itemFolder,
                assetGroupName=assetGroup
            )

        if typeBlock == ItemType.SHOT:
            return RamShot(
                shotName=shortName,
                shotShortName=shortName,
                shotFolder=itemFolder
            )

        

        log( "The given path does not belong to a shot nor an asset", LogLevel.Debug )
        return None

    def __init__( self, itemName, itemShortName, itemFolder="", itemType=ItemType.GENERAL ):
        """
        Args:
            itemName (str)
            itemShortName (str)
            itemFolder (str, optional): Defaults to "".
        """
        super().__init__( itemName, itemShortName )
        self._folderPath = itemFolder
        self._itemType = itemType

    def currentStatus( self, step, resource="" ):
        """The current status for the given step

        Args:
            step (RamStep or str): The step.
            resource (str, optional): The name of the resource. Defaults to "".

        Returns:
            RamStatus
        """
        # Check step, return shortName (str) or "" or raise TypeError:
        step = getObjectShortName( step )

        # If we're online, ask the client (return a dict)
        if Ramses.instance().online():
            replyDict = daemon.getCurrentStatus( self._shortName, self._name, step )
            # check if successful
            if daemon.checkReply( replyDict ):
                content = replyDict['content']
                status = RamStatus(
                    state=content['state'],
                    comment=content['comment'],
                    completionRatio=content['completionRatio'],
                    version=content['version'],
                    stateDate=content['date'],
                    user=content['user'],
                    )

                return status

        # If offline
        currentVersionPath = self.versionFilePath( step, resource )
        if currentVersionPath == None:
            log( "There was an error getting the latest version or none was found." )
            return None

        currentStatus = RamStatus.fromPath( currentVersionPath )

        return currentStatus

    # Do not document "type" and "assetGroup" arguments, they should stay hidden
    # (not needed in derived classes RamShot.folderPath() and RamAsset.folderPath())
    def folderPath( self, assetGroup="" ): #TODO : à vérifier
        """The absolute path to the folder containing the item, or to the step subfolder if provided

        Args:
            step (RamStep or str, optional): Defaults to "".

        Returns:
            str
        """

        if self._folderPath != "":
            return self._folderPath

        # If we're online, ask the client (return a dict)
        if Ramses.instance().online():
            if self._itemType == ItemType.SHOT:
                replyDict = daemon.getShot( self._shortName, self._name )
                # check if successful
                if daemon.checkReply( replyDict ):
                    return replyDict['content']['folder']
            elif self._itemType == ItemType.ASSET:
                replyDict = daemon.getAsset(( self._shortName, self._name ))
                # check if successful
                if daemon.checkReply( replyDict ):
                    return replyDict['content']['folder']
            else:
                return ""

        # Project
        project = Ramses.instance().currentProject()
        # Project path
        folderPath = project.folderPath()

        if self._itemType == ItemType.SHOT:
            # Go to shots
            folderPath = folderPath + '05-SHOTS'
            # Get the shot folder name
            shotFolderName = project.shortName() + '_S_' + self._shortName
            self._folderPath = folderPath + '/' + shotFolderName
            
            return self._folderPath
            
        if self._itemType == ItemType.ASSET:
            # Go to assets
            folderPath = folderPath + '04-ASSETS'
            # The asset folder name
            assetFolderName = project.shortName() + '_A_' + self._shortName
            
            if assetGroup == "": # Without groupname (which should never be the case), consider the asset folder is right there
                self._folderPath = folderPath + '/' + assetFolderName
                return self._folderPath
            
            # add the group
            folderPath = folderPath + '/' + assetGroup
            self._folderPath = folderPath + '/' + assetFolderName

            return self._folderPath
            
        return ""

    def stepPath(self, step, assetGroup=""):
        # Check step, return shortName (str) or "" or raise TypeError:
        step = getObjectShortName( step )

        folderPath = self.folderPath(assetGroup)
        if folderPath == "":
            return ""

        proj = RamFileManager.getProjectShortName( folderPath )

        return RamFileManager.buildPath((
            folderPath,
            proj + '_' + self._itemType + '_' + self.shortName + '_' + step
        ))

    def latestVersion( self, step, resource="", stateId="WIP"):
        """Returns the highest version number for the given state (wip, pub…).

        Args:
            step (RamStep or str)
            resource (str, optional): Defaults to "".
            stateId (str, optional): Defaults to "wip".

        Returns:
            int
        """
        # Check step, return shortName (str) or "" or raise TypeError:
        step = getObjectShortName( step )

        # Uniquement pour test
        # abc = Ramses.instance().daemonInterface().getCurrentStatus("SEA", "Sea", "ASSET")
        # print(abc)

        listWithState = []
 
        # If we're online, ask the client
        if Ramses.instance().online:
            folderPath = self.folderPath()
            # >>> e.g.  C:/Users/Megaport/Ramses/Projects/FPE/04 - ASSETS/Characters/FPE_A_TRI

            baseName = os.path.basename( folderPath )
            # >>> e.g.  FPE_A_TRI

            folderPath = folderPath + "/" + baseName + "_" + step + "/" + FolderNames().versions
            # >>> e.g.  C:/Users/Megaport/Ramses/Projects/FPE/04 - ASSETS/Characters/FPE_A_TRI/FPE_A_TRI_MOD/_versions

            filesList = os.listdir( folderPath )
            # >>> we get all the files in the -versions folder

            for files in filesList:
                if stateId.lower() in files.lower():
                    # search with stateId
                    listWithState.append(files)

            highestVersion = 0

            for filesWithState in listWithState:
                decomposedFoundFile = RamFileManager.decomposeRamsesFileName( filesWithState )

                if decomposedFoundFile == None:
                    continue
                if decomposedFoundFile["resourceStr"] != resource:
                    continue
                if decomposedFoundFile["version"] == '':
                    continue

                versionInt = int( decomposedFoundFile["version"] )
                if versionInt > highestVersion:
                    highestVersion = versionInt

            return highestVersion

        # Else check in the folders
        if self.folderPath == '':
            log( "The given item has no folderPath." )
            return None

        folderPath = Ramses.instance().currentProject().folderPath() + '/' + self.folderPath() #Makes it absolute

        if not os.path.isdir( folderPath ):
            log( "The given item's folder was not found.\nThis is the path that was checked:\n" + folderPath )
            return None
        if not isinstance( stateId, str ):
            raise TypeError( "State must be a str" )

        baseName = os.path.basename( self.folderPath() ) + '_' + step #Name without the resource str (added later)
        stepFolderPath = folderPath + '/' + baseName

        if os.path.isdir( stepFolderPath ) == False:
            log( "The folder for the following step: " + step + " has not been found." )
            return None
        if os.path.isdir( stepFolderPath + '/ramses_versions' ) == False:
            log( "ramses_versions directory has not been found" )
            return None

        foundFiles = os.listdir( stepFolderPath + '/ramses_versions' )
        highestVersion = 0

        for foundFile in foundFiles:
            if not os.path.isfile( stepFolderPath + '/ramses_versions/' + foundFile ): #This is in case the user has created folders in ramses_versions
                continue

            decomposedFoundFile = RamFileManager.decomposeRamsesFileName( foundFile )

            if decomposedFoundFile == None:
                continue
            if not foundFile.startswith( baseName ): #In case other assets have been misplaced here
                continue
            if decomposedFoundFile["resourceStr"] != resource:
                continue
            if decomposedFoundFile["version"] == '':
                continue
            if decomposedFoundFile["state"] != stateId:
                continue
            
            versionInt = int( decomposedFoundFile["version"] )
            if versionInt > highestVersion:
                highestVersion = versionInt

        return highestVersion

    def previewFolderPath( self, step ): #TODO: A vérifier...
        """Gets the path to the preview folder.
            Paths are relative to the root of the item folder.

        Args:
            step (RamStep or str)

        Returns:
            str
        """
        # Check step, return shortName (str) or "" or raise TypeError:
        step = getObjectShortName( step )

        folderPath = self.folderPath( step )
        if folderPath != None:
            return RamFileManager.buildPath( ( folderPath, RamSettings.instance().folderNames.preview ) )
        else:
            return ""

    def previewFilePaths( self, step, resource="" ): #TODO
        """Gets the list of file paths in the preview folder.
            Paths are relative to the root of the item folder.

        Args:
            step (RamStep or str)
            resource (str, optional): Defaults to "".

        Returns:
            list of str
        """
        # Check step, return shortName (str) or "" or raise TypeError:
        step = getObjectShortName( step )

        if self.folderPath == '':
            log( "The given item has no folderPath." )
            return None

        # Project
        project = Ramses.instance().currentProject()
        # Project path
        folderPath = project.folderPath()

        baseName = os.path.basename( self.folderPath() )
        folderPath = folderPath + "/" + self.folderPath()

        if not os.path.isdir( folderPath ):
            log( "The given item's folder was not found.\nThis is the path that was checked:\n" + folderPath )
            return None

        folderPath = folderPath + "/" + baseName + "_" + step

        if not os.path.isdir( folderPath + '/ramses_preview' ):
            log( "ramses_preview directory has not been found" )
            return None


        # print("*******************************************************")
        # EN COURS...
        # print("*******************************************************")

    def publishedFolderPath( self, step ): #TODO : à vérifier
        """Gets the path to the publish folder.
        Paths are relative to the root of the item folder.

        Args:
            step (RamStep or str)   

        Returns:
            str
        """
        # Check step, return shortName (str) or "" or raise TypeError:
        step = getObjectShortName( step )

        folderPath = self.folderPath( step )
        if folderPath != None:
            return RamFileManager.buildPath( ( folderPath, RamSettings.instance().folderNames.publish ) )
        else:
            return ""

    def publishedFilePaths( self, step, resource="" ):
        """Gets the list of file paths in the publish folder.
            Paths are relative to the root of the item folder.

        Args:
            step (RamStep or str)
            resource (str, optional): Defaults to "".

        Returns:
            list of str
        """
        # Check step, return shortName (str) or "" or raise TypeError:
        step = getObjectShortName( step )

        if self.folderPath == '':
            print( "The given item has no folderPath." )
            return None

        baseName = os.path.basename( self.folderPath() )
        folderPath = Ramses.instance().currentProject().folderPath + '/' + self.folderPath()

        if not os.path.isdir( folderPath ):
            print( "The given item's folder was not found.\nThis is the path that was checked:\n" + folderPath )
            return None
        
        folderPath = folderPath + '/' + baseName + '_' + step
        if not os.path.isdir( folderPath + '/ramses_publish' ):
            print( "ramses_publish directory has not been found" )
            return None

        foundFiles = os.listdir( folderPath + '/ramses_publish' )
        foundFilePath = ""
        publishFiles = []

        for foundFile in foundFiles:
            if os.path.isdir( foundFile ):
                continue

            blocks = RamFileManager.decomposeRamsesFileName( foundFile )

            if blocks == None:
                continue
            if blocks[ "resourceStr" ] != resource:
                continue
            if not foundFile.startswith( baseName ):
                continue

            #Building file path relative to root of item folder
            foundFilePath = baseName + '_' + step + '/ramses_publish/' + foundFile
            publishFiles.append(foundFilePath)
            
        return publishFiles

    def versionFolderPath( self, step ): #TODO : à vérifier
        """Path to the version folder relative to the item root folder

        Args:
            step (RamStep)

        Returns:
            str
        """
        # Check step, return shortName (str) or "" or raise TypeError:
        step = getObjectShortName( step )

        folderPath = ""
        if self._itemType == ItemType.GENERAL:
            folderPath = self.folderPath()
        else:
            folderPath = self.stepPath( step )

        if folderPath != "":
            return RamFileManager.buildPath( ( folderPath, RamSettings.instance().folderNames.versions ) )
        else:
            return ""

    def versionFilePath( self, step, resource="" ):
        """Latest version file path

        Args:
            step (RamStep or str)
            resource (str, optional): Defaults to "".

        Returns:
            str
        """
        # Check step, return shortName (str) or "" or raise TypeError:
        step = getObjectShortName( step )

        versionFolderPath = self.versionFolderPath( step )

        if not os.path.isdir( versionFolderPath ):
            return ""

        foundFiles = os.listdir( versionFolderPath )
        highestVersion = 0
        highestVersionFileName = ''

        baseName = os.path.basename( self.folderPath() )

        for foundFile in foundFiles:
            # In case the user has created folders in ramses_versions
            if not os.path.isfile( versionFolderPath + foundFile ): 
                continue
            # In case other assets have been misplaced here
            if not foundFile.startswith( baseName ):
                continue

            decomposedFoundFile = RamFileManager.decomposeRamsesFileName( foundFile )

            if decomposedFoundFile is None:
                continue
            if decomposedFoundFile[ "resourceStr" ] != resource:
                continue
            if decomposedFoundFile[ "version" ] < 0:
                continue
            
            versionInt = decomposedFoundFile["version"]
            if versionInt > highestVersion:
                highestVersion = versionInt
                highestVersionFileName = foundFile

        if highestVersionFileName == '':
            return ''

        highestVersionFilePath = RamFileManager.buildPath((
            versionFolderPath,
            highestVersionFileName
        ))

        return highestVersionFilePath

    def wipFolderPath( self, step ): #TODO
        """Path to the WIP folder relative to the item root folder

        Args:
            step (RamStep or str)

        Returns:
            str
        """
        # Check step, return shortName (str) or "" or raise TypeError:
        step = getObjectShortName( step )

        if self.folderPath == '':
            print( "The given item has no folderPath." )
            return None

        pass

    def wipFilePath( self, step, resource="" ): 
        """Current wip file path relative to the item root folder

        Args:
            step (RamStep or str)
            resource (str, optional): Defaults to "".

        Returns:
            str
        """
        # Check step, return shortName (str) or "" or raise TypeError:
        step = getObjectShortName( step )

        if self.folderPath == '':
            print( "The given item has no folderPath." )
            return None

        baseName = os.path.basename( self.folderPath() ) + '_' + step._shortName

        if step.fileType == None:
            raise Exception( "The given step has no fileType; cannot build the path towards the working file (missing extension)." )

        filePath = baseName + '/' + baseName + '.' + step.fileType.extension

        return filePath

    def isPublished( self, step, resource="" ):
        """Convenience function to check if there are published files in the publish folder.
            Equivalent to len(self.publishedFilePaths(step, resource)) > 0

        Args:
            step (RamStep)
            resource (str, optional): Defaults to "".

        Returns:
            bool
        """
        # Check step, return shortName (str) or "" or raise TypeError:
        step = getObjectShortName( step )

        result = self.publishedFilePaths( step, resource )
        if result == None:
            return False
        return len( result ) > 0

    def setStatus( self, status, step ): #TODO
        """Sets the current status for the given step

        Args:
            status (RamStatus)
            step (RamStep)
        """
        # Check step, return shortName (str) or "" or raise TypeError:
        step = getObjectShortName( step )

        pass

    def itemType( self ):
        """Returns the type of the item"""
        return self._itemType

    def steps( self ): #TODO : à vérifier
        """Returns the steps used by this asset"""

        stepsList = []

        # If we're online, ask the client (return a dict)
        if Ramses.instance().online():
            replyDict = daemon.getCurrentStatuses( self._shortName, self._name, self._itemType )
            # check if successful
            if daemon.checkReply( replyDict ):
                content = replyDict['content']
                statusList = content['status']
                for status in statusList:
                    stepsList.append( status['step'] )

        return stepsList

        # Else check in the folders

        # sinon aller voir les sous-dossiers dans folderPath()
        # PROJECTID_A_TRISTAN_DESIGN
        # -> split('_'), si 4 éléments, le dernier est le shortname
        # -> RamStep depuis le shortName
        # -> renvoyer la liste des ramsteps
