from sys import stderr
from numpy.core.fromnumeric import std
from numpy.lib.utils import source
# from pcbnewTransition import pcbnew, isV6
# from kikit.panelize_ui_impl import loadPresetChain, obtainPreset, mergePresets
# from kikit import panelize_ui
# from kikit.panelize import appendItem
# from kikit.common import PKG_BASE
# from .common import initDialog, destroyDialog
# import kikit.panelize_ui_sections
import wx
import json
import tempfile
import shutil
import os
from threading import Thread
from itertools import chain

PLATFORMS = ["Linux/MacOS", "Windows"]

class ExceptionThread(Thread):
    def run(self):
        self.exception = None
        try:
            super().run()
        except Exception as e:
            self.exception = e

def replaceExt(file, ext):
    return os.path.splitext(file)[0] + ext

def pcbnewPythonPath():
    return os.path.dirname(pcbnew.__file__)

def presetDifferential(source, target):
    result = {}
    for sectionName, section in target.items():
        if sectionName not in source:
            result[sectionName] = section
            continue
        updateKeys = {}
        sourceSection = source[sectionName]
        for key, value in section.items():
            if key not in sourceSection or str(sourceSection[key]).lower() != str(value).lower():
                updateKeys[key] = value
        if len(updateKeys) > 0:
            result[sectionName] = updateKeys
    return result


def transplateBoard(source, target):
    items = chain(
        list(target.GetDrawings()),
        list(target.GetFootprints()),
        list(target.GetTracks()),
        list(target.Zones()))
    for x in items:
        target.Remove(x)

    targetNetinfo = target.GetNetInfo()
    targetNetinfo.RemoveUnusedNets()

    for x in source.GetDrawings():
        appendItem(target, x)
    for x in source.GetFootprints():
        appendItem(target, x)
    for x in source.GetTracks():
        appendItem(target, x)
    for x in source.Zones():
        appendItem(target, x)
    for n in [n for _, n in source.GetNetInfo().NetsByNetcode().items()]:
        targetNetinfo.AppendNet(n)

    d = target.GetDesignSettings()
    d.CloneFrom(source.GetDesignSettings())

    target.SetProperties(source.GetProperties())
    target.SetPageSettings(source.GetPageSettings())
    target.SetTitleBlock(source.GetTitleBlock())
    target.SetZoneSettings(source.GetZoneSettings())


class SFile():
    def __init__(self, nameFilter):
        self.nameFilter = nameFilter
        self.description = ""
        self.isGuiRelevant = lambda section: True

    def validate(self, x):
        return x


class ParameterWidgetBase:
    def __init__(self, parent, name, parameter):
        self.name = name
        self.parameter = parameter
        self.label = wx.StaticText(parent,
                                   label=name,
                                   size=wx.Size(150, -1),
                                   style=wx.ALIGN_RIGHT)
        self.label.SetToolTip(parameter.description)
        self.fresh = True

    def showIfRelevant(self, preset):
        relevant = self.parameter.isGuiRelevant(preset)
        if self.fresh or self.label.IsShown() != relevant:
            self.label.Show(relevant)
            self.widget.Show(relevant)
            self.fresh = False
            return True
        return False


class TextWidget(ParameterWidgetBase):
    def __init__(self, parent, name, parameter, onChange):
        super().__init__(parent, name, parameter)
        self.widget = wx.TextCtrl(
            parent, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0)
        self.widget.Bind(wx.EVT_TEXT, onChange)

    def setValue(self, value):
        self.widget.ChangeValue(str(value))

    def getValue(self):
        return self.widget.GetValue()


class ChoiceWidget(ParameterWidgetBase):
    def __init__(self, parent, name, parameter, onChange):
        super().__init__(parent, name, parameter)
        self.widget = wx.Choice(parent, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize,
                                parameter.vals, 0)
        self.widget.SetSelection(0)
        self.widget.Bind(wx.EVT_CHOICE, onChange)

    def setValue(self, value):
        for i, option in enumerate(self.parameter.vals):
            if option.lower() == str(value).lower():
                self.widget.SetSelection(i)
                break

    def getValue(self):
        return self.parameter.vals[self.widget.GetSelection()]


