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
#openai.api_key = os.environ["OPENAI_API_KEY"]

# サイドバー：分析対象期間の選択
st.sidebar.header("どの期間？")
min_date = df["タイムスタンプ"].min().date()
max_date = df["タイムスタンプ"].max().date()
default_start = min_date
default_end = max_date

dates = st.sidebar.date_input(
    "対象期間（デフォルト:全期間）",
    [default_start, default_end],
    min_value=min_date, 
    max_value=max_date
)
if isinstance(dates, (list, tuple)) and len(dates) == 2:
    start_date, end_date = dates
else:
    start_date = end_date = dates

# サイドバー：分析対象エリアの選択
st.sidebar.header("どこのエリア？")
area_options = ["金沢エリア", "加賀エリア", "能登エリア"]
selected_areas = st.sidebar.multiselect(
    "対象地域（デフォルト:全エリア）",
    options=area_options,
    default=area_options
)

# サイドバー：分析の視点（追加指示）の入力
st.sidebar.header("どんな観点で分析する？")
analysis_instruction = st.sidebar.text_input(
    "分析にあたっての特記事項があれば入力",
    "例: 首都圏の若年女性を中心に分析"
)

# フィルタリング処理
filtered_df = df[
    (df["タイムスタンプ"] >= pd.to_datetime(start_date)) &
    (df["タイムスタンプ"] < pd.to_datetime(end_date) + pd.Timedelta(days=1))
]
if selected_areas:
    filtered_df = filtered_df[filtered_df["エリア"].isin(selected_areas)]

# 観光データの要約（基本分析）関数
def summarize_data(df, instruction=""):
    """
    観光データの傾向をOpenAI APIで要約する。
    ユーザーが入力した分析の視点も組み込む。
    """
    if df.empty:
        return "該当するデータがありません。別の期間やエリアを選択してください。"

    # ユーザーからの追加指示がある場合、その内容をプロンプトに組み込む
    instruction_text = f"以下の視点で分析してください：{instruction}\n" if instruction.strip() != "" else ""

    prompt = f"""
    以下の観光アンケートデータを基に、観光客の傾向や特徴を要約してください。
    {instruction_text}
    - 居住地の分布
    - 観光目的の傾向
    - 満足度の傾向
    - 滞在時間や訪問回数の特徴

    データの概要：
    {df.describe(include="all").to_string()}

    詳しく分析し、簡潔に要約してください。
    """
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "あなたはデータ分析の専門家です。"},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

# 追加質問に応じた分析結果を返す関数（必要に応じて別途作成可能）
def analyze_additional_query(query, df):
    prompt = f"""
    以下は観光アンケートデータに関する追加質問です。
    質問: {query}

    データの概要：
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
    basic_summary = summarize_data(filtered_df, analysis_instruction)
    st.session_state.basic_summary = basic_summary

if "basic_summary" in st.session_state:
    st.write("【基本分析結果】")
    st.write(st.session_state.basic_summary)

# 追加分析チャットは基本分析が完了した場合のみ表示する
if "basic_summary" in st.session_state:
    st.write("### 追加分析チャット")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    with st.form(key="chat_form"):
        user_query = st.text_area("追加で分析したい内容を入力してください", height=100)
        submitted = st.form_submit_button("送信")
        if submitted and user_query.strip() != "":
            st.session_state.chat_history.append({"role": "user", "content": user_query})
            assistant_response = analyze_additional_query(user_query, filtered_df)
            st.session_state.chat_history.append({"role": "assistant", "content": assistant_response})
            st.rerun()
    if st.session_state.chat_history:
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(f"**あなた:** {msg['content']}")
            else:
                st.markdown(f"**アシスタント:** {msg['content']}")