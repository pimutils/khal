import urwid
from additional_urwid_widgets import IndicativeListBox


class MailPopup(urwid.PopUpLauncher):
    command_map = urwid.CommandMap()
    own_commands = ["cursor left", "cursor right", "cursor max left", "cursor max right"]

    def __init__(self, widget, maillist):
        self.maillist = maillist
        self.widget = widget
        self.popup_visible = False
        self.justcompleted = False
        super().__init__(widget)

    def change_mail_list(self, mails):
        self.maillist = mails

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
        cmd = self.command_map[key]
        if cmd is not None and cmd not in self.own_commands and key != " ":
            return key
        if self.justcompleted and key not in ", ":
            self.widget.keypress(size, ",")
            self.widget.keypress(size, " ")
        self.widget.keypress(size, key)
        self.justcompleted = False
        if not self.popup_visible:
            # Only open the popup list if there will be at least 1 address displayed
            current = self.get_current_mailpart()
            if len([x for x in self.maillist if current.lower() in x.lower()]) == 0:
                return
            if len(current) == 0:
                return
            self.open_pop_up()
            self.popup_visible = True

    def keycallback(self, size, key):
        cmd = self.command_map[key]
        if cmd == "menu":
            self.popup_visible = False
            self.close_pop_up()
        self.widget.keypress((20,), key)
        self.justcompleted = False
        cmp = self.get_current_mailpart()
        num_candidates = self.listbox.update_mails(cmp)
        if num_candidates == 0 or len(cmp) == 0:
            self.popup_visible = False
            self.close_pop_up()

    def donecallback(self, text):
        self.widget.set_edit_text(self.complete_mail(text))
        fulllength = len(self.widget.get_edit_text())
        self.widget.move_cursor_to_coords((fulllength,), fulllength, 0)
        self.close_pop_up()
        self.popup_visible = False
        self.justcompleted = True

    def create_pop_up(self):
        current_mailpart = self.get_current_mailpart()
        self.listbox = MailListBox(
            self.maillist, self.keycallback, self.donecallback, current_mailpart
        )
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

    def __init__(self, mails, keycallback, donecallback, current_mailpart, **args):
        self.mails = [MailListItem(x) for x in mails]
        mailsBody = [urwid.AttrMap(x, None, "list focused") for x in self.mails]
        self.keycallback = keycallback
        self.donecallback = donecallback
        super().__init__(mailsBody, **args)
        if len(current_mailpart) != 0:
            self.update_mails(current_mailpart)

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
                new_body += [urwid.AttrMap(mail, None, "list focused")]
        self.set_body(new_body)
        return len(new_body)


class AutocompleteEdit(urwid.Edit):
    def render(self, size, focus=False):
        return super().render(size, True)


class AttendeeWidget(urwid.WidgetWrap):
    def __init__(self, initial_attendees, mails):
        self.mails = mails
        if self.mails is None:
            self.mails = []
        if initial_attendees is None:
            initial_attendees = ""
        self.acedit = AutocompleteEdit()
        self.acedit.set_edit_text(initial_attendees)
        self.mp = MailPopup(self.acedit, self.mails)
        super().__init__(self.mp)

    def get_attendees(self):
        return self.acedit.get_edit_text()

    def change_mail_list(self, mails):
        self.mails = mails
        if self.mails is None:
            self.mails = []
        self.mp.change_mail_list(mails)

    def get_edit_text(self):
        return self.acedit.get_edit_text()

