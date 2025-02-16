import pandas as pd
import io
import requests
import openai
import os
import streamlit as st
import datetime

# ページの基本設定（タブのタイトルを指定）
st.set_page_config(
    page_title="石川県観光客アンケートデータ分析",
    page_icon="icon.png"
)

# タイトルを設定
st.title("石川県観光客アンケートデータ分析アプリ")

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

# 「タイムスタンプ」列を datetime 型に変換
df["タイムスタンプ"] = pd.to_datetime(df["タイムスタンプ"])

# APIキーの取得
openai.api_key = st.secrets["OPENAI_API_KEY"]

with st.sidebar.header("分析対象期間"):
    st.write("分析対象期間を選択してください")

    # 最小・最大の日付を取得し、datetime.date 型に変換
    min_date = df["タイムスタンプ"].min().date()
    max_date = df["タイムスタンプ"].max().date()

    # デフォルト期間を min_date から max_date に設定
    default_start = min_date
    default_end = max_date
    
    # 日付範囲を選択するウィジェット
    start_date, end_date = st.date_input(
        "期間を選択",
        [default_start, default_end],  # デフォルト範囲
        min_value=min_date, 
        max_value=max_date
    )

# 選択した期間のデータを抽出
filtered_df = df[
    (df["タイムスタンプ"] >= pd.to_datetime(start_date)) &
    (df["タイムスタンプ"] < pd.to_datetime(end_date) + pd.Timedelta(days=1))
]

# 観光データの要約
def summarize_data(df):
    """
    観光データの傾向をOpenAI APIで要約する
    """
    if df.empty:
        return "該当するデータがありません。別の期間を選択してください。"

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

# 追加質問に応じた分析結果を返す関数
def analyze_additional_query(query, df):
    """
    ユーザーからの追加質問に応じた詳細分析をOpenAI APIで行う
    """
    prompt = f"""
    以下は観光アンケートデータに関する追加質問です。
    質問: {query}

    観光データの概要:
    {df.describe(include="all").to_string()}

    この質問に対して、詳しく具体的な回答を提供してください。
    """
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "あなたはデータ分析の専門家です。"},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

# 基本分析の実行
if st.button("基本分析を実行"):
    basic_summary = summarize_data(filtered_df)
    st.session_state.basic_summary = basic_summary  # セッション状態に保存

if "basic_summary" in st.session_state:
    st.write("【基本分析結果】")
    st.write(st.session_state.basic_summary)

# ここからチャット風の追加分析インターフェース
st.write("### 追加分析チャット")

# セッション状態にチャット履歴を保存する
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# チャットの入力フォーム（Ctrl+Enterで送信可能）
with st.form(key="chat_form"):
    user_query = st.text_area("追加で分析したい内容を入力してください", height=100)
    submitted = st.form_submit_button("送信")
    if submitted and user_query.strip() != "":
        # ユーザーの質問を履歴に追加
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        # 追加分析を実行
        assistant_response = analyze_additional_query(user_query, filtered_df)
        st.session_state.chat_history.append({"role": "assistant", "content": assistant_response})
        st.experimental_rerun()  # フォーム送信後に画面を更新

# チャット履歴の表示
if st.session_state.chat_history:
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(f"**あなた:** {msg['content']}")
        else:
            st.markdown(f"**アシスタント:** {msg['content']}")