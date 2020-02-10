from aqt import mw
from anki.hooks import addHook
from aqt.webview import AnkiWebView
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from aqt.utils import restoreGeom
from aqt.browser import *
import math
from .config import getUserOption, setUserOption

def showTagsInfoHighlight(self, cids):
    default = getUserOption("default search", "")
    highlights = getOnlyText("Which tags to highlight? (space separated)", default=default)
    if getUserOption("update default", False):
        setUserOption("default search", highlights)
    showTagsInfo(self, cids, highlights)

def showTagsInfo(self, cids, highlights=""):
    if not self.card:
        return
    info = tagStats(cids, highlights)
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

def tagStats(cids, highlights=""):
    highlights = highlights.lower()
    highlights = [highlight for highlight in highlights.split(" ") if highlight]
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
        highlighted = False
        lowerTag = tag.lower()
        for highlight in highlights:
            if highlight in lowerTag:
                highlighted = True
                break
        highlightColor = getUserOption("highlight color", "yellow")
        htmlTag = f"""<span style="background-color:{highlightColor}">{tag}</span>""" if highlighted else tag
        percentOfCardsWithThisTagWhichAreSelected = str(round((nb*100)/nbCardWithThisTag))+"%" if nbCardWithThisTag else "Error: no card with this tag in the fcollection."
        percentOfSelectedCardsWithThisTag = str(round((nb*100)/nbCards))+"%" if nbCardWithThisTag else "Error: no card with this tag in the collection."
        table.append((nb, htmlTag, percentOfSelectedCardsWithThisTag, percentOfCardsWithThisTagWhichAreSelected))
    html = ("""<table border=1>""" +
            "<tr><td></td><td width=\"25px\"># Card w/Tags</td><td width=\"25px\">% Cards Selected</td><td width=\"25px\">% Tags Covered</td>" +
            "\n".join(f"""<tr><td>{tag}</td><td>{nb}</td><td>{percentOfSelectedCardsWithThisTag}</td><td>{percentOfCardsWithThisTagWhichAreSelected}</td></tr>"""
                      for nb, tag, percentOfSelectedCardsWithThisTag, percentOfCardsWithThisTagWhichAreSelected in table) +
            """</table>""")
    return html
    

def setupMenu(browser):
    a = QAction("Number of tags", browser)
    a.setShortcut(QKeySequence("Ctrl+t"))
    a.triggered.connect(lambda: showTagsInfo(browser, browser.selectedCards()))
    browser.form.menu_Help.addAction(a)
    a = QAction("and highlight", browser)
    a.setShortcut(QKeySequence("Ctrl+shift+t"))
    a.triggered.connect(lambda: showTagsInfoHighlight(browser, browser.selectedCards()))
    browser.form.menu_Help.addAction(a)

addHook("browser.setupMenus", setupMenu)
