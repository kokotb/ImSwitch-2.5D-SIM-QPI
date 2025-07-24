import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtChart import QChart, QChartView, QLineSeries
from PyQt5.QtGui import QPainter
from PyQt5.QtCore import QPointF

class ChartWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PyQt5 Chart Example")
        self.setGeometry(100, 100, 600, 400)

        # Create a QLineSeries and add some data points
        series = QLineSeries()
        data = [QPointF(x, x**0.5) for x in range(10)]  # y = sqrt(x)
        series.append(data)

        # Create a QChart and add the series
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Line Chart Example")
        chart.createDefaultAxes()

        # Create a QChartView with the chart
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)

        # Set up layout
        layout = QVBoxLayout()
        layout.addWidget(chart_view)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

# Run the application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChartWindow()
    window.show()
    sys.exit(app.exec_())