class InputFileWidget(ParameterWidgetBase):
    def __init__(self, parent, name, parameter, onChange):
        super().__init__(parent, name, parameter)
        self.widget = wx.FilePickerCtrl(
            parent, wx.ID_ANY, wx.EmptyString, name,
            parameter.nameFilter, wx.DefaultPosition, wx.DefaultSize, wx.FLP_DEFAULT_STYLE)
        self.widget.Bind(wx.EVT_FILEPICKER_CHANGED, onChange)

    def getValue(self):
        return self.widget.GetPath()

    def setValue(self, value):
        self.widget.SetPath(value)


def obtainParameterWidget(parameter):
    # if isinstance(parameter, kikit.panelize_ui_sections.SChoiceBase):
        return ChoiceWidget
    # if isinstance(parameter, SFile):
    #     return InputFileWidget
    # return TextWidget


class SectionGui():
    def __init__(self, parent, name, section, onResize, onChange):
        self.name = name
        self.parent = parent
        self.container = wx.CollapsiblePane(
            parent, wx.ID_ANY, name, wx.DefaultPosition, wx.DefaultSize,
            wx.CP_DEFAULT_STYLE)
        self.container.Collapse(False)

        self.container.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, onResize)
        self.container.SetSizeHints(wx.DefaultSize, wx.DefaultSize)
        self.container.GetPane().SetSizeHints(wx.DefaultSize, wx.DefaultSize)

        self.itemGrid = wx.FlexGridSizer(0, 2, 2, 2)
        self.itemGrid.AddGrowableCol(1)
        self.itemGrid.SetFlexibleDirection(wx.BOTH)
        self.itemGrid.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_ALL)

        self.items = {
            name: obtainParameterWidget(param)(
                self.container.GetPane(), name, param, onChange)
            for name, param in section.items()
        }
        for widget in self.items.values():
            self.itemGrid.Add(widget.label, 0,  wx.ALL |
                              wx.ALIGN_CENTER_VERTICAL | wx.EXPAND | wx.RIGHT, 5)
            self.itemGrid.Add(widget.widget, 0,  wx.ALL |
                              wx.ALIGN_CENTER_VERTICAL | wx.EXPAND | wx.RIGHT, 5)

        self.container.GetPane().SetSizer(self.itemGrid)

    def populateInitialValue(self, values):
        for name, widget in self.items.items():
            if name not in values:
                continue
            widget.setValue(values[name])

    def collectPreset(self):
        return {name: widget.getValue() for name, widget in self.items.items()}

    def showOnlyRelevantFields(self):
        changed = False
        preset = self.collectPreset()
        for name, widget in self.items.items():
            if name not in preset:
                continue
            ch = widget.showIfRelevant(preset)
            changed = changed or ch
        if changed:
            # This is hacky, but it is the only reliable way to force collapsible
            # pane to correctly adjust its size
            self.container.Collapse()
            self.container.Expand()
        return changed

    def collectReleventPreset(self):
        preset = self.collectPreset()
        return {name: widget.getValue()
                for name, widget in self.items.items()
                if widget.parameter.isGuiRelevant(preset)}


