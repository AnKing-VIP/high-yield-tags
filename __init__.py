import math

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from .consts import DECK_DYN
from aqt import gui_hooks, mw
from aqt.browser import *
from aqt.utils import restoreGeom, getText
from aqt.webview import AnkiWebView

from .config import getUserOption, setUserOption

selected_tags = set()

def showTagsInfoHighlight(self, cids):
    default = getUserOption("default search")
    highlights, ret = getText(
        "Which tags to highlight? (space separated)", default=default)
    if not ret:
        return
    default_percent = getUserOption("default percent to box")
    highlights_percent, ret = getText(
        "Highlights values above x %", default=str(default_percent))
    if not ret:
        return
    if getUserOption("update default"):
        setUserOption("default search", highlights)
    showTagsInfo(self, cids, highlights, highlights_percent)


def showTagsInfo(self, cids, highlights="", highlights_percent=50):
    if not self.card:
        return
    info = tagStats(cids, highlights, highlights_percent)

    class CardInfoDialog(QDialog):
        silentlyClose = True

        def reject(self):
            saveGeom(self, "tagsList")
            if selected_tags:
                (d_name, ret) = getText("Deck name for this tag selection", parent=self)
                if d_name and ret:
                    did = mw.col.decks.newDyn(d_name)
                    deck = mw.col.decks.get(did)
                    assert(deck["dyn"] == DECK_DYN)
                    search = " or ".join(f"""("tag:{tag}")""" for tag in selected_tags)
                    search = f"({search}) is:due "
                    deck["terms"][0][0] = search
                    deck["terms"][0][1] = 99999
                    mw.col.decks.save(deck)
                    mw.col.sched.rebuildDyn(did)
                    mw.reset()


            return QDialog.reject(self)
    dialog = CardInfoDialog(self)
    layout = QVBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    view = AnkiWebView()
    layout.addWidget(view)
    view.stdHtml(info)
    bb = QDialogButtonBox(QDialogButtonBox.Close)
    layout.addWidget(bb)
    bb.rejected.connect(dialog.reject)
    dialog.setLayout(layout)
    dialog.setWindowModality(Qt.WindowModal)
    restoreGeom(dialog, "tagsList")
    selected_tags.clear()
    dialog.show()


def tagStats(cids, highlights="", highlights_percent=50):
    highlights = highlights.lower()
    highlights = [
        highlight for highlight in highlights.split(" ") if highlight]
    try:
        highlights_percent = int(highlights_percent)
    except:
        highlights_percent = 100
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
    highlightColor = getUserOption("highlight color")
    for nb, tag in l:
        search = f""" "tag:{tag}" """
        nbCardWithThisTag = len(mw.col.findCards(search))
        highlighted = False
        lowerTag = tag.lower()
        for highlight in highlights:
            if highlight in lowerTag:
                highlighted = True
                break
        htmlTag = f"""<span style="background-color:{highlightColor}">{tag}</span>""" if highlighted else tag
        percent_covered = round((nb*100)/nbCardWithThisTag)
        percentOfCardsWithThisTagWhichAreSelected = str(
            percent_covered)+"%" if nbCardWithThisTag else "Error: no card with this tag in the fcollection."
        if highlighted and percent_covered > highlights_percent:
            percentOfCardsWithThisTagWhichAreSelected = f"""<td style="border:1px solid yellow">{percentOfCardsWithThisTagWhichAreSelected}</td>"""
        else:
            percentOfCardsWithThisTagWhichAreSelected = f"""<td>{percentOfCardsWithThisTagWhichAreSelected}</td>"""
        percentOfSelectedCardsWithThisTag = str(round(
            (nb*100)/nbCards))+"%" if nbCardWithThisTag else "Error: no card with this tag in the collection."
        table.append((nb, tag, htmlTag, percentOfSelectedCardsWithThisTag,
                      percentOfCardsWithThisTagWhichAreSelected))
    html = ("""<script>
function high_yeld_tag(tag) {
  var cmd = "high_yeld_tag:" + tag;
  pycmd(cmd);
}
</script><table border=1>""" +
            "<tr><td></td><td>Tag</td><td width=\"25px\"># Card w/Tags</td><td width=\"25px\">% Cards Selected</td><td width=\"25px\">% Tag Covered</td>" +
            "\n".join(f"""<tr><td><input type="checkbox" onclick="high_yeld_tag(&quot;{tag}&quot;);"/></td><td>{htmlTag}</td><td>{nb}</td><td>{percentOfSelectedCardsWithThisTag}</td>{percentOfCardsWithThisTagWhichAreSelected}</tr>"""
                      for nb, tag, htmlTag, percentOfSelectedCardsWithThisTag, percentOfCardsWithThisTagWhichAreSelected in table) +
            """</table>""")
    return html


def setupMenu(browser):
    a = QAction("Number of tags", browser)
    a.setShortcut(QKeySequence(getUserOption(
        "Shortcut of 'number of tags'")))
    a.triggered.connect(lambda: showTagsInfo(browser, browser.selectedCards()))
    browser.form.menu_Help.addAction(a)
    a = QAction("and highlight", browser)
    a.setShortcut(QKeySequence(getUserOption(
        "Shortcut of 'and highlight'")))
    a.triggered.connect(lambda: showTagsInfoHighlight(
        browser, browser.selectedCards()))
    browser.form.menu_Help.addAction(a)


gui_hooks.browser_menus_did_init.append(setupMenu)


def select_tag(message, cmd, context):
    if not cmd.startswith("high_yeld_tag:"):
        return message
    (hyt, tag) = cmd.split(":", 1)
    print(tag)
    if tag in selected_tags:
        selected_tags.remove(tag)
    else:
        selected_tags.add(tag)
    return (True, None)

gui_hooks.webview_did_receive_js_message.append(select_tag)
