import sys
import fitz  # PyMuPDF
import os
import openai
import google.generativeai as genai
from dotenv import load_dotenv
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, QTextEdit, 
    QProgressBar, QComboBox, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QIcon

# 環境変数を読み込む
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# OpenAI クライアントの初期化
if OPENAI_API_KEY:
    openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

# **QSettings を使用してモデル設定を保存・復元**
settings = QSettings("MyCompany", "PDFSummaryApp")

# モデルリスト
GPT_MODELS = ["gpt-4o", "gpt-4-turbo", "gpt-4o-mini", "gpt-3.5-turbo"]
GEMINI_MODELS = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.5-flash-8B"]

class PDFSummaryApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_settings()  # **前回の設定をロード**

    def init_ui(self):
        self.setWindowTitle("PDF Summary App")
        self.setGeometry(100, 100, 800, 600)
        self.setAcceptDrops(True)  # ドラッグ＆ドロップを有効化

        layout = QVBoxLayout()
        
        # **AI選択ラジオボタン**
        self.radio_gpt = QRadioButton("GPT")
        self.radio_gemini = QRadioButton("Gemini")
        self.radio_gpt.setChecked(True)  # デフォルトはGPT
        self.radio_group = QButtonGroup(self)
        self.radio_group.addButton(self.radio_gpt)
        self.radio_group.addButton(self.radio_gemini)
        layout.addWidget(self.radio_gpt)
        layout.addWidget(self.radio_gemini)

        # **モデル選択（GPT / Gemini）**
        self.model_selector = QComboBox()
        self.update_model_list()  # 初期のモデルリストを設定
        layout.addWidget(self.model_selector)
        
        # **ラジオボタンとプルダウン変更時に設定を保存**
        self.radio_gpt.toggled.connect(self.update_model_list)
        self.radio_gemini.toggled.connect(self.update_model_list)
        self.radio_gpt.toggled.connect(self.save_settings)
        self.radio_gemini.toggled.connect(self.save_settings)
        self.model_selector.currentIndexChanged.connect(self.save_settings)

        # ラジオボタンの変更を監視
        self.radio_gpt.toggled.connect(self.update_model_list)
        self.radio_gemini.toggled.connect(self.update_model_list)

        # PDF選択ボタン
        self.btn_select_pdf = QPushButton("Select PDF File")
        self.btn_select_pdf.clicked.connect(self.select_pdf)
        layout.addWidget(self.btn_select_pdf)

        # ステータス表示
        self.label_status = QLabel("Status: select a pdf file or drag and drop it here")
        layout.addWidget(self.label_status)

        # プログレスバー
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # PDF内容表示エリア
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        layout.addWidget(self.text_area)

        # 要約ボタン
        self.btn_summarize = QPushButton("Summarize PDF")
        self.btn_summarize.setEnabled(False)
        self.btn_summarize.clicked.connect(self.summarize_pdf)
        layout.addWidget(self.btn_summarize)

        # TXT保存ボタン追加
        self.btn_save_txt = QPushButton("Save as TXT")
        self.btn_save_txt.setEnabled(False)
        self.btn_save_txt.clicked.connect(self.save_summary_as_txt)
        layout.addWidget(self.btn_save_txt)

        self.setLayout(layout)
        self.pdf_text = ""
        self.summary_text = ""

    def update_model_list(self):
        """ GPT か Gemini かによって選択可能なモデルを変更 """
        self.model_selector.clear()
        if self.radio_gpt.isChecked():
            self.model_selector.addItems(GPT_MODELS)
        else:
            self.model_selector.addItems(GEMINI_MODELS)
    
    def load_settings(self):
        """ QSettings から前回のモデル設定をロード """
        last_model = settings.value("selected_model", GPT_MODELS[0])
        last_ai = settings.value("selected_ai", "GPT")

        if last_ai == "GPT":
            self.radio_gpt.setChecked(True)
        else:
            self.radio_gemini.setChecked(True)

        # モデルを更新し、前回の選択をセット
        self.update_model_list()
        index = self.model_selector.findText(last_model)
        if index != -1:
            self.model_selector.setCurrentIndex(index)

    def save_settings(self):
        """ QSettings に現在のモデル設定を保存 """
        selected_model = self.model_selector.currentText()
        selected_ai = "GPT" if self.radio_gpt.isChecked() else "Gemini"
        settings.setValue("selected_model", selected_model)
        settings.setValue("selected_ai", selected_ai)

    def closeEvent(self, event):
        """ アプリ終了時に設定を保存 """
        self.save_settings()
        event.accept()

    def select_pdf(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Open PDF File", "", "PDF Files (*.pdf)")

        if file_path:
            self.load_pdf(file_path)

    def dragEnterEvent(self, event):
        """ ファイルがドロップされたときの処理 """
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """ ドロップされたファイルを処理 """
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith(".pdf"):  # PDFのみ許可
                self.load_pdf(file_path)
            else:
                self.label_status.setText("Status: Only PDF files are allowed.")

    def load_pdf(self, file_path):
        try:
            self.label_status.setText(f"Status: Loading {file_path}...")
            doc = fitz.open(file_path)
            self.pdf_text = "\n\n".join([page.get_text("text") for page in doc])

            if not self.pdf_text.strip():
                raise ValueError("PDF file is empty or cannot be read.")

            self.text_area.setText(self.pdf_text)
            self.label_status.setText("Status: PDF loaded. Ready to summarize.")
            self.btn_summarize.setEnabled(True)
        except Exception as e:
            self.label_status.setText("Status: Failed to load PDF")
            self.text_area.setText(f"Error: {str(e)}")
            self.btn_summarize.setEnabled(False)

    def summarize_pdf(self):
        if not self.pdf_text:
            return
        
        self.label_status.setText("Status: Processing summary...")
        self.progress_bar.setValue(30)

        self.summary_text = self.generate_summary(self.pdf_text)  # 要約を self.summary_text に格納

        if self.summary_text:
            self.text_area.setText(self.summary_text)
            self.label_status.setText("Status: Summary displayed")
            self.progress_bar.setValue(100)
            self.btn_save_txt.setEnabled(True)  # TXT保存ボタンを有効化
        else:
            self.label_status.setText("Status: Summary failed")
            self.progress_bar.setValue(0)


    def generate_summary(self, text):
        try:
            self.progress_bar.setValue(50)
            selected_model = self.model_selector.currentText()

            prompt = f"""
            Summarize the following academic paper in Japanese. The summary should include:
            - Abstract
            - Research background and objectives
            - Summary of figure and table captions
            - Conclusion

            Please keep the response concise.

            --- PAPER CONTENT ---
            {text}
            """

            if self.radio_gpt.isChecked():
                response = openai_client.chat.completions.create(
                    model=selected_model,
                    messages=[{"role": "system", "content": "You are an expert in summarizing academic papers."},
                              {"role": "user", "content": prompt}],
                    temperature=0.5,
                    max_tokens=1500
                )
                return response.choices[0].message.content.strip()
            else:
                model = genai.GenerativeModel(selected_model)
                response = model.generate_content(prompt)
                return response.text.strip() if response.text else "No response from Gemini."
            self.progress_bar.setValue(80)

            return response or "No summary generated."

        except Exception as e:
            return f"Error: {str(e)}"
    
    # 要約をTXTファイルに保存
    def save_summary_as_txt(self):
        if not self.summary_text:
            return
        
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(self, "Save Summary as TXT", "", "Text Files (*.txt)")

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.summary_text)
                self.label_status.setText("Status: summary saved as TXT")
            except Exception as e:
                self.label_status.setText(f"Status: save failed ({str(e)})")

def ico_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(ico_path('pdf_summary_app.ico')))
    window = PDFSummaryApp()
    window.show()
    sys.exit(app.exec())
