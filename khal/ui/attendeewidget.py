import urwid
from additional_urwid_widgets import IndicativeListBox
import subprocess
import re

PALETTE = [("reveal_focus",              "black",            "light cyan",   "standout"),
           ("ilb_barActive_focus",       "dark cyan",        "light gray"),
           ("ilb_barActive_offFocus",    "light gray",       "dark gray"),
           ("ilb_barInactive_focus",     "light cyan",       "dark gray"),
           ("ilb_barInactive_offFocus",  "black",            "dark gray")]

def get_mails():
  res = subprocess.check_output(["bash", "-c", "khard email gmail | tail -n +2"])  
  maildata = [re.split(r"\s{2,}", x) for x in res.decode("utf-8").split("\n")]
  mails = ["%s <%s>" % (x[0], x[2]) for x in maildata if len(x) > 1]
  return mails


class MailPopup(urwid.PopUpLauncher):
  def __init__(self, widget, maillist):
    self.maillist = maillist
    self.widget = widget
    self.popup_visible = False
    self.justcompleted = False
    super().__init__(widget)

  def get_current_mailpart(self):
    mails = self.widget.get_edit_text().split(",")
    lastmail = mails[-1].lstrip(" ")
    return lastmail

  def complete_mail(self, newmail):
    mails = [x.strip() for x in self.widget.get_edit_text().split(",")[:-1]]
    mails += [newmail]
    return ", ".join(mails)

  def get_num_mails(self):
    mails = self.widget.get_edit_text().split(",")
    return len(mails)

  def keypress(self, size, key):
    if self.justcompleted and key not in ", ":
      self.widget.keypress(size, ",")
      self.widget.keypress(size, " ")
    self.widget.keypress(size, key)
    self.justcompleted = False
    if not self.popup_visible:
      self.open_pop_up()
      self.popup_visible = True

  def keycallback(self, size, key):
    self.widget.keypress((20,), key)
    self.justcompleted = False
    self.listbox.update_mails(self.get_current_mailpart())

  def donecallback(self, text):
    self.widget.set_edit_text(self.complete_mail(text))
    fulllength = len(self.widget.get_edit_text())
    self.widget.move_cursor_to_coords((fulllength,), fulllength, 0)
    self.close_pop_up()
    self.popup_visible = False
    self.justcompleted = True

  def create_pop_up(self):
    self.listbox = MailListBox(self.maillist, self.keycallback,
                               self.donecallback)
    return urwid.WidgetWrap(self.listbox)

  def get_pop_up_parameters(self):
    return {"left": 0, "top": 1, "overlay_width": 60, "overlay_height": 10}

  def render(self, size, focus=False):
    return super().render(size, True)


class MailListItem(urwid.Text):
  def render(self, size, focus=False):
    return super().render(size, False)

  def selectable(self):
    return True

  def keypress(self, size, key):
    return key

class MailListBox(IndicativeListBox):

  command_map = urwid.CommandMap()
  own_commands = [urwid.CURSOR_DOWN, urwid.CURSOR_UP, urwid.ACTIVATE]

  def __init__(self, mails, keycallback, donecallback, **args):
    self.mails = [MailListItem(x) for x in mails]
    mailsBody = [urwid.AttrMap(x, None, "reveal_focus") for x in self.mails]
    self.keycallback = keycallback
    self.donecallback = donecallback
    super().__init__(mailsBody, **args)

  def keypress(self, size, key):
    cmd = self.command_map[key]
    if cmd not in self.own_commands or key == " ":
      self.keycallback(size, key)
    elif cmd is urwid.ACTIVATE:
      self.donecallback(self.get_selected_item()._original_widget.get_text()[0])
    else:
      super().keypress(size, key)

  def update_mails(self, new_edit_text):
    new_body = []
    for mail in self.mails:
      if new_edit_text.lower() in mail.get_text()[0].lower():
        new_body += [urwid.AttrMap(mail, None, "reveal_focus")]
    self.set_body(new_body)


class AutocompleteEdit(urwid.Edit):
  def render(self, size, focus=False):
    return super().render(size, True)


class AttendeeWidget(urwid.WidgetWrap):
  def __init__(self):
    self.mails = get_mails()
    self.acedit = AutocompleteEdit()
    self.mp = MailPopup(self.acedit, self.mails)
    super().__init__(self.mp)


if __name__ == "__main__":
  mails = get_mails()
  acedit = AutocompleteEdit()
  mp = MailPopup(acedit, mails)
  loop = urwid.MainLoop(urwid.Filler(mp), PALETTE, pop_ups=True)
  loop.run()
