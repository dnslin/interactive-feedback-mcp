# 交互式反馈 MCP 用户界面
# 由 Fábio Ferreira 开发 (https://x.com/fabiomlferreira)
# 灵感来源/相关项目: dotcursorrules.com (https://dotcursorrules.com/)
# 由 Pau Oliva (https://x.com/pof) 增强，借鉴了 https://github.com/ttommyth/interactive-mcp 的想法
import os
import sys
import json
import argparse
from typing import Optional, TypedDict, List

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QTextEdit, QGroupBox,
    QFrame
)
from PySide6.QtCore import Qt, Signal, QObject, QTimer, QSettings
from PySide6.QtGui import QTextCursor, QIcon, QKeyEvent, QPalette, QColor

class FeedbackResult(TypedDict):
    interactive_feedback: str

# 定义颜色常量以便在调色板和QSS中保持一致
WINDOW_BACKGROUND_COLOR = QColor(48, 48, 48)
BASE_COLOR = QColor(38, 38, 38)
TEXT_COLOR = Qt.white # QColor(220, 220, 220) 也可以考虑非纯白
DISABLED_TEXT_COLOR = QColor(127, 127, 127)
ACCENT_COLOR = QColor(28, 169, 201)  # #1CA9C9 现代青蓝色
ACCENT_HOVER_COLOR = QColor(31, 187, 223) # #1FBBDF
ACCENT_PRESSED_COLOR = QColor(25, 150, 179) # #1996B3
BORDER_COLOR = QColor(65, 65, 65)
SEPARATOR_COLOR = QColor(60, 60, 60)

MODERN_QSS = f"""
QMainWindow {{
    background-color: {WINDOW_BACKGROUND_COLOR.name()};
}}

QGroupBox {{
    border: 1px solid {BORDER_COLOR.name()};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 15px; /* 为标题和内容增加顶部内边距 */
    font-weight: bold;
    color: {TEXT_COLOR.name() if isinstance(TEXT_COLOR, QColor) else "white"}; /* GroupBox 标题颜色 */
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px 8px 8px; /* 调整标题的填充 */
    left: 10px;
}}

QLabel {{
    color: {TEXT_COLOR.name() if isinstance(TEXT_COLOR, QColor) else "white"};
    padding-left: 5px;
    padding-right: 5px;
    padding-top: 2px;
    padding-bottom: 2px;
}}

QTextEdit#feedback_text_edit {{
    background-color: {BASE_COLOR.name()};
    color: {TEXT_COLOR.name() if isinstance(TEXT_COLOR, QColor) else "white"};
    border: 1px solid {BORDER_COLOR.name()};
    border-radius: 6px;
    padding: 10px;
}}

QPushButton#submit_button {{
    background-color: {ACCENT_COLOR.name()};
    color: white;
    border: none;
    padding: 10px 22px;
    border-radius: 6px;
    font-weight: bold;
    min-height: 20px;
}}

QPushButton#submit_button:hover {{
    background-color: {ACCENT_HOVER_COLOR.name()};
}}

QPushButton#submit_button:pressed {{
    background-color: {ACCENT_PRESSED_COLOR.name()};
}}

QCheckBox {{
    spacing: 10px;
    color: {TEXT_COLOR.name() if isinstance(TEXT_COLOR, QColor) else "white"};
    padding: 5px 0;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid {BORDER_COLOR.name()}; /* 指示器边框颜色 */
    background-color: {BASE_COLOR.name()}; /* 未选中时背景色 */
}}

QCheckBox::indicator:hover {{
    border: 1px solid {ACCENT_COLOR.name()};
}}

QCheckBox::indicator:checked {{
    background-color: {ACCENT_COLOR.name()};
    border: 1px solid {ACCENT_COLOR.name()};
    /* 可以考虑添加一个小的白色对勾图标 image: url(:/icons/checkmark.svg); */
}}

QCheckBox::indicator:disabled {{
    border: 1px solid {DISABLED_TEXT_COLOR.name()};
    background-color: transparent;
}}

QFrame[frameShape="4"] {{ /* QFrame.Shape.HLine */
    border: none;
    max-height: 1px;
    background-color: {SEPARATOR_COLOR.name()}; /* 使用背景色实现细线 */
    margin-top: 10px;
    margin-bottom: 10px;
}}
"""

