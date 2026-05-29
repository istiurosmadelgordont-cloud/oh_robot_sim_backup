
#include <QtCore/QDir>
#include <QtCore/QFileInfo>
#include <QtCore/QTimer>

#include <QtWidgets/QApplication>
#include <QtWidgets/QInputDialog>
#include <QtWidgets/QLineEdit>
#include <QtWidgets/QToolTip>
#include <QtWidgets/QVBoxLayout>

#include <QtGui/QPainter>
#include <QtGui/QScreen>

#include <fstream>
#include <yaml-cpp/yaml.h>

#include "map_viewer.h"

void MapViewer::loadMap(const QString &yamlPath)  {
    this->currentMapFn = yamlPath;
    YAML::Node config = YAML::LoadFile(yamlPath.toStdString());
    
    resolution = config["resolution"].as<double>();
    origin_x = config["origin"][0].as<double>();
    origin_y = config["origin"][1].as<double>();

    if (config["mode"]) {
        mode = QString::fromStdString(config["mode"].as<std::string>());
        printf("Use mode: %s\n", mode.toStdString().c_str());
    }
    if (config["occupied_thresh"]) {
        occupied_thresh = config["occupied_thresh"].as<double>();
        printf("Use occupied threshold = %.3f\n", occupied_thresh);
    }
    if (config["free_thresh"]) {
        free_thresh = config["free_thresh"].as<double>();
        printf("Use free threshold = %.3f\n", free_thresh);
    }
    if (config["negate"]) {
        negate = config["negate"].as<int>();
        printf("Use negate = %d\n", negate);
    }
    
    QString pgmPath = QFileInfo(yamlPath).dir().filePath(
        QString::fromStdString(config["image"].as<std::string>()));
    
    QImage img = loadPGM(pgmPath);
    if (!img.isNull()) {
        mapImage = img;
        setFixedSize(mapImage.size());
        update();
    }
}

void MapViewer::loadAnnotations() {
    annotations.clear();
    try {
        YAML::Node node = YAML::LoadFile(annotationFile.toStdString());
        // load corresponding map file (if exists)
        const auto &mapFn = node["pgm_map"];
        if (mapFn) {
            this->loadMap(QString::fromStdString(mapFn.as<std::string>()));
        }
        for (const auto& item : node["annotations"]) {
            Annotation ann;
            const auto& on_map = item["map_transform"];
            const auto& pos_on_map = on_map["translation"];
            ann.position.x = pos_on_map["x"].as<double>();
            ann.position.y = pos_on_map["y"].as<double>();
            ann.position.z = pos_on_map["z"].as<double>();
            const auto& orient_on_map = item["rotation"];
            if (orient_on_map) {
                ann.orientation.w = orient_on_map["w"].as<double>();
                ann.orientation.x = orient_on_map["x"].as<double>();
                ann.orientation.y = orient_on_map["y"].as<double>();
                ann.orientation.z = orient_on_map["z"].as<double>();
            }
            
            const auto &posePos = item["position"];
            const auto &poseR = item["orientation"];
            ann.pose.present = posePos.IsDefined() && poseR.IsDefined();
            if (ann.pose.present) {
                ann.pose.x = posePos["x"].as<double>();
                ann.pose.y = posePos["y"].as<double>();
                ann.pose.z = posePos["z"].as<double>();
                ann.pose.rw = poseR["w"].as<double>();
                ann.pose.rx = poseR["x"].as<double>();
                ann.pose.ry = poseR["y"].as<double>();
                ann.pose.rz = poseR["z"].as<double>();
            }

            const auto& image = item["image"];
            if (image) {
                ann.image.width = image["width"].as<int>();
                ann.image.height = image["height"].as<int>();
                ann.image.encoding = QString::fromStdString(image["encoding"].as<std::string>());
                ann.image.frame_id = QString::fromStdString(image["frame_id"].as<std::string>());
                ann.image.image_file = QString::fromStdString(image["image_file"].as<std::string>());
                ann.image.depth_image_file = QString::fromStdString(image["depth_image_file"].as<std::string>());
            }
            ann.image.present = image.IsDefined();

            const auto &msg = item["text"];
            if (msg) {
                ann.text = QString::fromStdString(item["text"].as<std::string>());
            } else {
                // maybe picture only
                if (!image.IsDefined()) {
                    printf("WARN: ignore useless annotation detected without image or text\n");
                    continue;
                }
            }
            annotations.append(ann);
        }
    } catch (const YAML::ParserException &ex) {
        printf("WARN: ignore invalid annotation file format: %s\n", ex.msg.c_str());
    } catch (const YAML::BadFile &ex) {
        printf("WARN: ignore bad file: %s\n", ex.msg.c_str());
    } catch (const std::exception &ex) {
        printf("WARN: unexpected error: %s\n", ex.what());
    }
    update();
}