class PanelizeDialog(wx.Dialog):
    def __init__(self, parent=None, board=None, preset=None):
        wx.Dialog.__init__(
            self, parent, title=f'Panelize a board  (version asds)',
            style=wx.DEFAULT_DIALOG_STYLE)
        self.Bind(wx.EVT_CLOSE, self.OnClose, id=self.GetId())

        self.board = board
        self.dirty = False

        topMostBoxSizer = wx.BoxSizer(wx.VERTICAL)

        middleSizer = wx.BoxSizer(wx.HORIZONTAL)

        maxDisplayArea = wx.Display().GetClientArea()
        self.maxDialogSize = wx.Size(
            min(500, maxDisplayArea.Width),
            min(800, maxDisplayArea.Height - 200))

        self.scrollWindow = wx.ScrolledWindow(
            self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.VSCROLL)
        self.scrollWindow.SetSizeHints(self.maxDialogSize, wx.Size(self.maxDialogSize.width, -1))
        self.scrollWindow.SetScrollRate(5, 5)
        self._buildSections(self.scrollWindow)
        middleSizer.Add(self.scrollWindow, 0, wx.EXPAND | wx.ALL, 5)

        self._buildOutputSections(middleSizer)

        topMostBoxSizer.Add(middleSizer, 1, wx.EXPAND | wx.ALL, 5)
        self._buildBottomButtons(topMostBoxSizer)

        self.SetSizer(topMostBoxSizer)
        self.populateInitialValue(preset)
        self.buildOutputSections()
        self.showOnlyRelevantFields()
        self.OnResize()

        if os.name != "nt":
            self.SetBackgroundColour( wx.SystemSettings.GetColour(wx.SYS_COLOUR_BACKGROUND))


    def _buildOutputSections(self, sizer):
        internalSizer = wx.BoxSizer(wx.VERTICAL)

        cliLabel = wx.StaticText(self, label="KiKit CLI command:",
                                 size=wx.DefaultSize, style=wx.ALIGN_LEFT)
        internalSizer.Add(cliLabel, 0, wx.EXPAND | wx.ALL, 2)

        self.platformSelector = wx.Choice(self, wx.ID_ANY, wx.DefaultPosition,
            wx.DefaultSize, PLATFORMS, 0)
        if os.name == "nt":
            self.platformSelector.SetSelection(PLATFORMS.index("Windows"))
        else:
            self.platformSelector.SetSelection(0) # Choose posix by default
        self.platformSelector.Bind(wx.EVT_CHOICE, lambda evt: self.buildOutputSections())
        internalSizer.Add(self.platformSelector, 0, wx.EXPAND | wx.ALL, 2 )

        self.kikitCmdWidget = wx.TextCtrl(
            self, wx.ID_ANY, "KiKit Command", wx.DefaultPosition, wx.DefaultSize,
            wx.TE_MULTILINE | wx.TE_READONLY)
        self.kikitCmdWidget.SetSizeHints(
            wx.Size(self.maxDialogSize.width,
                    self.maxDialogSize.height // 2),
            wx.Size(self.maxDialogSize.width, -1))
        cmdFont = self.kikitCmdWidget.GetFont()
        cmdFont.SetFamily(wx.FONTFAMILY_TELETYPE)
        self.kikitCmdWidget.SetFont(cmdFont)
        internalSizer.Add(self.kikitCmdWidget, 0, wx.EXPAND | wx.ALL, 2)

        jsonLabel = wx.StaticText(self, label="KiKit JSON preset (contains only changed keys):",
                                  size=wx.DefaultSize, style=wx.ALIGN_LEFT)
        internalSizer.Add(jsonLabel, 0, wx.EXPAND | wx.ALL, 2)

        self.kikitJsonWidget = wx.TextCtrl(
            self, wx.ID_ANY, "KiKit JSON", wx.DefaultPosition, wx.DefaultSize,
            wx.TE_MULTILINE | wx.TE_READONLY)
        self.kikitJsonWidget.SetSizeHints(
            wx.Size(self.maxDialogSize.width,
                    self.maxDialogSize.height // 2),
            wx.Size(self.maxDialogSize.width, -1))
        cmdFont = self.kikitJsonWidget.GetFont()
        cmdFont.SetFamily(wx.FONTFAMILY_TELETYPE)
        self.kikitJsonWidget.SetFont(cmdFont)
        internalSizer.Add(self.kikitJsonWidget, 0, wx.EXPAND | wx.ALL, 2)

        ieButtonsSizer = wx.BoxSizer(wx.HORIZONTAL)
        ieButtonsSizer.Add((0, 0), 1, wx.EXPAND, 5)

        self.importButton = wx.Button(self, wx.ID_ANY, u"Import JSON configuration",
            wx.DefaultPosition, wx.DefaultSize, 0)
        try:
            self.importButton.SetBitmap(wx.BitmapBundle(wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN)))
        except:
            self.importButton.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN))
        ieButtonsSizer.Add(self.importButton, 0, wx.ALL, 5)
        self.importButton.Bind(wx.EVT_BUTTON, self.onImport)

        self.exportButton = wx.Button(self, wx.ID_ANY, u"Export JSON configuration",
            wx.DefaultPosition, wx.DefaultSize, 0)
        try:
            self.exportButton.SetBitmap(wx.BitmapBundle(wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE)))
        except:
            self.exportButton.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE))
        ieButtonsSizer.Add(self.exportButton, 0, wx.ALL, 5)
        self.exportButton.Bind(wx.EVT_BUTTON, self.onExport)

        internalSizer.Add(ieButtonsSizer, 1, wx.EXPAND, 5)

        sizer.Add(internalSizer, 0, wx.EXPAND | wx.ALL, 2)

    def _buildSections(self, parentWindow):
        sectionsSizer = wx.BoxSizer(wx.VERTICAL)

        sections = {
            "Input": {
                "Input file": SFile("*.kicad_pcb")
            }
        }
        # sections.update(kikit.panelize_ui_sections.availableSections)

        self.sections = {
            name: SectionGui(parentWindow, name, section,
                             lambda evt: self.OnResize(), lambda evt: self.OnChange())
            for name, section in sections.items()
        }
        for section in self.sections.values():
            sectionsSizer.Add(section.container, 0, wx.ALL | wx.EXPAND, 5)

        parentWindow.SetSizer(sectionsSizer)

    def _buildBottomButtons(self, parentSizer):
        button_box = wx.BoxSizer(wx.HORIZONTAL)
        closeButton = wx.Button(self, label='Close')
        self.Bind(wx.EVT_BUTTON, self.OnClose, id=closeButton.GetId())
        button_box.Add(closeButton, 1, wx.RIGHT, 10)
        self.okButton = wx.Button(self, label='Panelize')
        self.Bind(wx.EVT_BUTTON, self.OnPanelize, id=self.okButton.GetId())
        button_box.Add(self.okButton, 1)

        parentSizer.Add(button_box, 0, wx.ALIGN_RIGHT |
                        wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

    def OnResize(self):
        self.scrollWindow.GetSizer().Layout()
        self.scrollWindow.Fit()
        self.scrollWindow.FitInside()
        self.GetSizer().Layout()
        self.Fit()

    def OnClose(self, event):
        self.EndModal(0)

    def OnPanelize(self, event):
        with tempfile.TemporaryDirectory(prefix="kikit") as dirname:
            try:
                panelFile = os.path.join(dirname, "panel.kicad_pcb")

                progressDlg = wx.ProgressDialog(
                    "Running kikit", "Running kikit, please wait",
                    parent=self)
                progressDlg.Show()
                progressDlg.Pulse()

                args = self.kikitArgs()
                preset = obtainPreset([], **args)
                input = self.sections["Input"].items["Input file"].getValue()
                if len(input) == 0:
                    dlg = wx.MessageDialog(
                        None, f"No input file specified", "Error", wx.OK)
                    dlg.ShowModal()
                    dlg.Destroy()
                    return
                if os.path.realpath(input) == os.path.realpath(pcbnew.GetBoard().GetFileName()):
                    dlg = wx.MessageDialog(
                        None,
                        f"The file {input} is the same as currently opened board. Cannot continue.\n\n" + \
                         "Please, run the panelization tool when no board is opened in pcbnew.",
                        "Error", wx.OK)
                    dlg.ShowModal()
                    dlg.Destroy()
                    return
                thread = ExceptionThread(target=panelize_ui.doPanelization,
                                         args=(input, panelFile, preset))
                thread.daemon = True
                thread.start()
                while True:
                    progressDlg.Pulse()
                    thread.join(timeout=1)
                    if not thread.is_alive():
                        break
                if thread.exception:
                    raise thread.exception
                # KiCAD 6 does something strange here, so we will load
                # an empty file if we read it directly, but we can always make
                # a copy and read that:
                copyPanelName = os.path.join(dirname, "panel-copy.kicad_pcb")
                shutil.copy(panelFile, copyPanelName)
                try:
                    shutil.copy(replaceExt(panelFile, ".kicad_pro"), replaceExt(copyPanelName, "kicad_pro"))
                    shutil.copy(replaceExt(panelFile, ".kicad_prl"), replaceExt(copyPanelName, "kicad_prl"))
                except FileNotFoundError:
                    # We don't care if we didn't manage to copy the files
                    pass
                panel = pcbnew.LoadBoard(copyPanelName)
                transplateBoard(panel, self.board)
                self.dirty = True
            except Exception as e:
                dlg = wx.MessageDialog(
                    None, f"Cannot perform:\n\n{e}", "Error", wx.OK)
                dlg.ShowModal()
                dlg.Destroy()
            finally:
                progressDlg.Hide()
                progressDlg.Destroy()
        pcbnew.Refresh()

    def populateInitialValue(self, initialPreset=None):
        preset = loadPresetChain([":default"])
        if initialPreset is not None:
            mergePresets(preset, initialPreset)
        for name, section in self.sections.items():
            if name.lower() not in preset:
                continue
            section.populateInitialValue(preset[name.lower()])
        self.buildOutputSections()

    def showOnlyRelevantFields(self):
        changed = False
        for section in self.sections.values():
            sectionChanged = section.showOnlyRelevantFields()
            changed = changed or sectionChanged
        return changed

    def collectPreset(self, includeInput=False):
        preset = loadPresetChain([":default"])
        if includeInput:
            preset["input"] = {}
        for name, section in self.sections.items():
            if name.lower() not in preset:
                continue
            preset[name.lower()].update(section.collectPreset())
        return preset

    def collectReleventPreset(self):
        preset = {}
        for name, section in self.sections.items():
            preset[name.lower()] = section.collectReleventPreset()
        del preset["input"]
        return preset

    def OnChange(self):
        if self.showOnlyRelevantFields():
            self.OnResize()
        self.buildOutputSections()

    def buildOutputSections(self):
        defaultPreset = loadPresetChain([":default"])
        preset = self.collectReleventPreset()
        presetUpdates = presetDifferential(defaultPreset, preset)

        self.kikitJsonWidget.ChangeValue(json.dumps(presetUpdates, indent=4))

        command = self._buildUnixCommand(presetUpdates) \
                    if self.platformSelector.GetSelection() == 0 \
                    else self._buildWindowsCommand(presetUpdates)
        self.kikitCmdWidget.ChangeValue(command)

    def _buildUnixCommand(self, presetUpdates):
        kikitCommand = "kikit panelize \\\n"
        for section, values in presetUpdates.items():
            if len(values) == 0:
                continue
            attrs = "; ".join(
                [f"{key}: {value}" for key, value in values.items()])
            kikitCommand += f"    --{section} '{attrs}' \\\n"
        inputFilename = self.sections["Input"].items["Input file"].getValue()
        if len(inputFilename) == 0:
            inputFilename = "<missingInput>"
        kikitCommand += f"    '{inputFilename}' panel.kicad_pcb"
        return kikitCommand

    def _buildWindowsCommand(self, presetUpdates):
        kikitCommand = "kikit panelize^\n"
        for section, values in presetUpdates.items():
            if len(values) == 0:
                continue
            attrs = "; ".join(
                [f"{key}: {value}" for key, value in values.items()])
            kikitCommand += f"    --{section} \"{attrs}\" ^\n"
        inputFilename = self.sections["Input"].items["Input file"].getValue()
        if len(inputFilename) == 0:
            inputFilename = "<missingInput>"
        kikitCommand += f"    \"{inputFilename}\" panel.kicad_pcb"
        return kikitCommand


    def kikitArgs(self):
        defaultPreset = loadPresetChain([":default"])
        preset = self.collectReleventPreset()
        presetUpdates = presetDifferential(defaultPreset, preset)

        args = {}
        for section, values in presetUpdates.items():
            if len(values) == 0:
                continue
            args[section] = values
        return args

    def onExport(self, evt):
        with wx.FileDialog(self, "Export configuration", wildcard="KiKit configurations (*.json)|*.json",
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            pathname = fileDialog.GetPath()
            try:
                defaultPreset = loadPresetChain([":default"])
                preset = self.collectReleventPreset()
                presetUpdates = presetDifferential(defaultPreset, preset)
                with open(pathname, "w", encoding="utf-8") as file:
                    json.dump(presetUpdates, file, indent=4)
                wx.MessageBox(f"Configuration exported to {pathname}", "Success",
                    style=wx.OK | wx.ICON_INFORMATION, parent=self)
            except IOError as e:
                wx.MessageBox(f"Cannot export to file {pathname}: {e}", "Error",
                    style=wx.OK | wx.ICON_ERROR, parent=self)

    def onImport(self, evt):
        with wx.FileDialog(self, "Open KiKit configuration", wildcard="KiKit configurations (*.json)|*.json",
                       style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            pathname = fileDialog.GetPath()
            try:
                with open(pathname, "r", encoding="utf-8") as file:
                    preset = json.load(file)
                    self.populateInitialValue(preset)
                    self.OnChange()
            except Exception as e:
                wx.MessageBox(f"Cannot load configuration: {e}", "Error",
                    style=wx.OK | wx.ICON_ERROR, parent=self)


# class PanelizePlugin(pcbnew.ActionPlugin):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.preset = {}
#         self.dirty = False

#     def defaults(self):
#         self.name = "KiKit: Panelize PCB"
#         self.category = "KiKit"
#         self.description = "Create a panel"
#         self.icon_file_name = os.path.join(PKG_BASE, "resources", "graphics", "panelizeIcon_24x24.png")
#         self.show_toolbar_button = True

#     def Run(self):
#         try:
#             dialog = None
#             if not self.dirty and not pcbnew.GetBoard().IsEmpty():
#                 dlg = wx.MessageDialog(
#                     None,
#                     "The currently opened board is not empty and it will be " + \
#                     "replaced by the panel. Do you wish to continue?\n\n" + \
#                     "Note that the panelization tool is supposed to be invoked from a stand-alone pcbnew instance.",
#                     "Confirm",
#                     wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
#                 ret = dlg.ShowModal()
#                 dlg.Destroy()
#                 if ret == wx.ID_NO:
#                     return
#             dialog = initDialog(lambda: PanelizeDialog(None, pcbnew.GetBoard(), self.preset))
#             dialog.ShowModal()
#             self.preset = dialog.collectPreset(includeInput=True)
#             self.dirty = self.dirty or dialog.dirty
#         except Exception as e:
#             dlg = wx.MessageDialog(
#                 None, f"Cannot perform: {e}", "Error", wx.OK)
#             dlg.ShowModal()
#             dlg.Destroy()
#         finally:
#             destroyDialog(dialog)


# plugin = PanelizePlugin

if __name__ == "__main__":
    # Run test dialog
    import json
    app = wx.App()

    dialog = PanelizeDialog()
    dialog.ShowModal()
    print(json.dumps(dialog.collectPreset(True), indent=4))

