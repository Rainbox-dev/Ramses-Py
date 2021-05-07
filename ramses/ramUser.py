from .ramObject import RamObject
from .ramSettings import RamSettings

class UserRole():
    STANDARD = 0
    LEAD = 1
    PROJECT_ADMIN = 2
    ADMIN = 3

class RamUser( RamObject ):
    """The class representing users."""

    @staticmethod
    def fromDict( userDict ):
        """Builds a RamUser from dict like the ones returned by the RamDaemonInterface"""

        u = RamUser(
            userDict['name'],
            userDict['shortName'],
            userDict['folderPath'],
            userDict['role']
        )
        return u

    def __init__( self, userName, userShortName, userFolderPath="", role=UserRole.STANDARD ):
        """
        Args:
            userName (str)
            userShortName (str)
            userFolderPath (str, optional): Defaults to "".
            role (str, optional): (Read-only) enumerated value. Defaults to 'STANDARD'.
                'ADMIN', 'PROJECT_ADMIN', 'LEAD', or 'STANDARD'
        """
        super().__init__( userName, userShortName )
        self._folderPath = userFolderPath
        self._role = role

    def role( self ):
        """
        Returns:
            (Read-only) enumerated value: 'ADMIN', 'PROJECT_ADMIN', 'LEAD', or 'STANDARD'
        """
        return self._role

    def configPath( self ): 
        """The path to the Config folder

        Arguments:
            absolute: bool

        Returns:
            str
        """

        path = RamSettings.instance().folderNames.userConfig
        return self.folderPath() + "/" + path

    def folderPath( self ):
        """The absolute path to the user folder

        Returns:
            str
        """
        return self._folderPath

