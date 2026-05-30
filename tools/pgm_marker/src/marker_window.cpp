
#include <QtWidgets/QFileDialog>
#include <QtWidgets/QMenuBar>
#include <QtWidgets/QScrollArea>
#include <QtWidgets/QStatusBar>
#include <QtWidgets/QVBoxLayout>

#include "marker_window.h"


PgmMarkerWindow::PgmMarkerWindow(const QString &annotationYaml)  {
    mapViewer = new MapViewer(annotationYaml, this);
    
    QScrollArea *scrollArea = new QScrollArea(this);
    scrollArea->setWidget(mapViewer);
    scrollArea->setWidgetResizable(false);
    setCentralWidget(scrollArea);
    
    QMenu *fileMenu = menuBar()->addMenu("&File");
    fileMenu->addAction("&Open Map...", this, &PgmMarkerWindow::openMap);
    fileMenu->addAction("E&xit", this, &QWidget::close);
    
    statusBar()->showMessage("Ready");
    
    connect(mapViewer, &MapViewer::coordinatesChanged,
            this, &PgmMarkerWindow::updateStatus);
    
    setWindowTitle("ROS2 Map Viewer");
    resize(800, 600);
}

void PgmMarkerWindow::openMap()  {
    QString path = QFileDialog::getOpenFileName(this, "Open Map YAML",
                                                    "", "YAML Files (*.yaml)");
    if (!path.isEmpty()) {
        mapViewer->loadMap(path);
        statusBar()->showMessage("Map loaded: " + path);
    }
}

void PgmMarkerWindow::updateStatus(double x, double y) {
    statusBar()->showMessage(QString("Map coordinates: x=%1, y=%2").arg(x).arg(y));
}

