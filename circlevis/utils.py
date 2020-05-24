from pathlib import Path

ROOT_PATH = Path(__file__).parent.parent.absolute()
def resource_path(path):
    """
    Get the resource path for a given file.

    Returns
    -------
    string
        The absolute path (as a string) to the given file.
        Return string because this function is almost always used in a ``QIcon``
        context, which does not accept a ``Path``.
    """

    return str(ROOT_PATH / "resources" / Path(path))
