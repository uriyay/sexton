# -*- coding: utf-8 -*-
#
# Petter Strandmark 2013.

import binascii
import datetime
import os
import struct
import time
from collections import OrderedDict
import pprint
import imp

from PySide import QtUiTools
from PySide.QtCore import *
from PySide.QtGui import *

from Petter.guihelper import exception_handler

from construct import *

class DataTypes(QMainWindow):
    def __init__(self, main_window, company_name, software_name):
        QMainWindow.__init__(self)
        self.setWindowTitle("Data Types")
        self.setWindowFlags(Qt.CustomizeWindowHint |
                            Qt.WindowTitleHint |
                            Qt.WindowCloseButtonHint)

        self.main_window = main_window
        self.main_struct = None

        # Set up UI
        loader = QtUiTools.QUiLoader()
        this_dir = os.path.dirname(__file__)
        self.ui = loader.load(os.path.join(this_dir, 'data_types.ui'), None)
        self.setCentralWidget(self.ui)
        QMetaObject.connectSlotsByName(self)

        # Size constraints
        self.setMinimumSize(self.ui.minimumSize())
        self.setMaximumSize(self.ui.maximumSize())

        # Read settings
        self.settings = QSettings(company_name, software_name)
        self.restoreGeometry(self.settings.value("DataTypes/geometry"))
        self.view = None

        # Internal flags.
        self.date_changed_internally = False
        self.time_changed_internally = False

    def set_view(self, view):
        self.view = view

    def get_format_string(self):
        if self.ui.littleEndianCheckBox.isChecked():
            format_string = '<'
        else:
            format_string = '>'

        if self.ui.eightBitRadioButton.isChecked():
            format_string += 'b'
            printf_string = '%d'
        elif self.ui.sixteenBitRadioButton.isChecked():
            format_string += 'h'
            printf_string = '%d'
        elif self.ui.thirtyTwoBitRadioButton.isChecked():
            format_string += 'i'
            printf_string = '%d'
        elif self.ui.sixtyFourBitRadioButton.isChecked():
            format_string += 'q'
            printf_string = '%d'

        if not self.ui.signedCheckBox.isChecked():
            format_string = format_string.upper()

        if self.ui.singleRadioButton.isChecked():
            format_string += 'f'
            printf_string = '%e'
        elif self.ui.doubleRadioButton.isChecked():
            format_string += 'd'
            printf_string = '%e'

        return format_string, printf_string

    def set_hexEdit_bytes(self, bytes):
        text = ''.join(["%02X " % ord(x) for x in bytes]).strip()
        # self.ui.hexEdit.setText(text)
        self.ui.hexEdit.setPlainText(text)

        # If there is text in the hex data field, the change
        # button should be activated.
        if len(text) > 0:
            self.ui.changeButton.setEnabled(True)
        else:
            self.ui.changeButton.setEnabled(False)

    def date_and_time_to_bytes(self):
        qdate = self.ui.calendarWidget.selectedDate()
        qtime = self.ui.timeEdit.time()
        dt = datetime.datetime(qdate.year(), qdate.month(), qdate.day(),
                               qtime.hour(), qtime.minute(), qtime.second())

        number = int(time.mktime(dt.timetuple()))
        bytes = struct.pack("I", number)
        return bytes

    def set_bytes(self, bytes_or_view, is_hexEdit_changer=False):
        current_tab = self.ui.tabWidget.currentWidget()

        if current_tab == self.ui.tab_numbers:
            #Get the format string.
            format_string, printf_string = self.get_format_string()
            # Compute how many bytes are needed.
            size_needed = struct.calcsize(format_string)
            # Extract the correct number of bytes if the
            # input is a memoryview.
            if isinstance(bytes_or_view, memoryview):
                bytes_or_view = bytes_or_view[:size_needed].tobytes()

            # Try to parse a number.
            self.ui.numberEdit.setEnabled(True)
            if printf_string == '%d':
                self.ui.signedCheckBox.setEnabled(True)
            else:
                self.ui.signedCheckBox.setEnabled(False)
            self.ui.littleEndianCheckBox.setEnabled(True)

            number = None
            try:
                assert(size_needed == len(bytes_or_view))
                number = struct.unpack(format_string, bytes_or_view)[0]
            except:
                self.ui.numberEdit.setText("n/a")
                self.ui.numberEdit.setEnabled(False)
                self.ui.signedCheckBox.setEnabled(False)
                self.ui.littleEndianCheckBox.setEnabled(False)

            if number is not None:
                self.ui.numberEdit.setText(printf_string % number)
                number_bytes = struct.pack(format_string, number)
                if not is_hexEdit_changer:
                    self.set_hexEdit_bytes(number_bytes)

        elif current_tab == self.ui.tab_dates:

            size_needed = 4
            if isinstance(bytes_or_view, memoryview):
                bytes_or_view = bytes_or_view[:size_needed].tobytes()

            # Try to parse a number.
            number = None
            try:
                assert(size_needed == len(bytes_or_view))
                number = struct.unpack('I', bytes_or_view)[0]
                # Success. Enable calendar.
                self.ui.calendarWidget.setEnabled(True)
                self.ui.timeEdit.setEnabled(True)
            except:
                self.ui.numberEdit.setText("n/a")
                self.ui.numberEdit.setEnabled(False)
                self.ui.calendarWidget.setEnabled(False)
                self.ui.timeEdit.setEnabled(False)

            if number is not None:
                localtime = time.localtime(number)
                qdate = QDate(localtime.tm_year, localtime.tm_mon, localtime.tm_mday)
                qtime = QTime(localtime.tm_hour, localtime.tm_min, localtime.tm_sec)

                self.date_changed_internally = True
                self.time_changed_internally = True
                self.ui.calendarWidget.setSelectedDate(qdate)
                self.ui.timeEdit.setTime(qtime)
                if not is_hexEdit_changer:
                    self.set_hexEdit_bytes(bytes_or_view)

        elif current_tab == self.ui.tab_construct:
            #parse data with self.main_struct.parse() and str() it to the text box
            if self.main_struct:
                size_needed = self.main_struct.sizeof()
                if isinstance(bytes_or_view, memoryview):
                    bytes_or_view = bytes_or_view[:size_needed].tobytes()
                try:
                    assert(size_needed == len(bytes_or_view))
                    self.parsed_struct = self.main_struct.parse(bytes_or_view)
                    self.ui.lstConstruct.clear()
                    self._dump_container_to_list(self.parsed_struct)
                    if not is_hexEdit_changer:
                        self.set_hexEdit_bytes(bytes_or_view)
                except:
                    self.ui.lstConstruct.clear()

    def _dump_container_to_list(self, dict_obj, tabs=0, path=None):
        if path is None:
            path = ''

        for key,value in dict_obj.items():
            value_path = '%s.%s' % (path, key)
            if type(value) is Container:
                item = QListWidgetItem()
                item.setText('{}{}:'.format('\t'*tabs, repr(key)))
                self.ui.lstConstruct.addItem(item)
                self._dump_container_to_list(value, tabs+1, value_path)
            else:
                value_string = '{}{}: {}'.format('\t' * tabs,
                        repr(key),
                        repr(value))
                item = QListWidgetItem()
                item.setText(value_string)
                item.setToolTip(value_path)
                self.ui.lstConstruct.addItem(item)

    def _get_from_dict(self, dict_obj, keys_list):
        return reduce(operator.getitem, keys_list, dict_obj)

    def _offsetOf(self, struct, container, path):
        if type(struct) is not Renamed:
            struct = Renamed('struct', struct)
        offset = 0
        for key,value in container.items():
            if key == path[0]:
                #increment the path
                path = path[1:]
                if not path:
                    return offset
                subcon = [x for x in struct.subcon.subcons if x.name == key][0]
                return offset + self._offsetOf(subcon, value, path)
            else:
                subcon = [x for x in struct.subcon.subcons if x.name == key][0]
                offset += subcon.sizeof()

    def _sizeOf(self, struct, container, path):
        if type(struct) is not Renamed:
            struct = Renamed('struct', struct)
        offset = 0
        for key,value in container.items():
            if key == path[0]:
                #increment the path
                path = path[1:]
                subcon = [x for x in struct.subcon.subcons if x.name == key][0]
                if not path:
                    return offset + subcon.sizeof()
                return offset + self._sizeOf(subcon, value, path)
            else:
                subcon = [x for x in struct.subcon.subcons if x.name == key][0]
                offset += subcon.sizeof()

    def update(self):
        if not self.view:
            return
        if not self.view.data_buffer:
            return
        data_view = self.view.data_at_position(self.view.get_cursor_position())
        self.set_bytes(data_view)

    def showEvent(self, event):
        QMainWindow.showEvent(self, event)

    def closeEvent(self, event):
        self.settings.setValue("DataTypes/geometry", self.saveGeometry())
        QMainWindow.closeEvent(self, event)

    @Slot()
    @exception_handler
    def on_hexEdit_textChanged(self):
        # Fires only when the text is edited by the user, not
        # by the program.
        try:
            hex_string = self.ui.hexEdit.toPlainText()
            hex_string = hex_string.replace(" ", "")
            bytes = binascii.unhexlify(hex_string)
            # This is a valid hex string. Enable the change button.
            self.ui.changeButton.setEnabled(True)
        except:
            bytes = ''
            # For invalid hex strings, the change button should be disabled.
            self.ui.changeButton.setEnabled(False)
        self.set_bytes(bytes, is_hexEdit_changer=True)

    @Slot()
    @exception_handler
    def on_numberEdit_textEdited(self):
        # Fires only when the text is edited by the user, not
        # by the program.
        number_string = self.ui.numberEdit.text().encode('utf-8')
        format_string, printf_string = self.get_format_string()
        try:
            number = None
            if printf_string == '%d':
                number = int(number_string)
            elif printf_string == '%e':
                number = float(number_string)
            bytes = struct.pack(format_string, number)
        except ValueError:
            bytes = ''
        except struct.error:
            bytes = ''
        self.set_hexEdit_bytes(bytes)

    @Slot()
    @exception_handler
    def on_timeEdit_timeChanged(self):
        # We only want to capture changes made by the user.
        if self.time_changed_internally:
            self.time_changed_internally = False
            return

        bytes = self.date_and_time_to_bytes()
        self.set_hexEdit_bytes(bytes)

    @Slot()
    @exception_handler
    def on_calendarWidget_selectionChanged(self):
        # We only want to capture changes made by the user.
        if self.date_changed_internally:
            self.date_changed_internally = False
            return

        bytes = self.date_and_time_to_bytes()
        self.set_hexEdit_bytes(bytes)

    @Slot()
    @exception_handler
    def on_changeButton_clicked(self):
        # Copy the hex data from hexEdit to the editor in the main
        # window.

        # First, get the hex data.
        try:
            hex_string = self.ui.hexEdit.toPlainText()
            hex_string = hex_string.replace(" ", "")
            byte_string = binascii.unhexlify(hex_string)
        except:
            byte_string = b''

        self.view.write_byte_string(byte_string)

    @Slot()
    @exception_handler
    def on_tabWidget_currentChanged(self):
        self.update()

    @Slot()
    @exception_handler
    def on_eightBitRadioButton_clicked(self):
        self.update()

    @Slot()
    @exception_handler
    def on_sixteenBitRadioButton_clicked(self):
        self.update()

    @Slot()
    @exception_handler
    def on_thirtyTwoBitRadioButton_clicked(self):
        self.update()

    @Slot()
    @exception_handler
    def on_sixtyFourBitRadioButton_clicked(self):
        self.update()

    @Slot()
    @exception_handler
    def on_signedCheckBox_clicked(self):
        if len(self.ui.hexEdit.text()) == 0:
            self.update()
        else:
            self.on_hexEdit_textChanged()

    @Slot()
    @exception_handler
    def on_littleEndianCheckBox_clicked(self):
        self.on_hexEdit_textChanged()

    @Slot()
    @exception_handler
    def on_singleRadioButton_clicked(self):
        self.update()

    @Slot()
    @exception_handler
    def on_doubleRadioButton_clicked(self):
        self.update()

    @Slot()
    @exception_handler
    def on_btnLoadConstruct_clicked(self):
        #display openDialogBox
        default_dir = self.settings.value("default_dir", '')
        file_filter = "Python script (*.py)"
        (file_name, mask) = QFileDialog.getOpenFileName(self,
                                                        "Choose construct script",
                                                        default_dir,
                                                        file_filter)
        self.ui.label_construct_filename.setText(file_name + ' - loading..')
        #parse construct
        module = imp.load_source('module', file_name)
        self.main_struct = module.main_struct
        self.ui.label_construct_filename.setText(file_name + ' - loading succeeded!')
        self.update()

    @Slot()
    @exception_handler
    def on_btnApplyConstruct_clicked(self):
        struct_dict = eval(self.ui.lstConstruct.toPlainText())
        #rebuild struct
        data = self.main_struct.build(struct_dict)
        self.set_hexEdit_bytes(data)
        #apply change
        self.on_changeButton_clicked()

    @Slot()
    @exception_handler
    def on_lstConstruct_itemSelectionChanged(self):
        #get the offset from the struct
        current_item = self.ui.lstConstruct.currentItem()
        item_tooltip = current_item.toolTip()
        if item_tooltip:
            path = item_tooltip.split('.')[1:]
            offset = self._offsetOf(self.main_struct, self.parsed_struct, path)
            size = self._sizeOf(self.main_struct, self.parsed_struct, path)
            #highlight in the hexeditor
            cursor = self.view.get_cursor_position()
            self.view.set_selection(cursor + offset, cursor + offset + size)
