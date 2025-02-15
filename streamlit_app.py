import pandas as pd
import io
import requests
import openai
import os
import streamlit as st


# スプレッドシートの共有URL（閲覧権限があることを確認）
SHEET_URL = "https://docs.google.com/spreadsheets/d/1riK_ufkmF6Ql7Tujwlm22FtHOLz7hwUzf6Zi6JAG_QI/edit?usp=sharing"

# スプレッドシートIDをURLから抽出
SHEET_ID = SHEET_URL.split('/d/')[1].split('/edit')[0]

# CSVとしてダウンロードするためのURLを作成
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

# CSVデータをダウンロード
response = requests.get(CSV_URL)
response.raise_for_status()  # エラーが発生した場合、例外を発生させる

# ダウンロードしたCSVデータをpandas DataFrameに読み込む
# UTF-8エンコーディングを指定
df = pd.read_csv(io.StringIO(response.content.decode('utf-8')))

# APIキーの取得
openai.api_key = os.getenv("OPENAI_API_KEY")

def summarize_data(df):
    """
    観光データの傾向をOpenAI APIで要約する
    """
    prompt = f"""
    以下の観光アンケートデータを基に、観光客の傾向や特徴を要約してください。
    - 居住地の分布
    - 観光目的の傾向
    - 満足度の傾向
    - 滞在時間や訪問回数の特徴

    データの概要：
    {df.describe(include="all").to_string()}

    詳しく分析し、簡潔に要約してください。
    """

    # openai.ChatCompletion.create を openai.chat.completions.create に変更
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "あなたはデータ分析の専門家です。"},
                  {"role": "user", "content": prompt}]
    )

    # response["choices"][0]["message"]["content"] を response.choices[0].message.content に変更
    # ChatCompletion オブジェクトの属性にアクセスするように修正
    return response.choices[0].message.content

# 傾向を要約
summary = summarize_data(df)

st.write(summary)