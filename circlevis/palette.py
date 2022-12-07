from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtCore import Qt

# Defining this as a global at the module level (instead of instantiating a new
# palette on demand) causes the colors for ceratin roles to not be respected by
# Qt. In particular ColorRole.Text is set to black if dark_palette is defined
# at the module level, even when we set ColorRole.Text to
# Qt.GlobalColor.white.
# My only guess here is some sort of pointer sharing weirdness on qt's side
# which messes with reusing a palette, or even defining it at a module level.

def get_dark_palette():
    accent = QColor(71, 174, 247)
    dark_palette = QPalette()

    cg = QPalette.ColorGroup
    cr = QPalette.ColorRole
    dark_palette.setColor(cg.Normal,     cr.Window, QColor(53, 53, 53))
    dark_palette.setColor(cg.Normal,     cr.WindowText, Qt.GlobalColor.white)
    dark_palette.setColor(cg.Normal,     cr.Base, QColor(25, 25, 25))
    dark_palette.setColor(cg.Normal,     cr.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(cg.Normal,     cr.ToolTipBase, QColor(53, 53, 53))
    dark_palette.setColor(cg.Normal,     cr.ToolTipText, Qt.GlobalColor.white)
    dark_palette.setColor(cg.Normal,     cr.Text, Qt.GlobalColor.white)
    dark_palette.setColor(cg.Normal,     cr.Button, QColor(53, 53, 53))
    dark_palette.setColor(cg.Normal,     cr.ButtonText, Qt.GlobalColor.white)
    dark_palette.setColor(cg.Normal,     cr.BrightText, Qt.GlobalColor.red)
    dark_palette.setColor(cg.Normal,     cr.Highlight, accent)
    # also change for inactive (when app is in background)
    dark_palette.setColor(cg.Inactive,   cr.Window, QColor(53, 53, 53))
    dark_palette.setColor(cg.Inactive,   cr.WindowText, Qt.GlobalColor.white)
    dark_palette.setColor(cg.Inactive,   cr.Base, QColor(25, 25, 25))
    dark_palette.setColor(cg.Inactive,   cr.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(cg.Inactive,   cr.ToolTipBase, QColor(53, 53, 53))
    dark_palette.setColor(cg.Inactive,   cr.ToolTipText, Qt.GlobalColor.white)
    dark_palette.setColor(cg.Inactive,   cr.Text, Qt.GlobalColor.white)
    dark_palette.setColor(cg.Inactive,   cr.Button, QColor(53, 53, 53))
    dark_palette.setColor(cg.Inactive,   cr.ButtonText, Qt.GlobalColor.white)
    dark_palette.setColor(cg.Inactive,   cr.BrightText, Qt.GlobalColor.red)
    dark_palette.setColor(cg.Inactive,   cr.Highlight, accent)

    dark_palette.setColor(cg.Inactive,   cr.Highlight, Qt.GlobalColor.lightGray)
    dark_palette.setColor(cg.Normal,     cr.HighlightedText, Qt.GlobalColor.black)
    dark_palette.setColor(cg.Disabled,   cr.Text, Qt.GlobalColor.darkGray)
    dark_palette.setColor(cg.Disabled,   cr.ButtonText, Qt.GlobalColor.darkGray)
    dark_palette.setColor(cg.Disabled,   cr.Highlight, Qt.GlobalColor.darkGray)
    dark_palette.setColor(cg.Disabled,   cr.Base, QColor(53, 53, 53))
    dark_palette.setColor(cg.Normal,     cr.Link, accent)
    dark_palette.setColor(cg.Normal,     cr.LinkVisited, accent)
    dark_palette.setColor(cg.Inactive,   cr.Link, accent)
    dark_palette.setColor(cg.Inactive,   cr.LinkVisited, accent)

    return dark_palette
