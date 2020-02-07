from aqt import mw
from anki.hooks import addHook
from aqt.webview import AnkiWebView
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from aqt.utils import restoreGeom
from aqt.browser import *

def showTagsInfo(self, nids):
    if not self.card:
        return
    info = tagStats(nids)
    class CardInfoDialog(QDialog):
        silentlyClose = True

        def reject(self):
            saveGeom(self, "tagsList")
            return QDialog.reject(self)
    dialog = CardInfoDialog(self)
    layout = QVBoxLayout()
    layout.setContentsMargins(0,0,0,0)
    view = AnkiWebView()
    layout.addWidget(view)
    view.stdHtml(info)
    bb = QDialogButtonBox(QDialogButtonBox.Close)
    layout.addWidget(bb)
    bb.rejected.connect(dialog.reject)
    dialog.setLayout(layout)
    dialog.setWindowModality(Qt.WindowModal)
    dialog.resize(500, 400)
    restoreGeom(dialog, "tagsList")
    dialog.show()

def tagStats(nids):
    tags = dict()
    for nid in nids:
        note = mw.col.getNote(nid)
        for tag in note.tags:
            tags[tag] = tags.get(tag, 0) + 1
    l = [(nb, tag) for tag, nb in tags.items()]
    l.sort(reverse=True)
    html = ("""<table border=1>""" +
            "\n".join(f"<tr><td>{tag}</td><td>{nb}</td></tr>" for nb, tag in l) +
            """</table>""")
    return html
    

def setupMenu(browser):
    a = QAction("Number of tags", browser)
    a.setShortcut(QKeySequence("Ctrl+shift+t"))
    a.triggered.connect(lambda: showTagsInfo(browser, browser.selectedNotes()))
    browser.form.menu_Help.addAction(a)

addHook("browser.setupMenus", setupMenu)