def get_dark_mode_palette(app: QApplication): # app 参数保留，虽然QSS会覆盖很多
    darkPalette = QPalette() # 创建一个新的调色板，而不是修改应用的现有调色板
    darkPalette.setColor(QPalette.Window, WINDOW_BACKGROUND_COLOR)
    darkPalette.setColor(QPalette.WindowText, TEXT_COLOR)
    darkPalette.setColor(QPalette.Disabled, QPalette.WindowText, DISABLED_TEXT_COLOR)
    darkPalette.setColor(QPalette.Base, BASE_COLOR)
    darkPalette.setColor(QPalette.AlternateBase, QColor(55, 55, 55)) # 比Base稍亮
    darkPalette.setColor(QPalette.ToolTipBase, WINDOW_BACKGROUND_COLOR)
    darkPalette.setColor(QPalette.ToolTipText, TEXT_COLOR)
    darkPalette.setColor(QPalette.Text, TEXT_COLOR)
    darkPalette.setColor(QPalette.Disabled, QPalette.Text, DISABLED_TEXT_COLOR)
    darkPalette.setColor(QPalette.Dark, QColor(30, 30, 30)) # 比Base更暗
    darkPalette.setColor(QPalette.Shadow, QColor(15, 15, 15))
    # 按钮颜色主要由QSS控制，但这里也设置一下以防QSS未完全覆盖
    darkPalette.setColor(QPalette.Button, ACCENT_COLOR)
    darkPalette.setColor(QPalette.ButtonText, TEXT_COLOR) # 通常按钮文字是白色或对比色
    darkPalette.setColor(QPalette.Disabled, QPalette.ButtonText, DISABLED_TEXT_COLOR)
    darkPalette.setColor(QPalette.BrightText, ACCENT_HOVER_COLOR) # 可以用作警告等亮色文本
    darkPalette.setColor(QPalette.Link, ACCENT_COLOR)
    darkPalette.setColor(QPalette.Highlight, ACCENT_COLOR)
    darkPalette.setColor(QPalette.Disabled, QPalette.Highlight, QColor(80, 80, 80))
    darkPalette.setColor(QPalette.HighlightedText, TEXT_COLOR) # 高亮文本通常是白色
    darkPalette.setColor(QPalette.Disabled, QPalette.HighlightedText, DISABLED_TEXT_COLOR)
    darkPalette.setColor(QPalette.PlaceholderText, DISABLED_TEXT_COLOR)
    return darkPalette

class FeedbackTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Return and event.modifiers() == Qt.ControlModifier:
            # 查找父 FeedbackUI 实例并调用提交方法
            parent = self.parent()
            while parent and not isinstance(parent, FeedbackUI):
                parent = parent.parent()
            if parent:
                parent._submit_feedback()
        else:
            super().keyPressEvent(event)

