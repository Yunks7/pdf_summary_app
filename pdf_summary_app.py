import sys
import fitz  # PyMuPDF
import os
import openai
import google.generativeai as genai
from dotenv import load_dotenv
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, QTextEdit, QProgressBar, QComboBox
)
from PyQt6.QtCore import Qt

# 環境変数を読み込む
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# OpenAI / Gemini のどちらを使用するか選択可能
USE_GEMINI = False  # True にするとGeminiを使用

if USE_GEMINI:
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY is not set.")
        sys.exit(1)
    genai.configure(api_key=GEMINI_API_KEY)
else:
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY is not set.")
        sys.exit(1)
    openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

# モデル設定
GPT_MODEL = "gpt-4o-mini"  # OpenAI用
GEMINI_MODEL = "gemini-1.5-flash"  # Gemini用

class PDFSummaryApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("PDF Summary App")
        self.setGeometry(100, 100, 800, 600)
        self.setAcceptDrops(True)  # ドラッグ＆ドロップを有効化

        layout = QVBoxLayout()

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

        # モデル選択（OpenAI / Gemini）
        self.model_selector = QComboBox()
        self.model_selector.addItems(["OpenAI (GPT-4o-mini)", "Gemini (1.5-flash)"])
        self.model_selector.currentIndexChanged.connect(self.update_model)
        layout.addWidget(self.model_selector)

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
        self.use_gemini = USE_GEMINI  # 初期設定
        self.summary_text = ""  # 要約の内容を保持する

    def update_model(self, index):
        """ モデル選択を更新 """
        self.use_gemini = (index == 1)
        print(f"Using {'Gemini' if self.use_gemini else 'OpenAI'}")

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

            if self.use_gemini:
                response = self.call_gemini_api(prompt)
            else:
                response = self.call_openai_api(prompt)

            self.progress_bar.setValue(80)

            return response or "No summary generated."

        except Exception as e:
            return f"Error: {str(e)}"

    def call_openai_api(self, prompt):
        """ OpenAI APIを使用して要約を生成 """
        try:
            response = openai_client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert in summarizing academic papers."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1500
            )
            return response.choices[0].message.content.strip()
        except openai.OpenAIError as e:
            return f"OpenAI API Error: {str(e)}"

    def call_gemini_api(self, prompt):
        """ Gemini APIを使用して要約を生成 """
        try:
            model = genai.GenerativeModel(GEMINI_MODEL)
            response = model.generate_content(prompt)
            return response.text.strip() if response.text else "No response from Gemini."
        except Exception as e:
            return f"Gemini API Error: {str(e)}"
    
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFSummaryApp()
    window.show()
    sys.exit(app.exec())
