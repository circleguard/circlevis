from pathlib import Path
import sys

ROOT_PATH = Path(__file__).parent.absolute()
def resource_path(path):
    """
    Get the resource path for a given file.

    This location changes if the program is run from an application built with
    pyinstaller.

    Returns
    -------
    string
        The absolute path (as a string) to the given file, after taking into
        account whether we are running in a development setting.
        Return string because this function is almost always used in a ``QIcon``
        context, which does not accept a ``Path``.
    """

    if hasattr(sys, '_MEIPASS'): # being run from a pyinstall'd app
        # this will only work if the consumer is using a circlevis hook to add
        # the circlevis resource files to the pyinstall'd app.
        # As we're basically only providing it for circleguard, that's fine.
        return str(Path(sys._MEIPASS) / "circlevis" / "resources" / Path(path)) # pylint: disable=no-member
    return str(ROOT_PATH / "resources" / Path(path))