class FeedbackUI(QMainWindow):
    def __init__(self, prompt: str, predefined_options: Optional[List[str]] = None):
        super().__init__()
        self.prompt = prompt
        self.predefined_options = predefined_options or []

        self.feedback_result = None
        
        self.setWindowTitle("交互式反馈 MCP")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(script_dir, "images", "feedback.png")
        self.setWindowIcon(QIcon(icon_path))
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        
        self.settings = QSettings("InteractiveFeedbackMCP", "InteractiveFeedbackMCP")
        
        # 加载主窗口的通用UI设置 (几何形状, 状态)
        self.settings.beginGroup("MainWindow_General")
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(800, 600)
            screen = QApplication.primaryScreen().geometry()
            x = (screen.width() - 800) // 2
            y = (screen.height() - 600) // 2
            self.move(x, y)
        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)
        self.settings.endGroup() # "MainWindow_General" 分组结束

        self._create_ui()

    def _create_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(15, 15, 15, 15) # 增加主布局的外边距
        layout.setSpacing(20) # 增加主布局中控件的间距

        # 反馈区域
        self.feedback_group = QGroupBox("反馈")
        feedback_layout = QVBoxLayout(self.feedback_group)
        feedback_layout.setContentsMargins(15, 10, 15, 15) # 调整GroupBox内边距
        feedback_layout.setSpacing(15) # 增加GroupBox内控件间距

        # 描述标签 (来自 self.prompt) - 支持多行文本
        self.description_label = QLabel(self.prompt)
        self.description_label.setWordWrap(True)
        feedback_layout.addWidget(self.description_label)

        # 如果有预定义选项，则添加
        self.option_checkboxes = []
        if self.predefined_options and len(self.predefined_options) > 0:
            options_frame = QFrame()
            options_layout = QVBoxLayout(options_frame)
            options_layout.setContentsMargins(5, 10, 5, 10) # 选项区域的边距
            options_layout.setSpacing(10) # 选项之间的间距
            
            for option in self.predefined_options:
                checkbox = QCheckBox(option)
                self.option_checkboxes.append(checkbox)
                options_layout.addWidget(checkbox)
            
            feedback_layout.addWidget(options_frame)
            
            # 添加一个分隔线
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            separator.setFrameShadow(QFrame.Sunken)
            feedback_layout.addWidget(separator)

        # 自由格式文本反馈
        self.feedback_text = FeedbackTextEdit()
        self.feedback_text.setObjectName("feedback_text_edit") # 为QSS设置objectName
        font_metrics = self.feedback_text.fontMetrics()
        row_height = font_metrics.height()
        # 计算5行文本的高度 + 一些用于边距的填充 (5 是额外的垂直填充)
        padding = self.feedback_text.contentsMargins().top() + self.feedback_text.contentsMargins().bottom() + 5
        self.feedback_text.setMinimumHeight(5 * row_height + padding)

        self.feedback_text.setPlaceholderText("在此输入您的反馈 (Ctrl+Enter 提交)")
        submit_button = QPushButton("&发送反馈")
        submit_button.setObjectName("submit_button") # 为QSS设置objectName
        # 尝试添加图标 (需要一个合适的图标路径或使用QStyle的标准图标)
        # send_icon = QApplication.style().standardIcon(QStyle.SP_DialogApplyButton) # SP_MailSend
        # if not send_icon.isNull():
        #     submit_button.setIcon(send_icon)
        submit_button.clicked.connect(self._submit_feedback)


        feedback_layout.addWidget(self.feedback_text)
        feedback_layout.addWidget(submit_button)

        # 为 feedback_group 设置最小高度
        self.feedback_group.setMinimumHeight(self.description_label.sizeHint().height() + self.feedback_text.minimumHeight() + submit_button.sizeHint().height() + feedback_layout.spacing() * 2 + feedback_layout.contentsMargins().top() + feedback_layout.contentsMargins().bottom() + 10)

        # 添加控件
        layout.addWidget(self.feedback_group)

    def _submit_feedback(self):
        feedback_text = self.feedback_text.toPlainText().strip()
        selected_options = []
        
        # 如果有选中的预定义选项，则获取
        if self.option_checkboxes:
            for i, checkbox in enumerate(self.option_checkboxes):
                if checkbox.isChecked():
                    selected_options.append(self.predefined_options[i])
        
        # 合并选中的选项和反馈文本
        final_feedback_parts = []
        
        # 添加选中的选项
        if selected_options:
            final_feedback_parts.append("; ".join(selected_options))
        
        # 添加用户的文本反馈
        if feedback_text:
            final_feedback_parts.append(feedback_text)
            
        # 如果两部分都存在，则用换行符连接
        final_feedback = "\n\n".join(final_feedback_parts)
            
        self.feedback_result = FeedbackResult(
            interactive_feedback=final_feedback,
        )
        self.close()

    def closeEvent(self, event):
        # 保存主窗口的通用UI设置 (几何形状, 状态)
        self.settings.beginGroup("MainWindow_General")
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.settings.endGroup()

        super().closeEvent(event)

    def run(self) -> FeedbackResult:
        self.show()
        QApplication.instance().exec()

        if not self.feedback_result:
            return FeedbackResult(interactive_feedback="")

        return self.feedback_result

def feedback_ui(prompt: str, predefined_options: Optional[List[str]] = None, output_file: Optional[str] = None) -> Optional[FeedbackResult]:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv) # 确保传入sys.argv
    
    # 应用新的调色板和QSS
    app.setPalette(get_dark_mode_palette(app)) # 设置调色板
    app.setStyleSheet(MODERN_QSS) # 应用全局QSS
    app.setStyle("Fusion") # Fusion风格通常与自定义QSS配合良好

    ui = FeedbackUI(prompt, predefined_options)
    result = ui.run()

    if output_file and result:
        # 确保目录存在
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
        # 将结果保存到输出文件
        with open(output_file, "w") as f:
            json.dump(result, f)
        return None

    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="运行反馈用户界面")
    parser.add_argument("--prompt", default="我已实现您请求的更改。", help="要向用户显示的提示信息")
    parser.add_argument("--predefined-options", default="", help="管道符(|||)分隔的预定义选项列表")
    parser.add_argument("--output-file", help="将反馈结果保存为JSON的路径")
    args = parser.parse_args()

    predefined_options = [opt for opt in args.predefined_options.split("|||") if opt] if args.predefined_options else None
    
    result = feedback_ui(args.prompt, predefined_options, args.output_file)
    if result:
        print(f"\n已收到反馈:\n{result['interactive_feedback']}")
    sys.exit(0)
