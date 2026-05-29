
#include <QtCore/QCommandLineParser>
#include <QtCore/QCommandLineOption>

#include <QtWidgets/QApplication>

#include "marker_window.h"

const std::string DEFAULT_ANNOTATION_FILE = "annotation_map.yaml";


int main(int argc, char *argv[]) {
    QApplication app(argc, argv);

    // for --help
    QCoreApplication::setApplicationName("PgmMarker");
    QCoreApplication::setApplicationVersion("1.0");

    QCommandLineParser parser;
    parser.setApplicationDescription("A ROS2 package of Pgm Marker Tool written by SSRVodka ;)");
    parser.addHelpOption();
    parser.addVersionOption();

    QCommandLineOption annotationOption(
        QStringList() << "a" << "annotation",
        QCoreApplication::translate(
            "main",
            "The path of annotation file ('%1' by default)"
        ).arg(DEFAULT_ANNOTATION_FILE.c_str()),
        QCoreApplication::translate("main", "file"),
        QString::fromStdString(DEFAULT_ANNOTATION_FILE)
    );

    parser.addOption(annotationOption);
    parser.process(app);

    QString annotationPath = parser.value(annotationOption);
    std::string ANNOTATION_FILE = annotationPath.toStdString();
    // create if not exist
    FILE *fh = fopen(ANNOTATION_FILE.c_str(), "a+");
    fclose(fh);

    printf("Use annotation file: '%s'\n", ANNOTATION_FILE.c_str());

    PgmMarkerWindow window(QString::fromStdString(ANNOTATION_FILE));
    window.show();
    return app.exec();
}