void MapViewer::saveAnnotations() {
    YAML::Emitter out;

    out << YAML::BeginMap;
    // save current map file
    out << YAML::Key << "pgm_map";
    out << YAML::Value << this->currentMapFn.toStdString();
    out << YAML::Key << "annotations";
    out << YAML::Value << YAML::BeginSeq;
    
    for (const auto& ann : annotations) {
        out << YAML::BeginMap;

        out << YAML::Key << "map_transform";
        out << YAML::Value << YAML::BeginMap;
        {
            out << YAML::Key << "translation";
            out << YAML::Value << YAML::BeginMap;
            {
                out << YAML::Key << "x" << YAML::Value << ann.position.x;
                out << YAML::Key << "y" << YAML::Value << ann.position.y;
                out << YAML::Key << "z" << YAML::Value << ann.position.z;
            }
            out << YAML::EndMap;

            out << YAML::Key << "rotation";
            out << YAML::Value << YAML::BeginMap;
            {
                out << YAML::Key << "w" << YAML::Value << ann.orientation.w;
                out << YAML::Key << "x" << YAML::Value << ann.orientation.x;
                out << YAML::Key << "y" << YAML::Value << ann.orientation.y;
                out << YAML::Key << "z" << YAML::Value << ann.orientation.z;
            }
            out << YAML::EndMap;
        }
        out << YAML::EndMap;

        if (ann.pose.present) {
            out << YAML::Key << "position";
            out << YAML::Value << YAML::BeginMap;
            {
                out << YAML::Key << "x" << YAML::Value << ann.pose.x;
                out << YAML::Key << "y" << YAML::Value << ann.pose.y;
                out << YAML::Key << "z" << YAML::Value << ann.pose.z;
            }
            out << YAML::EndMap;

            out << YAML::Key << "orientation";
            out << YAML::Value << YAML::BeginMap;
            {
                out << YAML::Key << "w" << YAML::Value << ann.pose.rw;
                out << YAML::Key << "x" << YAML::Value << ann.pose.rx;
                out << YAML::Key << "y" << YAML::Value << ann.pose.ry;
                out << YAML::Key << "z" << YAML::Value << ann.pose.rz;
            }
            out << YAML::EndMap;
        }

        if (ann.image.present) {
            out << YAML::Key << "image";
            out << YAML::Value << YAML::BeginMap;
            {
                out << YAML::Key << "width" << YAML::Value << ann.image.width;
                out << YAML::Key << "height" << YAML::Value << ann.image.height;
                out << YAML::Key << "encoding" << YAML::Value << ann.image.encoding.toStdString();
                out << YAML::Key << "frame_id" << YAML::Value << ann.image.frame_id.toStdString();
                out << YAML::Key << "image_file" << YAML::Value << ann.image.image_file.toStdString();
                out << YAML::Key << "depth_image_file" << YAML::Value << ann.image.depth_image_file.toStdString();
            }
            out << YAML::EndMap;
        }

        QString trimmedText = ann.text.trimmed();
        if (!trimmedText.isEmpty()) {
            out << YAML::Key << "text" << YAML::Value << trimmedText.toStdString();
        }

        out << YAML::EndMap;
    }
    
    out << YAML::EndSeq;
    out << YAML::EndMap;
    
    std::ofstream fout(annotationFile.toStdString());
    fout << out.c_str();
}

