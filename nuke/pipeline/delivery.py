#!/usr/local/bin/python

import sys
import db_access as DB
import ConfigParser
import os
import operator

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

g_version_status = 'rev'
g_version_status_qt = 'rev'
g_version_status_2k = 'p2k'
g_version_list = []
g_ih_show_code = None
g_ih_show_root = None
g_ih_show_cfg_path = None
g_config = None
g_cancel = False
ihdb = None

def globals_from_config():
    global ihdb, g_ih_show_cfg_path, g_ih_show_root, g_ih_show_code, g_config, g_version_status, g_version_status_2k, g_version_status_qt
    try:
        g_ih_show_code = os.environ['IH_SHOW_CODE']
        g_ih_show_root = os.environ['IH_SHOW_ROOT']
        g_ih_show_cfg_path = os.environ['IH_SHOW_CFG_PATH']
        g_config = ConfigParser.ConfigParser()
        g_config.read(g_ih_show_cfg_path)
        g_version_status = g_config.get('delivery', 'version_status_qt')
        g_version_status_qt = g_config.get('delivery', 'version_status_qt')
        g_version_status_2k = g_config.get('delivery', 'version_status_2k')
        ihdb = DB.DBAccessGlobals.get_db_access()
        print "INFO: globals initiliazed from config %s."%g_ih_show_cfg_path
    except KeyError:
        e = sys.exc_info()
        print e[1]
        print "This is most likely because this system has not been set up to run inside the In-House environment."
    except ConfigParser.NoSectionError:
        e = sys.exc_info()
        print e[1]
    except ConfigParser.NoOptionError:
        e = sys.exc_info()
        print e[1]
    except:        
        e = sys.exc_info()
        print e[1]

def load_versions_for_status(m_status):
    global g_version_list
    g_version_list = ihdb.fetch_versions_with_status(m_status)

def execute_shell(m_interactive=False, m_2k=False):
    global g_version_list, g_version_status

    if m_2k:
        g_version_status = g_version_status_2k
    else:
        g_version_status = g_version_status_qt
    
    if m_interactive and not m_2k:
        sys.stdout.write("Proceed with low-resolution (Quicktime) delivery? \nAnswering no will switch to high-resolution (2k) delivery: (y|n) ")
        input = sys.stdin.readline()
        if 'n' in input or 'N' in input:
            print "INFO: Switching to high-resolution delivery."
            g_version_status = g_version_status_2k

    if m_interactive and m_2k:
        sys.stdout.write("Proceed with high-resolution (2K) delivery? (y|n) ")
        input = sys.stdin.readline()
        if 'n' in input or 'N' in input:
            print "Program will now exit."
            return

    load_versions_for_status(g_version_status)
    version_names = []
    for version in g_version_list:
        version_names.append(version.g_version_code)
    
    print "INFO: List of versions matching status %s:"%g_version_status
    print ""
    for count, version_name in enumerate(version_names, 1):
        print "%2d. %s"%(count, version_name)
    
    print ""
    if len(version_names) == 0:
        print "WARNING: No versions in the database for status %s!"%g_version_status
        print "Program will now exit."
        
    if m_interactive:
        sys.stdout.write("Remove any versions from the delivery?\nInput a comma-separated list of version index numbers: ")
        input = sys.stdin.readline()
        versions_rm = []
        for idx in input.split(','):
            i_idx = 0
            try:
                i_idx = int(idx)
            except ValueError:
                print "ERROR: %s is not a valid number."%idx
                continue
            if i_idx > 0 and i_idx <= len(version_names):
                versions_rm.append(i_idx - 1)
            else:
                print "ERROR: %s is not a valid index number."%idx
                continue
        new_version_list = []
        for count, version in enumerate(g_version_list):
            if count in versions_rm:
                print "INFO: Removing version %s from delivery list."%version.g_version_code
            else:
                new_version_list.append(version)
        g_version_list = new_version_list

class CheckBoxDelegate(QItemDelegate):
    """
    A delegate that places a fully functioning QCheckBox cell of the column to which it's applied.
    """
    def __init__(self, parent):
        QItemDelegate.__init__(self, parent)

    def createEditor(self, parent, option, index):
        """
        Important, otherwise an editor is created if the user clicks in this cell.
        """
        return None

    def paint(self, painter, option, index):
        """
        Paint a checkbox without the label.
        """
        self.drawCheck(painter, option, option.rect, Qt.Unchecked if int(index.data()) == 0 else Qt.Checked)

    def editorEvent(self, event, model, option, index):
        '''
        Change the data in the model and the state of the checkbox
        if the user presses the left mousebutton and this cell is editable. Otherwise do nothing.
        '''
        #         if not int(index.flags() & Qt.ItemIsEditable) > 0:
        #             print 'Item not editable'
        #             return False

        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            # Change the checkbox-state
            self.setModelData(None, model, index)
            return True

        return False


    def setModelData (self, editor, model, index):
        '''
        The user wanted to change the old state in the opposite.
        '''
        model.setData(index, True if int(index.data()) == 0 else False, Qt.EditRole)

