from concurrent.futures import Future
import functools
import re
from time import time
from .consts import DECK_DYN
from aqt import gui_hooks, mw
from aqt.qt import *
from aqt.browser import *
from aqt.utils import restoreGeom, getText, saveGeom
from aqt.webview import AnkiWebView

from .config import getUserOption, setUserOption

selected_tags = set()

def showTagsInfoHighlight(browser, cids, nids):
    if not cids:
        return
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
    showTagsInfo(browser, cids, nids, highlights, highlights_percent)


def showTagsInfo(browser, cids, nids, highlights="", highlights_percent=50):
    if not cids:
        return

    class CardInfoDialog(QDialog):
        def __init__(self, parent) -> None:
            super().__init__(parent)
            qconnect(self.finished, self.on_close)

        def on_close(self):
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


    def on_done(fut: Future):
        mw.progress.finish()
        info = fut.result()
        if not info:
            return
        dialog = CardInfoDialog(browser)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        view = AnkiWebView()
        layout.addWidget(view)
        view.stdHtml(info)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        layout.addWidget(bb)
        bb.rejected.connect(dialog.reject)
        dialog.setLayout(layout)
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        restoreGeom(dialog, "tagsList")
        selected_tags.clear()
        dialog.show()

    mw.progress.start(100, 0, label="Processing cards...", parent=browser)
    mw.progress.set_title("High Yield Tags")
    mw.taskman.run_in_background(lambda: tagStats(cids, nids, highlights, highlights_percent), on_done)

def escape_tag(tag):
    return re.escape(tag).replace("'", "''")

def tag_and_parents(tag):
    components = tag.split("::")
    yield components[0]
    for i in range(1, len(components)):
        comp = components[i]
        parents = components[0:i]
        yield '::'.join(parents) + '::' + comp


def tagStats(cids, nids, highlights="", highlights_percent=50):
    highlights = highlights.lower()
    highlights = [
        highlight for highlight in highlights.split(" ") if highlight]
    try:
        highlights_percent = int(highlights_percent)
    except:
        highlights_percent = 100
    tags = dict()
    nbCards = len(cids)
    last_progress = 0
    want_cancel = False
    def on_note_progress(i, total):
        mw.progress.update(f"Processing note {i} out of {total}", value=i, max=total)
        nonlocal want_cancel
        want_cancel = mw.progress.want_cancel()

    for i, nid in enumerate(nids, 1):
        if time() - last_progress >= 0.1:
            mw.taskman.run_on_main(functools.partial(on_note_progress, i=i, total=len(nids)))
            if want_cancel:
                return ''
        note = mw.col.getNote(nid)
        for tag in note.tags:
            tags[tag] = tags.get(tag, 0) + 1
    l = [(nb, tag) for tag, nb in tags.items()]
    l.sort(reverse=True)
    table = []
    highlightColor = getUserOption("highlight color")

    mw.taskman.run_on_main(lambda: mw.progress.update("Collecting tag frequencies..."))
    tag_freqs = {}
    for ntags, ccount in mw.col.db.execute('select n.tags, (select count() from cards c where c.nid=n.id) from notes n'):
        for tag in ntags.split():
            for parent in tag_and_parents(tag):
                tag_freqs.setdefault(parent, 0)
                tag_freqs[parent] += ccount

    last_progress = 0
    def on_tag_progress(i, total):
        mw.progress.update(f"Processing tag {i} out of {total}", value=i, max=total)
        nonlocal want_cancel
        want_cancel = mw.progress.want_cancel()

    for i, (nb, tag) in enumerate(l, 1):
        if time() - last_progress >= 0.1:
            mw.taskman.run_on_main(functools.partial(on_tag_progress, i=i, total=len(l)))
            if want_cancel:
                return ''
        nbCardWithThisTag = tag_freqs[tag]
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
    a.triggered.connect(lambda: showTagsInfo(browser, browser.selectedCards(), browser.selectedNotes()))
    browser.form.menu_Help.addAction(a)
    a = QAction("and highlight", browser)
    a.setShortcut(QKeySequence(getUserOption(
        "Shortcut of 'and highlight'")))
    a.triggered.connect(lambda: showTagsInfoHighlight(
        browser, browser.selectedCards(), browser.selectedNotes()))
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
