import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel
from PyQt5.QtGui import QIntValidator
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QRegExpValidator

class SimpleWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Set up the window
        self.setWindowTitle('Basic UI with Text Entry')
        self.setGeometry(100, 100, 300, 150)

        # Create a layout
        layout = QVBoxLayout()

        # Create a QLabel
        self.label = QLabel('Enter text below:', self)

        # Create a QLineEdit (Text Entry Box)
        self.text_entry = QLineEdit(self)
        # self.text_entry.setMaxLength(3)
        email_pattern = r"^[0-1]{1}.[0-9]{1}"
        regexp = QRegExp(email_pattern)
        validator = QRegExpValidator(regexp, self.text_entry)
        self.text_entry.setValidator(validator)
        
        self.text_entry.setText("0.0")

        # self.text_entry.setInputMask("0.0")
        # self.validator = QIntValidator()
        # self.text_entry.setValidator(self.validator)
        # self.validator = QDoubleValidator(0.0, 1.0, 1)  # Range from 0.0 to 2.0 with 2 decimal places
        # self.validator.setNotation(QDoubleValidator.StandardNotation)
        # self.text_entry.setValidator(self.validator)

        # Create a QPushButton
        self.button = QPushButton('Submit', self)
        self.button.clicked.connect(self.show_text)

        # Add widgets to layout
        layout.addWidget(self.label)
        layout.addWidget(self.text_entry)
        layout.addWidget(self.button)

        # Set layout for the window
        self.setLayout(layout)

    def show_text(self):
        text = self.text_entry.text()
        self.label.setText(f'You entered: {text}')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SimpleWindow()
    window.show()
    sys.exit(app.exec_())