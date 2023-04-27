from PyQt5.QtWidgets import QApplication, QComboBox, QLabel, QWidget, QPushButton
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import *
from PyQt5 import QtCore
from PyQt5 import QtGui


from Main_window_Final import MainWindow


import sys
from Vid_Test import VideoPlayerGUI


class Mainpage(QWidget):
    def __init__(self, parent=None):
        """constructor to create a new window with charactersitis after create object from class window"""
        super().__init__()
        self.title = "SPLICE MASTER"
        self.top = 200
        self.left = 500
        self.width = 550
        self.height = 260
        self.file_path = ""
        self.init_window()

    def init_window(self):
        """initialize Main IFD window"""

        self.setWindowTitle(self.title)
        # icon Pic File name
        self.setWindowIcon(QtGui.QIcon(
            r"C:\Users\Tanmay\Documents\Major_Pjct\DFSpot-Deepfake-Recognition\img_splice\Icons\icons8-cbs-513.ico"))
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.setFixedSize(self.width, self.height)

        label = QLabel(self)
        label.move(175, 40)
        label.setText('Splice Master')
        label.setFont(QtGui.QFont("Sanserif", 24))

        label = QLabel(self)
        label.move(20, 200)
        label.setText('Select Video Detection or Image Detection:')
        label.setFont(QtGui.QFont("Sanserif", 8))

        pixmap = QPixmap(
            r"C:\Users\Tanmay\Documents\Major_Pjct\DFSpot-Deepfake-Recognition\img_splice\Icons\icons8-cbs-512.jpg")
        self.label = QLabel(self)
        self.label.setPixmap(pixmap)
        self.label.resize(150, 150)
        self.label.move(10, 20)
        self.label.setPixmap(pixmap.scaled(
            self.label.size(), Qt.IgnoreAspectRatio))
        self.label.show()

        self.combo = QComboBox(self)
        self.combo.addItem("Video Detection")
        self.combo.addItem("Image Detection")
        self.combo.setGeometry(QRect(234, 198, 300, 20))

        self.button = QPushButton("Start", self)
        self.button.setGeometry(QRect(445, 230, 90, 20))
        # icon Pic File name
        self.button.setIcon(QtGui.QIcon(
            r"C:\Users\Tanmay\Documents\Major_Pjct\DFSpot-Deepfake-Recognition\img_splice\Icons\start.png"))
        self.button.setIconSize(QtCore.QSize(15, 15))  # to change icon Size
        self.button.setToolTip(
            "<h5>Lunch Your choice either Video or Image Detection<h5>")
        self.button.clicked.connect(self.on_click)

        self.show()

    def on_click(self):
        if str(self.combo.currentText()) == "Video Detection":
            self.training_window = VideoPlayerGUI()
            self.training_window.show()
            self.close()

        elif str(self.combo.currentText()) == "Image Detection":
            self.test_window = MainWindow()
            self.test_window.show()
            self.close()


if __name__ == "__main__":
    App = QApplication(sys.argv)
    App.setStyle('Fusion')
    window = Mainpage()
    sys.exit(App.exec())
