import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ページ設定
st.set_page_config(page_title="麻雀対局管理システム", layout="wide")

# Googleスプレッドシートへの接続設定
# (Secretsに設定した情報を使用して接続)
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("🀄 麻雀対局管理システム")

# サイドメニュー
menu = st.sidebar.selectbox("メニュー", ["日程調整", "スコア登録", "ランキング表示"])

# ---------------------------------------------------------
# 1. 日程調整機能
# ---------------------------------------------------------
if menu == "日程調整":
    st.header("📅 日程調整登録")
    
    with st.form("schedule_form"):
        date = st.date_input("対局希望日")
        names = st.multiselect("参加可能メンバー", ["山田", "田中", "佐藤", "鈴木", "高橋"])
        memo = st.text_area("備考")
        submit = st.form_submit_button("登録する")
        
        if submit:
            # 既存データの取得
            df = conn.read(worksheet="schedule")
            # 新規データの追加
            new_data = pd.DataFrame([{"日付": str(date), "参加希望者名": ", ".join(names), "備考": memo}])
            updated_df = pd.concat([df, new_data], ignore_index=True)
            # スプレッドシートの更新
            conn.update(worksheet="schedule", data=updated_df)
            st.success("日程を登録しました！")

# ---------------------------------------------------------
# 2. スコア登録機能 (ウマ・オカ自動計算例)
# ---------------------------------------------------------
elif menu == "スコア登録":
    st.header("📝 対局スコア登録")
    
    with st.form("score_form"):
        date = st.date_input("対局日")
        col1, col2 = st.columns(2)
        
        # 簡易的な4人入力
        players = []
        points = []
        for i in range(4):
            p = st.selectbox(f"プレイヤー {i+1}", ["山田", "田中", "佐藤", "鈴木"], key=f"p{i}")
            pt = st.number_input(f"プレイヤー {i+1} の素点", value=25000, step=100, key=f"pt{i}")
            players.append(p)
            points.append(pt)
            
        memo = st.text_input("備考 (半荘何回目など)")
        submit = st.form_submit_button("スコアを計算・保存")

        if submit:
            # 合計点チェック (10万点)
            if sum(points) != 100000:
                st.error(f"合計点が {sum(points)} です。100,000点に調整してください。")
            else:
                # ここにウマ・オカのロジックを追加可能
                # 例: 30000返し、ウマ10-30など
                st.success("スコアを保存しました（計算ロジックはルールに合わせて調整してください）")

# ---------------------------------------------------------
# 3. ランキング表示
# ---------------------------------------------------------
elif menu == "ランキング表示":
    st.header("📊 通算成績ランキング")
    
    try:
        df_results = conn.read(worksheet="results")
        st.dataframe(df_results)
        
        # 可視化 (Plotly)
        if not df_results.empty:
            st.subheader("スコア推移")
            # ここに st.line_chart 等の可視化ロジック
    except Exception as e:
        st.info("データがまだありません。")