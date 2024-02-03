import wx


class SelectDialog(wx.Dialog):
    def __init__(self, parent, title, choices):
        super().__init__(parent, title=title, size=(250, 200))
        self.selected_values = []  # Initialize an empty list to store selections
        self.init_ui(choices)
        self.SetSize((250, 200))
        self.SetTitle(title)

    def init_ui(self, choices):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        self.list_box = wx.ListBox(panel, choices=choices, style=wx.LB_MULTIPLE)
        vbox.Add(self.list_box, proportion=1, flag=wx.EXPAND | wx.ALL, border=10)

        ok_button = wx.Button(panel, label='OK')
        ok_button.Bind(wx.EVT_BUTTON, self.on_ok)
        vbox.Add(ok_button, flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, border=10)

        panel.SetSizer(vbox)

    def on_ok(self, event):
        self.selected_values = [self.list_box.GetString(i) for i in self.list_box.GetSelections()]
        self.EndModal(wx.ID_OK)  # End the modal state with an OK status

    def get_selected_values(self):
        return self.selected_values


# Example usage
if __name__ == "__main__":
    app = wx.App(False)
    dialog = SelectDialog(None, 'Select Options', ['Option 1', 'Option 2', 'Option 3'])
    if dialog.ShowModal() == wx.ID_OK:
        selected_values = dialog.get_selected_values()
        print(f"Selected: {selected_values}")
    dialog.Destroy()
    app.MainLoop()
