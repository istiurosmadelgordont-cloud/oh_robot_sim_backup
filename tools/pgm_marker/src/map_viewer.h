#pragma once

#include <QtCore/QPointer>

#include <QtWidgets/QLabel>
#include <QtWidgets/QWidget>

#include <QtGui/QPixmap>
#include <QtGui/QImage>
#include <QtGui/QMouseEvent>


struct Annotation {
    /* position on the map */
    struct Pos {
        double x, y, z;
    } position;
    /* orientation to the map tranformation (optional) */
    struct Orient {
        double x, y, z, w;
    } orientation;
    /* optional (use `present`) */
    struct Image {
        int width, height;
        QString encoding;
        QString frame_id;
        /* NOTE: file name here use the relative path to the annotation file */
        QString image_file;
        QString depth_image_file;
        bool present;
    } image;

    /* absolute pose of the robot */
    struct Pose {
        double x, y, z, rw, rx, ry, rz;
        bool present;
    } pose;
    
    /* optional if image is present */
    QString text;
};


class MapViewer : public QWidget {
    Q_OBJECT
public:
    MapViewer(const QString &annoFn, QWidget *parent = nullptr) : QWidget(parent) {
        setMouseTracking(true);
        annotationFile = annoFn;
        loadAnnotations();
    }

    void loadMap(const QString &yamlPath);
    void loadAnnotations();
    void saveAnnotations();

protected:
    void paintEvent(QPaintEvent *) override;
    void mouseMoveEvent(QMouseEvent *event) override;
    void mouseDoubleClickEvent(QMouseEvent *event) override;

signals:
    void coordinatesChanged(double x, double y);
    void annotationAdded(double x, double y, const QString& text);

private:
    QPoint mapToPixel(double x, double y);
    QImage loadPGM(const QString &path);

    void closeTooltip();
    void renderAnnotationTooltip(const QPoint &pt, const Annotation &ann);

    QString currentMapFn;
    QImage mapImage;
    QString mode = "trinary";

    int edit_thresh_pixel = 10;

    double occupied_thresh = 0.65;
    double free_thresh = 0.196;
    int negate = 0;
    
    double resolution = 0.05;
    double origin_x = 0.0;
    double origin_y = 0.0;

    QString annotationFile;
    QList<Annotation> annotations;

    // for displaying image on tooltip
    QPointer<QLabel> currentTooltip;
};