void MapViewer::paintEvent(QPaintEvent *) {
    QPainter painter(this);

    // not drawing annotation or other components if map is not loaded
    if (mapImage.isNull()) return;
    
    // Draw map
    painter.drawImage(0, 0, mapImage);
    
    // Draw annotations
    painter.setPen(QPen(Qt::red, 2));
    painter.setBrush(Qt::red);
    
    for (const auto& ann : annotations) {
        QPoint pixelPos = mapToPixel(ann.position.x, ann.position.y);
        painter.drawEllipse(pixelPos, 6, 6);
        
        // Draw cross
        painter.drawLine(pixelPos.x() - 10, pixelPos.y(), 
                        pixelPos.x() + 10, pixelPos.y());
        painter.drawLine(pixelPos.x(), pixelPos.y() - 10, 
                        pixelPos.x(), pixelPos.y() + 10);
    }
}

void MapViewer::mouseMoveEvent(QMouseEvent *event)  {
    if (!mapImage.isNull()) {
        QPoint pos = event->pos();
        double map_x = origin_x + pos.x() * resolution;
        double map_y = origin_y + (mapImage.height() - pos.y()) * resolution;
        
        emit coordinatesChanged(map_x, map_y);
        
        // Check if hovering over annotation
        for (const auto& ann : annotations) {
            QPoint annPos = mapToPixel(ann.position.x, ann.position.y);
            if ((pos - annPos).manhattanLength() < 10) {
                this->renderAnnotationTooltip(event->globalPos(), ann);
                return;
            }
        }
        // close tooltip if not rendering
        this->closeTooltip();
    }
}

void MapViewer::closeTooltip() {
    if (currentTooltip) {
        currentTooltip->hide();
        currentTooltip->deleteLater();
        currentTooltip = nullptr;
    }
}

void MapViewer::renderAnnotationTooltip(const QPoint &pt, const Annotation &ann) {
    // Hide any previous tooltip
    this->closeTooltip();

    // Hide any simple text tooltip (we'll show our richer widget instead)
    QToolTip::hideText();

    // show simple text as fallback immediately
    QToolTip::showText(pt, 
                    QString("(%1, %2)\n%3")
                        .arg(ann.position.x)
                        .arg(ann.position.y)
                        .arg(ann.text),
                    this);

    // render picture under the text
    if (ann.image.present) {
        // resolve image path relative to annotation file dir
        QFileInfo annFi(annotationFile);
        QDir imageAbsDir = annFi.absoluteDir();
        QString imageAbsPath = imageAbsDir.filePath(ann.image.image_file);

        // Create a custom tooltip widget
        QLabel *tooltipLabel = new QLabel(nullptr, Qt::ToolTip | Qt::FramelessWindowHint);
        tooltipLabel->setAttribute(Qt::WA_DeleteOnClose);
        tooltipLabel->setAttribute(Qt::WA_TranslucentBackground, false);
        tooltipLabel->setFrameStyle(QFrame::Box | QFrame::Plain);
        tooltipLabel->setLineWidth(1);
        tooltipLabel->setMargin(5);
        
        // Load and scale the image
        QPixmap pixmap(imageAbsPath);
        if (!pixmap.isNull()) {
            // Scale image if it's too large (max 300x300 pixels)
            if (pixmap.width() > 300 || pixmap.height() > 300) {
                pixmap = pixmap.scaled(300, 300, Qt::KeepAspectRatio, Qt::SmoothTransformation);
            }
            
            // Create rich text with image and text
            QString html = QString(
                "<div style='text-align: center;'>"
                "<p style='margin: 0 0 5px 0;'><b>Position:</b> (%1, %2)</p>"
                "<p style='margin: 0 0 5px 0;'>%3</p>"
                "</div>")
                .arg(ann.position.x)
                .arg(ann.position.y)
                .arg(ann.text);
            
            // Create a vertical layout for text and image
            QWidget *contentWidget = new QWidget();
            QVBoxLayout *layout = new QVBoxLayout(contentWidget);
            layout->setContentsMargins(5, 5, 5, 5);
            layout->setSpacing(5);
            
            // Add text label
            QLabel *textLabel = new QLabel(html);
            textLabel->setTextFormat(Qt::RichText);
            textLabel->setAlignment(Qt::AlignCenter);
            layout->addWidget(textLabel);
            
            // Add image label
            QLabel *imageLabel = new QLabel();
            imageLabel->setPixmap(pixmap);
            imageLabel->setAlignment(Qt::AlignCenter);
            layout->addWidget(imageLabel);
            
            contentWidget->setLayout(layout);
            
            // Render the widget to a pixmap for the tooltip
            QPixmap tooltipPixmap(contentWidget->sizeHint());
            contentWidget->render(&tooltipPixmap);
            
            tooltipLabel->setPixmap(tooltipPixmap);
            tooltipLabel->adjustSize();
            
            // Position the tooltip near the cursor
            tooltipLabel->move(pt + QPoint(10, 10));
            tooltipLabel->show();

            // Store reference to clean up when mouse moves away
            currentTooltip = tooltipLabel;
            
            delete contentWidget;
        } else {
            // Image failed to load, keep the simple text tooltip
            printf("ERROR: Failed to load annotation image: %s\n", imageAbsPath.toStdString().c_str());
            delete tooltipLabel;  // Clean up if image load failed
        }
    }
}

