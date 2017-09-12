# -*- coding: utf-8 -*-
#
# Petter Strandmark 2013.

import binascii
import datetime
import os
import sys
import struct
import time
from collections import OrderedDict
import pprint
import imp
import operator
from ast import literal_eval

from PySide import QtUiTools
from PySide.QtCore import *
from PySide.QtGui import *

from Petter.guihelper import exception_handler

from modules import construct_helper
from modules import _010_template_helper
from construct import *
import pfp

class DataTypes(QMainWindow):
    def __init__(self, main_window, company_name, software_name):
        QMainWindow.__init__(self)
        self.setWindowTitle("Data Types")
        self.setWindowFlags(Qt.CustomizeWindowHint |
                            Qt.WindowTitleHint |
                            Qt.WindowCloseButtonHint)

        self.main_window = main_window
        self.parsed_struct = None
        self.main_struct = None
        self.parsed_template = None
        self.template_path = None

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
            if isinstance(bytes_or_view, memoryview):
                bytes_or_view = bytes_or_view.tobytes()
            try:
                if self.main_struct is not None:
                    #Its useless to check the size, since there can be dynamic size
                    self.parsed_struct = self.main_struct.parse(bytes_or_view)
                    self._dump_container_to_list(self.parsed_struct)
                    if not is_hexEdit_changer:
                        self.set_hexEdit_bytes(bytes_or_view)
            except Exception, err:
                self.ui.lstConstruct.clear()
                raise sys.exc_info()[1], None, sys.exc_info()[2]
        elif current_tab == self.ui.tab_010_templates:
            #parse data with self.main_struct.parse() and str() it to the text box
            if isinstance(bytes_or_view, memoryview):
                bytes_or_view = bytes_or_view.tobytes()
            try:
                if self.template_path is not None:
                    #Its useless to check the size, since there can be dynamic size
                    self.parsed_template = pfp.parse(data=bytes_or_view, template_file=self.template_path)
                    self._dump_parsed_010_object_to_list(OrderedDict(self.parsed_template._pfp__children_map))
                    if not is_hexEdit_changer:
                        self.set_hexEdit_bytes(bytes_or_view)
            except Exception, err:
                self.ui.lst010Template.clear()
                raise sys.exc_info()[1], None, sys.exc_info()[2]

    def _dump_container_to_list(self, dict_obj, tabs=0, path=None):
        if path is None:
            self.ui.lstConstruct.clear()
            path = ''

        for key,value in dict_obj.items():
            value_path = '%s.%s' % (path, key)
            if type(value) is Container:
                item = QListWidgetItem()
                item.setText('{}{}:'.format('\t'*tabs, repr(key)))
                item.setToolTip(value_path)
                self.ui.lstConstruct.addItem(item)
                self._dump_container_to_list(value, tabs+1, value_path)
            elif type(value) is ListContainer:
                for index, field in enumerate(value):
                    item = QListWidgetItem()
                    field_path = value_path + '.[%d]' % (index,)
                    item.setText('{}{}:'.format('\t'*tabs, repr(key) + '[%d]' % (index,)))
                    item.setToolTip(field_path)
                    self.ui.lstConstruct.addItem(item)
                    self._dump_container_to_list(field, tabs+1, field_path)
            else:
                value_string = '{}{}: {}'.format('\t' * tabs,
                        repr(key),
                        repr(value))
                item = QListWidgetItem()
                item.setText(value_string)
                item.setToolTip(value_path)
                self.ui.lstConstruct.addItem(item)


    def _dump_parsed_010_object_to_list(self, dict_obj, tabs=0, path=None):
        if path is None:
            self.ui.lst010Template.clear()
            path = ''

        for key,value in dict_obj.items():
            print 'value type is', type(value), 'key_name = ', key
            value_path = '%s.%s' % (path, key)
            if value.__class__.__base__ in (pfp.fields.Union, pfp.fields.Struct):
                item = QListWidgetItem()
                item.setText('{}{}:'.format('\t'*tabs, repr(key)))
                item.setToolTip(value_path)
                self.ui.lst010Template.addItem(item)
                self._dump_parsed_010_object_to_list(OrderedDict(value._pfp__children_map), tabs+1, value_path)
            elif value.__class__.__base__ is pfp.fields.Array:
                for index, field in enumerate(value):
                    item = QListWidgetItem()
                    field_path = value_path + '.[%d]' % (index,)
                    item.setText('{}{}:'.format('\t'*tabs, repr(key) + '[%d]' % (index,)))
                    item.setToolTip(field_path)
                    self.ui.lst010Template.addItem(item)
                    if hasattr(field, '_pfp__children_map'):
                        self._dump_parsed_010_object_to_list(OrderedDict(field._pfp__children_map), tabs+1, field_path)
            else:
                value_string = '{}{}: {}'.format('\t' * tabs,
                        repr(key),
                        value._pfp__value)
                item = QListWidgetItem()
                item.setText(value_string)
                item.setToolTip(value_path)
                self.ui.lst010Template.addItem(item)

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
        data = self.main_struct.build(self.parsed_struct)
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
            offset = construct_helper.get_offset_of(self.main_struct, self.parsed_struct, path)
            size = construct_helper.get_size_of(self.main_struct, self.parsed_struct, path)
            #highlight in the hexeditor
            cursor = self.view.get_cursor_position()
            self.view.set_selection(cursor + offset, cursor + offset + size)

    @Slot()
    @exception_handler
    def on_lstConstruct_itemActivated(self):
        '''
        This event happens when the user double click on item in the list or press Enter
        '''
        #get field value
        current_item = self.ui.lstConstruct.currentItem()
        item_tooltip = current_item.toolTip()
        field_name = item_tooltip
        path = field_name.split('.')[1:]
        struct_dict = OrderedDict(self.parsed_struct.items())
        field_value = construct_helper.get_from_dict(struct_dict, path)
        field_size = construct_helper.get_size_of(self.main_struct, self.parsed_struct, path)
        #field type is actually string or int/long
        if type(field_value) is str:
            #display as a string
            field_value = repr(field_value)
        elif type(field_value) in (int,long):
            field_value = '0x%x' % (field_value,)
        else:
            raise Exception('Unknown field type for %s' % (path,))

        #open dialog box
        value,is_confirmed = QInputDialog.getText(self,
                'Change value',
                'Enter new integer value for %s (%d bytes)' % (field_name, field_size),
                text=field_value)
        if not is_confirmed:
            return

        #parse the value
        value = literal_eval(value)
        #change the value in the dict
        construct_helper.set_dict_value(struct_dict, path, value)
        #try to rebuild the struct, this might throw exception that will be displayed in message box
        parsed_struct = Container(struct_dict)
        data = self.main_struct.build(parsed_struct)
        #change self.parsed_struct after we succeded to rebuild the main_struct with it
        self.parsed_struct = parsed_struct
        #change also in lstConstruct
        self._dump_container_to_list(self.parsed_struct)
        #and the hexEdit
        self.set_hexEdit_bytes(data)

    @Slot()
    @exception_handler
    def on_btnLoad010Template_clicked(self):
        #display openDialogBox
        default_dir = self.settings.value("default_dir", '')
        file_filter = "010 Template (*.bt)"
        (file_name, mask) = QFileDialog.getOpenFileName(self,
                                                        "Choose 010 template",
                                                        default_dir,
                                                        file_filter)
        self.ui.label_010_template_filename.setText(file_name + ' - loading..')
        #parse 010 template
        self.template_path = file_name
        self.ui.label_010_template_filename.setText(file_name + ' - loading succeeded!')
        self.update()

    @Slot()
    @exception_handler
    def on_btnApply010Template_clicked(self):
        data = self.parsed_template._pfp__build()
        self.set_hexEdit_bytes(data)
        #apply change
        self.on_changeButton_clicked()

    @Slot()
    @exception_handler
    def on_lst010Template_itemSelectionChanged(self):
        #get the offset from the struct
        current_item = self.ui.lst010Template.currentItem()
        item_tooltip = current_item.toolTip()
        if item_tooltip:
            path = item_tooltip.split('.')[1:]
            offset = _010_template_helper.get_offset_of(self.parsed_template, path)
            size = _010_template_helper.get_size_of(self.parsed_template, path)
            #highlight in the hexeditor
            cursor = self.view.get_cursor_position()
            self.view.set_selection(cursor + offset, cursor + offset + size)

    @Slot()
    @exception_handler
    def on_lst010Template_itemActivated(self):
        '''
        This event happens when the user double click on item in the list or press Enter
        '''
        #get field value
        current_item = self.ui.lst010Template.currentItem()
        item_tooltip = current_item.toolTip()
        field_name = item_tooltip
        path = field_name.split('.')[1:]
        field_value = _010_template_helper.get_from_template(self.parsed_template, path)._pfp__value
        field_size = _010_template_helper.get_size_of(self.parsed_template, path)
        #field type is actually string or int/long
        if type(field_value) is str:
            #display as a string
            field_value = repr(field_value)
        elif type(field_value) in (int,long):
            field_value = '0x%x' % (field_value,)
        else:
            raise Exception('Unknown field type for %s' % (path,))

        #open dialog box
        value,is_confirmed = QInputDialog.getText(self,
                'Change value',
                'Enter new integer value for %s (%d bytes)' % (field_name, field_size),
                text=field_value)
        if not is_confirmed:
            return

        #parse the value
        value = literal_eval(value)
        #change the value in the dict
        _010_template_helper.set_template_value(self.parsed_template, path, value)
        #try to rebuild the struct, this might throw exception that will be displayed in message box
        data = self.parsed_template._pfp__build()
        #change also in lst010Template
        self._dump_parsed_010_object_to_list(self.parsed_template)
        #and the hexEdit
        self.set_hexEdit_bytes(data)
