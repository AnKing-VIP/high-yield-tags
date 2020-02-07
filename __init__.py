from aqt import mw
from anki.hooks import addHook
from aqt.webview import AnkiWebView
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from aqt.utils import restoreGeom
from aqt.browser import *
import math

def showTagsInfo(self, cids):
    if not self.card:
        return
    info = tagStats(cids)
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
    restoreGeom(dialog, "tagsList")
    dialog.show()

def tagStats(cids):
    tags = dict()
    nbCards = len(cids)
    for cid in cids:
        card = mw.col.getCard(cid)
        note = card.note()
        for tag in note.tags:
            tags[tag] = tags.get(tag, 0) + 1
    l = [(nb, tag) for tag, nb in tags.items()]
    l.sort(reverse=True)
    table = []
    for nb, tag in l:
        nbCardWithThisTag = len(mw.col.findCards(f""" "tag:{tag}" """))
        percent = str(round((nb*100)/nbCardWithThisTag))+"%" if nbCardWithThisTag else "Error: no card with this tag in the collection."
        table.append((nb,tag,percent))
    html = ("""<table border=1>""" +
            "\n".join(f"""<tr><td>{tag}</td><td>{nb}</td><td>{percent}</td></tr>""" for nb, tag, percent in table) +
            """</table>""")
    return html
    

def setupMenu(browser):
    a = QAction("Number of tags", browser)
    a.setShortcut(QKeySequence("Ctrl+shift+t"))
    a.triggered.connect(lambda: showTagsInfo(browser, browser.selectedCards()))
    browser.form.menu_Help.addAction(a)

addHook("browser.setupMenus", setupMenu)
