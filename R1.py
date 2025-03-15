import sys
import os
import subprocess
from pathlib import Path
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QSize
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QFileDialog,
    QListWidget, QCheckBox, QSpinBox, QProgressBar, QMessageBox,
    QListWidgetItem, QStyleFactory, QComboBox, QTabWidget, QTextBrowser
)
from PyQt6.QtGui import QFont, QColor, QPalette

class EnhancedConvertWorker(QObject):
    progress_incremented = pyqtSignal()
    output_received = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    current_file = pyqtSignal(str)

    def __init__(self, commands, output_dir):
        super().__init__()
        self.commands = commands
        self.output_dir = output_dir
        self._is_running = True

    def run(self):
        success = True
        error_msg = ""
        try:
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)
            total = len(self.commands)
            for idx, cmd_parts in enumerate(self.commands):
                if not self._is_running:
                    break
                self.current_file.emit(cmd_parts[-1])
                self.output_received.emit(f"[{idx+1}/{total}] Executing: {' '.join(cmd_parts)}\n")

                try:
                    process = subprocess.run(
                        cmd_parts,
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True
                    )
                    self.output_received.emit(process.stdout)
                except subprocess.CalledProcessError as e:
                    self.output_received.emit(f"Error: {e.output}")
                    success = False
                    error_msg = f"Failed to process {cmd_parts[-1]}"
                    break

                self.progress_incremented.emit()
        except Exception as e:
            error_msg = str(e)
            success = False
            self.output_received.emit(f"Critical Error: {error_msg}")
        finally:
            self.finished.emit(success, error_msg)

    def stop(self):
        self._is_running = False

class ImprovedGMConvertGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.thread = None
        self.initUI()
        self.check_gm_installed()
        self.set_dark_theme()

    def set_dark_theme(self):
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
        dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(142, 45, 197))
        dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        self.setPalette(dark_palette)

    def initUI(self):
        self.setWindowTitle('GM Convert Professional')
        self.setGeometry(100, 100, 1000, 800)
        self.setAcceptDrops(True)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Create tab widget
        tab_widget = QTabWidget()
        conversion_tab = QWidget()
        settings_tab = QWidget()
        tab_widget.addTab(conversion_tab, "Conversion")
        tab_widget.addTab(settings_tab, "Settings")

        # Conversion Tab
        conversion_layout = QVBoxLayout(conversion_tab)

        # File Selection
        file_group = QGroupBox("Input Files")
        file_layout = QVBoxLayout()

        self.file_list = QListWidget()
        self.file_list.setDragDropMode(QListWidget.DragDropMode.DropOnly)
        self.file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.file_list.setStyleSheet("QListWidget { background-color: #252525; }")

        btn_layout = QHBoxLayout()
        self.btn_add_files = QPushButton("Add Files")
        self.btn_add_files.clicked.connect(self.browse_files)
        self.btn_clear_files = QPushButton("Clear List")
        self.btn_clear_files.clicked.connect(self.clear_files)

        btn_layout.addWidget(self.btn_add_files)
        btn_layout.addWidget(self.btn_clear_files)

        file_layout.addLayout(btn_layout)
        file_layout.addWidget(self.file_list)
        file_group.setLayout(file_layout)

        # Output Settings
        output_group = QGroupBox("Output Settings")
        output_layout = QVBoxLayout()

        self.output_dir = QLineEdit()
        self.btn_output_dir = QPushButton("Select Output Directory")
        self.btn_output_dir.clicked.connect(self.browse_output_dir)

        self.chk_overwrite = QCheckBox("Overwrite existing files")
        self.chk_preserve_structure = QCheckBox("Preserve directory structure")

        output_layout.addWidget(QLabel("Output Directory:"))
        output_layout.addWidget(self.output_dir)
        output_layout.addWidget(self.btn_output_dir)
        output_layout.addWidget(self.chk_overwrite)
        output_layout.addWidget(self.chk_preserve_structure)
        output_group.setLayout(output_layout)

        # Conversion Parameters
        param_group = QGroupBox("Conversion Parameters")
        param_layout = QVBoxLayout()

        # Format and Quality
        format_layout = QHBoxLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItems(["jpg", "png", "webp", "tiff", "bmp", "Same as input"])
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(90)

        format_layout.addWidget(QLabel("Output Format:"))
        format_layout.addWidget(self.format_combo)
        format_layout.addWidget(QLabel("Quality:"))
        format_layout.addWidget(self.quality_spin)

        # Image Manipulation
        transform_layout = QHBoxLayout()
        self.rotate_combo = QComboBox()
        self.rotate_combo.addItems(["0°", "90°", "180°", "270°"])
        self.flip_check = QCheckBox("Flip Horizontal")
        self.flop_check = QCheckBox("Flip Vertical")

        transform_layout.addWidget(QLabel("Rotation:"))
        transform_layout.addWidget(self.rotate_combo)
        transform_layout.addWidget(self.flip_check)
        transform_layout.addWidget(self.flop_check)

        # Resize Options
        resize_layout = QHBoxLayout()
        self.resize_check = QCheckBox("Resize")
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 10000)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 10000)
        self.aspect_check = QCheckBox("Maintain Aspect Ratio")
        self.aspect_check.setChecked(True)

        resize_layout.addWidget(self.resize_check)
        resize_layout.addWidget(QLabel("Width:"))
        resize_layout.addWidget(self.width_spin)
        resize_layout.addWidget(QLabel("Height:"))
        resize_layout.addWidget(self.height_spin)
        resize_layout.addWidget(self.aspect_check)

        param_layout.addLayout(format_layout)
        param_layout.addLayout(transform_layout)
        param_layout.addLayout(resize_layout)
        param_group.setLayout(param_layout)

        # Progress and Logs
        self.log_browser = QTextBrowser()
        #self.log_browser.setMaximumBlockCount(1000)  # Limit log memory usage
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate by default

        status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.file_counter = QLabel("0 files queued")

        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.file_counter)

        # Control Buttons
        control_layout = QHBoxLayout()
        self.btn_convert = QPushButton("Start Conversion")
        self.btn_convert.clicked.connect(self.start_conversion)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.cancel_conversion)
        self.btn_cancel.setEnabled(False)

        control_layout.addWidget(self.btn_convert)
        control_layout.addWidget(self.btn_cancel)

        # Assemble Conversion Tab
        conversion_layout.addWidget(file_group)
        conversion_layout.addWidget(output_group)
        conversion_layout.addWidget(param_group)
        conversion_layout.addWidget(self.log_browser)
        conversion_layout.addWidget(self.progress_bar)
        conversion_layout.addLayout(status_layout)
        conversion_layout.addLayout(control_layout)

        # Settings Tab (example content)
        settings_layout = QVBoxLayout(settings_tab)
        advanced_group = QGroupBox("Advanced Settings")
        advanced_layout = QVBoxLayout()

        self.chk_verbose = QCheckBox("Verbose logging")
        self.chk_parallel = QCheckBox("Parallel processing (experimental)")
        self.chk_color_profile = QCheckBox("Preserve color profiles")

        advanced_layout.addWidget(self.chk_verbose)
        advanced_layout.addWidget(self.chk_parallel)
        advanced_layout.addWidget(self.chk_color_profile)
        advanced_group.setLayout(advanced_layout)

        settings_layout.addWidget(advanced_group)
        settings_layout.addStretch()

        # Main Layout
        layout.addWidget(tab_widget)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp')
        self.input_files = [f for f in files if f.lower().endswith(valid_extensions)]
        self.update_file_list()

    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Images", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.webp)"
        )
        if files:
            self.input_files = files
            self.update_file_list()

    def update_file_list(self):
        self.file_list.clear()
        for f in self.input_files:
            item = QListWidgetItem(f)
            item.setToolTip(f)
            self.file_list.addItem(item)
        self.file_counter.setText(f"{len(self.input_files)} files queued")

    def clear_files(self):
        self.input_files = []
        self.file_list.clear()
        self.file_counter.setText("0 files queued")

    def browse_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.output_dir.setText(directory)

    def validate_settings(self):
        if not self.input_files:
            QMessageBox.warning(self, "Warning", "Please select input files!")
            return False
        if not self.output_dir.text():
            QMessageBox.warning(self, "Warning", "Please select output directory!")
            return False
        try:
            if not os.access(self.output_dir.text(), os.W_OK):
                raise PermissionError("Output directory is not writable")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return False

    def build_commands(self):
        commands = []
        output_format = self.format_combo.currentText().lower()
        if output_format == "same as input":
            output_format = None

        for input_path in self.input_files:
            input_path = Path(input_path)
            output_path = Path(self.output_dir.text())

            if self.chk_preserve_structure.isChecked():
                output_path = output_path / input_path.parent.relative_to(input_path.anchor)

            output_path.mkdir(parents=True, exist_ok=True)

            if output_format:
                output_file = output_path / f"{input_path.stem}.{output_format}"
            else:
                output_file = output_path / f"{input_path.name}"

            cmd = ["gm", "convert", str(input_path)]

            # Add transformation parameters
            if self.resize_check.isChecked():
                cmd += ["-resize", f"{self.width_spin.value()}x{self.height_spin.value()}"]
                if self.aspect_check.isChecked():
                    cmd += ["-filter", "Lanczos", "-unsharp", "0.25x0.25+8+0.065"]

            rotation = self.rotate_combo.currentText().rstrip('°')
            if rotation != "0":
                cmd += ["-rotate", rotation]

            if self.flip_check.isChecked():
                cmd += ["-flip"]
            if self.flop_check.isChecked():
                cmd += ["-flop"]

            # Add quality if format supports it
            if output_format in ('jpg', 'webp', 'tiff'):
                cmd += ["-quality", str(self.quality_spin.value())]

            if self.chk_color_profile.isChecked():
                cmd += ["-profile", "RGB.icm"]

            cmd.append(str(output_file))
            commands.append(cmd)

        return commands

    def start_conversion(self):
        if not self.validate_settings():
            return

        commands = self.build_commands()
        self.log_browser.clear()
        self.btn_convert.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setRange(0, len(commands))
        self.progress_bar.setValue(0)

        self.thread = QThread()
        self.worker = EnhancedConvertWorker(commands, self.output_dir.text())
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.progress_incremented.connect(lambda: self.progress_bar.setValue(self.progress_bar.value() + 1))
        self.worker.output_received.connect(self.update_log)
        self.worker.finished.connect(self.conversion_finished)
        self.worker.current_file.connect(lambda f: self.status_label.setText(f"Processing: {f}"))

        self.thread.start()

    def cancel_conversion(self):
        if self.worker:
            self.worker.stop()
        self.btn_cancel.setEnabled(False)
        self.status_label.setText("Conversion canceled")
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)

    def update_log(self, text):
        self.log_browser.append(text)
        self.log_browser.ensureCursorVisible()

    def conversion_finished(self, success, error_msg):
        self.btn_convert.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1 if success else 0)

        if success:
            QMessageBox.information(self, "Success", "All conversions completed successfully!")
            self.status_label.setText("Ready")
        else:
            QMessageBox.critical(self, "Error", error_msg)
            self.status_label.setText("Conversion failed")

    def check_gm_installed(self):
        try:
            result = subprocess.run(["gm", "version"], capture_output=True, text=True)
            if "GraphicsMagick" not in result.stdout:
                raise FileNotFoundError
            self.log_browser.append("GraphicsMagick version detected:\n" + result.stdout)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                "GraphicsMagick (gm) not found! Please install it and ensure it's in your PATH."
            )
            self.btn_convert.setEnabled(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    window = ImprovedGMConvertGUI()
    window.show()
    sys.exit(app.exec())
