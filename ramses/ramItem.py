import os

from .ramses import Ramses
from .ramObject import RamObject
from .ramStatus import RamStatus
from .ramStep import RamStep
from .ramSettings import FolderNames
from .file_manager import RamFileManager
from .daemon_interface import RamDaemonInterface
from .logger import log, Log, LogLevel

# Keep the daemon at hand
daemon = RamDaemonInterface.instance()

class ItemType():
    GENERAL='G'
    ASSET='A'
    SHOT='S'

class RamItem( RamObject ):
    """
    Base class for RamAsset and RamShot.
    An item of the project, either an asset or a shot.
    """

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

    def currentStatus( self, step, resource="" ): #TODO if online
        """The current status for the given step

        Args:
            step (RamStep or str): The step.
            resource (str, optional): The name of the resource. Defaults to "".

        Returns:
            RamStatus
        """

        # If we're online, ask the client (return a dict)
        if Ramses.instance().online():
            statusDict = daemon.getCurrentStatus( self._shortName, self._name )
            # check if successful
            if daemon.checkReply( statusDict ):
                content = statusDict['content']
                foundStatus = content['status']
                log(foundStatus)
                # manque le type !! Comment mettre ASSET !?

            return None

        # If offline
        currentVersionPath = self.versionFilePath( step, resource )
        if currentVersionPath == None:
            log( "There was an error getting the latest version or none was found." )
            return None

        currentVersionPath = self._folderPath + '/' + currentVersionPath
        currentVersionPath = Ramses.instance().currentProject().absolutePath( currentVersionPath )

        currentStatus = RamStatus.getFromPath( currentVersionPath )

        return currentStatus

    # Do not document "type" and "assetGroup" arguments, they should stay hidden
    # (not needed in derived classes RamShot.folderPath() and RamAsset.folderPath())
    def folderPath( self, itemType, step="", assetGroup="" ):
        """The absolute path to the folder containing the asset, or to the step subfolder if provided

        Args:
            step (RamStep or str, optional): Defaults to "".

        Returns:
            str
        """
        if self._folderPath != "":
            return self._folderPath

        # Project
        project = Ramses.instance().currentProject()
        # Project path
        folderPath = project.folderPath()

        if itemType == "SHOT":
            # Go to shots
            folderPath = folderPath + '05-SHOTS'
            # Get the shot folder name
            shotFolderName = project.shortName() + '_S_' + self._shortName
            self._folderPath = folderPath + '/' + shotFolderName
            
            if step == "": # Return the base shot folder
                return self._folderPath
            
            return self._folderPath + '/' + shotFolderName + '_' + step # add the step subfolder

        if itemType == "ASSET":
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

            if step == "": # Return the base asset folder
                return self._folderPath
            
            return self._folderPath + '/' + assetFolderName + '_' + step # add the step subfolder

        return ""

    def latestVersion( self, step, resource="", stateId="WIP"):
        """Returns the highest version number for the given state (wip, pub…).

        Args:
            step (RamStep or str)
            resource (str, optional): Defaults to "".
            stateId (str, optional): Defaults to "wip".

        Returns:
            int
        """

        # Uniquement pour test
        # abc = Ramses.instance.daemonInterface().getCurrentStatus("SEA", "Sea", "ASSET")
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

        if isinstance( step, str ):
            stepShortName = step
        elif isinstance( step, RamStep ):
            stepShortName = step.shortName
        else:
            raise TypeError( "Step must be a str or an instance of RamStep" )

        baseName = os.path.basename( self._folderPath ) + '_' + stepShortName #Name without the resource str (added later)
        stepFolderPath = folderPath + '/' + baseName

        if os.path.isdir( stepFolderPath ) == False:
            log( "The folder for the following step: " + stepShortName + " has not been found." )
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

    def previewFolderPath( self, step ): #TODO
        """Gets the path to the preview folder.
            Paths are relative to the root of the item folder.

        Args:
            step (RamStep or str)

        Returns:
            str
        """
        pass

    def previewFilePaths( self, step, resource="" ): #TODO
        """Gets the list of file paths in the preview folder.
            Paths are relative to the root of the item folder.

        Args:
            step (RamStep or str)
            resource (str, optional): Defaults to "".

        Returns:
            list of str
        """

        if isinstance( step, str ):
            stepShortName = step
        elif isinstance( step, RamStep ):
            stepShortName = step.shortName
        else:
            raise TypeError( "Step must be a str or an instance of RamStep" )

        if self.folderPath == '':
            log( "The given item has no folderPath." )
            return None

        # Project
        project = Ramses.instance().currentProject()
        # Project path
        folderPath = project.folderPath()

        baseName = os.path.basename( self._folderPath )
        folderPath = folderPath + "/" + self._folderPath

        if not os.path.isdir( folderPath ):
            log( "The given item's folder was not found.\nThis is the path that was checked:\n" + folderPath )
            return None

        folderPath = folderPath + "/" + baseName + "_" + stepShortName

        if not os.path.isdir( folderPath + '/ramses_preview' ):
            log( "ramses_preview directory has not been found" )
            return None


        # print("*******************************************************")
        # EN COURS...
        # print("*******************************************************")

    def publishedFolderPath( self, step ): #TODO
        """Gets the path to the publish folder.
        Paths are relative to the root of the item folder.

        Args:
            step (RamStep or str)   

        Returns:
            str
        """
        pass

    def publishedFilePaths( self, step, resource="" ):
        """Gets the list of file paths in the publish folder.
            Paths are relative to the root of the item folder.

        Args:
            step (RamStep or str)
            resource (str, optional): Defaults to "".

        Returns:
            list of str
        """

        if isinstance( step, str ):
            stepShortName = step
        elif isinstance( step, RamStep ):
            stepShortName = step.shortName
        else:
            raise TypeError( "Step must be a str or an instance of RamStep" )

        if self.folderPath == '':
            print( "The given item has no folderPath." )
            return None

        baseName = os.path.basename( self._folderPath )
        folderPath = Ramses.instance().currentProject().folderPath + '/' + self.folderPath

        if not os.path.isdir( folderPath ):
            print( "The given item's folder was not found.\nThis is the path that was checked:\n" + folderPath )
            return None
        
        folderPath = folderPath + '/' + baseName + '_' + stepShortName
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
            foundFilePath = baseName + '_' + stepShortName + '/ramses_publish/' + foundFile
            publishFiles.append(foundFilePath)
            
        return publishFiles

    def versionFolderPath( self, step ): #TODO
        """Path to the version folder relative to the item root folder

        Args:
            step (RamStep)

        Returns:
            str
        """
        pass

    def versionFilePath( self, step, resource="" ): #TODO if online
        """Latest version file path relative to the item root folder

        Args:
            step (RamStep)
            resource (str, optional): Defaults to "".

        Returns:
            str
        """ 

        # If we're online, ask the client
        if Ramses.instance().online():
            #TODO ask the client
            return None
        
        # Else check in the folders
        # It is basically the same as getLatestVersion. Only difference is that it does not take the stateId into account
        # and returns the path instead of the version number.
        if self.folderPath == '':
            print( "The given item has no folderPath." )
            return None

        folderPath = Ramses.instance().currentProject().absolutePath( self.folderPath )

        if not os.path.isdir( folderPath ):
            print( "The given item's folder was not found.\nThis is the path that was checked:\n" + folderPath )
            return None

        if isinstance( step, str ):
            stepShortName = step
        elif isinstance( step, RamStep ):
            stepShortName = step.shortName
        else:
            raise TypeError( "Step must be a str or an instance of RamStep" )

        baseName = os.path.basename( self._folderPath ) + '_' + stepShortName # Name without the resource str (added later)
        stepFolderPath = folderPath + '/' + baseName

        if os.path.isdir( stepFolderPath ) == False:
            print( "The folder for the following step: " + stepShortName + " has not been found." )
            return None
        if os.path.isdir( stepFolderPath + '/ramses_versions' ) == False:
            print( "ramses_versions directory has not been found" )
            return None

        foundFiles = os.listdir( stepFolderPath + '/ramses_versions' )
        highestVersion = 0
        highestVersionFileName = ""

        for foundFile in foundFiles:
            if not os.path.isfile( stepFolderPath + '/ramses_versions/' + foundFile ): # This is in case the user has created folders in ramses_versions
                continue

            decomposedFoundFile = RamFileManager.decomposeRamsesFileName( foundFile )

            if decomposedFoundFile == None:
                continue
            if not foundFile.startswith( baseName ): # In case other assets have been misplaced here
                continue
            if decomposedFoundFile[ "resourceStr" ] != resource:
                continue
            if decomposedFoundFile[ "version" ] == '':
                continue
            
            versionInt = int( decomposedFoundFile["version"] )
            if versionInt > highestVersion:
                highestVersion = versionInt
                highestVersionFileName = foundFile

        if highestVersionFileName == '':
            print( "No version was found" )
            return None

        highestVersionFilePath = baseName + "/ramses_versions/" + highestVersionFileName

        return highestVersionFilePath

    def wipFolderPath( self, step ): #TODO
        """Path to the WIP folder relative to the item root folder

        Args:
            step (RamStep or str)

        Returns:
            str
        """
        pass

    def wipFilePath( self, step, resource="" ): 
        """Current wip file path relative to the item root folder

        Args:
            step (RamStep or str)
            resource (str, optional): Defaults to "".

        Returns:
            str
        """
        if self.folderPath == '':
            print( "The given item has no folderPath." )
            return None

        if not isinstance(step, RamStep):
            raise TypeError( "Step must be an instance of RamStep" )

        baseName = os.path.basename( self._folderPath ) + '_' + step._shortName

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
        pass

    def itemType( self ):
        """Returns the type of the item"""
        return self._itemType

    @staticmethod
    def getFromPath( path ): #TODO
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

        #TODO TEST and build general items (which are stored anywhere, just build from savename and folder)

        itemStepFolder = os.path.dirname( RamFileManager.getSaveFilePath( path ) )
        itemFolder = os.path.dirname( itemStepFolder )
        print( itemFolder )

        if not os.path.isdir( itemFolder ):
            if Ramses.instance().currentProject() is None:
                log( Log.NoProject, LogLevel.Debug )
                log( Log.PathNotFound, LogLevel.Debug )
                return None

            itemFolder = Ramses.instance().currentProject().absolutePath( itemFolder )
            if not os.path.isdir( itemFolder ):
                log( Log.PathNotFound, LogLevel.Debug )
                return None

        folderName = os.path.basename( itemFolder )

        if not RamFileManager._isRamsesItemFoldername( folderName ):
            log( "The given folder does not respect Ramses' naming convention", LogLevel.Debug )
            return None
        
        folderBlocks = folderName.split( '_' )
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