class PublishDeliveryWindow(QMainWindow):
    def __init__(self, m_2k=False):
        super(PublishDeliveryWindow, self).__init__()
        self.setWindowTitle('Publish Delivery')
        self.setMinimumSize(640,480)
    
        # central widget
        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QVBoxLayout()
        self.widget.setLayout(self.layout)
    
        self.layout_top = QHBoxLayout()
        self.delivery_label = QLabel()
        self.delivery_label.setText("Choose a delivery type:")
    
        self.layout_top.addWidget(self.delivery_label)
    
        # ComboBox to select Quicktime or High-resolution delivery
        self.delivery_cbox = QComboBox()
        self.delivery_cbox.addItems(["Avid/VFX Quicktime", "High Resolution (DPX/EXR)"])
        if m_2k:
            self.delivery_cbox.setCurrentIndex(1)
    
        self.delivery_cbox.currentIndexChanged.connect(self.delivery_type_change)
    
        self.layout_top.addWidget(self.delivery_cbox)
    
        self.layout.addLayout(self.layout_top)
        
        self.layout_mid = QHBoxLayout()

        # Let's try this with a QTableView
        self.table_model = DeliveryTableModel(self, self.table_data(), self.table_header())
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.resizeColumnsToContents()
        self.table_view.setSortingEnabled(True)
        delegate = CheckBoxDelegate(None)
        self.table_view.setItemDelegateForColumn(0, delegate)          
        self.layout_mid.addWidget(self.table_view)
        self.layout.addLayout(self.layout_mid)

        # buttons at the bottom        
        self.layout_bottom = QHBoxLayout()
        self.buttons = QDialogButtonBox(self)
        self.buttons.setOrientation(Qt.Horizontal)
        self.buttons.setStandardButtons(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)     
        self.layout_bottom.addWidget(self.buttons)
        self.layout.addLayout(self.layout_bottom)

    def reject(self):
        global g_cancel
        g_cancel = True
        print "INFO: User has cancelled operation."
        QCoreApplication.instance().quit()

    def accept(self):
        global g_version_list
        tmp_version_list = []
        print "INFO: Proceeding with delivery publish."
        
        for index, row in enumerate(self.table_model.mylist):
            if not row[0]:
                print "INFO: User requested removal of %s from delivery."%row[2]
            else:
                tmp_version_list.append(g_version_list[index])
        g_version_list = tmp_version_list
        QCoreApplication.instance().quit()

    def table_data(self):
        version_table_ret = []
        global g_version_list
        for version in g_version_list:
            version_table_ret.append([True, version.g_dbid, version.g_version_code, version.g_shot.g_shot_code, version.g_artist.g_full_name, version.g_path_to_frames])
        return version_table_ret
        
    def table_header(self):
        version_header_ret = ['Include?', 'Database ID', 'Version Name', 'Shot Name', 'Artist Name', 'Path to Frames']
        return version_header_ret

    def delivery_type_change(self, idx):
        global g_version_status, g_version_list
    
        if idx == 0:
            print "INFO: Switching delivery type to Avid/VFX Quicktime."
            g_version_status = g_version_status_qt
        elif idx == 1:
            print "INFO: Switching delivery type to High Resolution (DPX/EXR)."
            g_version_status = g_version_status_2k

        load_versions_for_status(g_version_status)
        self.table_model.updateModel(self.table_data())
        self.table_view.setModel(self.table_model)
        self.table_view.update()

class DeliveryTableModel(QAbstractTableModel):
    def __init__(self, parent, mylist, header, *args):
        super(DeliveryTableModel, self).__init__()
        self.mylist = mylist
        self.header = header
    def updateModel(self, mylist):
        self.mylist = mylist
    def rowCount(self, parent):
        return len(self.mylist)
    def columnCount(self, parent):
        return len(self.header)
    def data(self, index, role):
        if not index.isValid():
            return None
        elif role != Qt.DisplayRole:
            return None
        return self.mylist[index.row()][index.column()]
    def setData(self, index, value, role=Qt.DisplayRole):
        if index.column() == 0:
            self.mylist[index.row()][0] = value
            return value
        return value

    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.header[col]
        return None
    def sort(self, col, order):
        """sort table by given column number col"""
        self.layoutAboutToBeChanged.emit()
        self.mylist = sorted(self.mylist,
            key=operator.itemgetter(col))
        if order == Qt.DescendingOrder:
            self.mylist.reverse()
        self.layoutChanged.emit()
        
def display_window(m_2k=False):
    global g_version_list, g_version_status
    if m_2k:
        g_version_status = g_version_status_2k
    else:
        g_version_status = g_version_status_qt

    load_versions_for_status(g_version_status)
        
    # Create a Qt application
    app = QApplication(sys.argv)
 
    # Our main window will be a QListView
    window = PublishDeliveryWindow(m_2k)
    window.show()
    app.exec_()
    
    if g_cancel:
        return
    
    
