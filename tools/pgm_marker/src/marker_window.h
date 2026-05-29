#pragma once

#include <QtWidgets/QMainWindow>

#include "map_viewer.h"


class PgmMarkerWindow : public QMainWindow {
    Q_OBJECT
public:
    PgmMarkerWindow(const QString &annotationYaml);

private slots:
    void openMap();
    
    void updateStatus(double x, double y);

private:
    MapViewer *mapViewer;
};