// NOTE: 2D map for now (Annotation::position::z is not used)
void MapViewer::mouseDoubleClickEvent(QMouseEvent *event) {
    if (event->button() == Qt::LeftButton && !mapImage.isNull()) {

        // close the tooltip before editing
        this->closeTooltip();

        QPoint pos = event->pos();
        double map_x = origin_x + pos.x() * resolution;
        double map_y = origin_y + (mapImage.height() - pos.y()) * resolution;
        
        // Check if clicking near an existing annotation
        int existingIndex = -1;
        for (int i = 0; i < annotations.size(); ++i) {
            QPoint annPos = mapToPixel(annotations[i].position.x, annotations[i].position.y);
            if ((pos - annPos).manhattanLength() < this->edit_thresh_pixel) {
                existingIndex = i;
                break;
            }
        }
        
        bool ok;
        QString text;
        if (existingIndex >= 0) {
            // Edit existing annotation
            text = QInputDialog::getText(this, "Edit Annotation",
                                        "Edit annotation text:",
                                        QLineEdit::Normal, 
                                        annotations[existingIndex].text, &ok);
            if (ok && !text.isEmpty()) {
                annotations[existingIndex].text = text;
                saveAnnotations();
                update();
                emit annotationAdded(annotations[existingIndex].position.x, 
                                   annotations[existingIndex].position.y, text);
            }
        } else {
            // Create new annotation
            text = QInputDialog::getText(this, "Add Annotation",
                                        "Enter annotation text:",
                                        QLineEdit::Normal, "", &ok);
            if (ok && !text.isEmpty()) {
                Annotation ann;
                ann.position.x = map_x;
                ann.position.y = map_y;
                ann.position.z = ann.orientation.w
                    = ann.orientation.x = ann.orientation.y = ann.orientation.z = 0;
                ann.image.present = false;
                ann.text = text;
                annotations.append(ann);
                saveAnnotations();
                update();
                emit annotationAdded(map_x, map_y, text);
            }
        }
    }
}

QPoint MapViewer::mapToPixel(double x, double y) {
    int px = (x - origin_x) / resolution;
    int py = mapImage.height() - (y - origin_y) / resolution;
    return QPoint(px, py);
}

QImage MapViewer::loadPGM(const QString &path) {
    std::ifstream file(path.toStdString(), std::ios::binary);
    if (!file) return QImage();
    
    std::string magic;
    int width, height, maxval;
    file >> magic >> width >> height >> maxval;
    file.get(); // consume newline
    
    if (magic != "P5") return QImage();
    
    QImage img(width, height, QImage::Format_RGB888);
    for (int y = 0; y < height; y++) {
        for (int x = 0; x < width; x++) {
            unsigned char val = file.get();
            QColor color;
            int gray = negate ? val : 255 - val;

            if (mode == "trinary") {
                // Convert pixel value to probability (0-100 range typically)
                double prob = gray / 255.0;  // or use specific mapping based on your data
                
                if (prob >= occupied_thresh) color = Qt::black;   // occupied
                else if (prob <= free_thresh) color = Qt::white;  // free
                else color = Qt::gray;                            // unknown
            }
            else { // "raw"
                // Show continuous grayscale
                color = QColor(gray, gray, gray);
            }
            img.setPixel(x, y, color.rgb());
        }
    }
    return img;
}
