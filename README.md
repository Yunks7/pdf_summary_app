# pdf_summary_app

【アプリ説明】
これは論文などのPDFデータからLLMモデルのAIのAPIを用いて、簡単な日本語の要約を作成するアプリです。

【使い方】
１．アプリがあるディレクトリ（同じフォルダ）に「.env」ファイルを作成し、中身を
      OPENAI_API_KEY=（ここにGPTのAPIキーを入力）
      GOOGLE_API_KEY=（ここにGeminiのAPIキーを入力）  
  とします。（APIキーはそれぞれのサイトに登録すると入手できます。）
２．アプリを起動します。
３．要約したいPDFファイルを参照/ドラッグアンドドロップし、中身が文字起こしされることを確認します。
４．使いたいAIサービスを選びます。（GPT 4o-mini　もしくは　Gemini 1.5-flash）
５．「Summarize PDF」ボタンを押し、プログレスバーが100%になるまで待ちます。
６．プログレスバーが100%になると、PDFの文字データが表示されていた部分に要約内容が記入されます。
７．出力をTXT形式で保存することが可能です。「Save as TXT」ボタンを押すと出力内容を保存できます。

【違うAIモデルを使いたい】
コードの中にある「＃モデル設定」以下の項目を書き換えてください。
2025/2/05現在利用できる主なものは以下のモデルです。
---GPT---
gpt-4o        :現状最高性能、お高い。
gpt-4-turbo   :まあまあな性能。
gpt-4o-mini   :普通の性能。安い。
gpt-3.5-turbo :性能は低め。安いけど4o-miniとそこまで変わらない。
---Gemini---
gemini-1.5-pro      :Gemini最高性能。お高い。
gemini-1.5-flash    :そこそこの性能。
gemini-1.0-flash-8B :精度は高くない。
(gemini-2.0-flash   :現在試験運用中のためアプリでは利用不可。1.5-proより高性能らしい。)

最終更新ver1.1
2025/2/5
