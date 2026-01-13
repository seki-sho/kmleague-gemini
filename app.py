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
    st.header("📅 日程調整（丸三角バツ入力）")
    # メンバー情報をスプレッドシートから取得
    try:
        df_members = conn.read(worksheet="members")
        members = df_members["名前"].dropna().tolist()
        if not members:
            raise ValueError("メンバーが空です")
    except Exception as e:
        st.error(f"メンバー情報の取得に失敗しました: {e}")
        members = ["山田", "田中", "佐藤", "鈴木", "高橋"]  # 取得失敗時はデフォルト
    if not members:
        st.warning("メンバーが設定されていません。membersシートを確認してください。")
    else:
        # 期間選択
        start_date = st.date_input("開始日", pd.Timestamp.today())
        end_date = st.date_input("終了日", pd.Timestamp.today() + pd.Timedelta(days=14))
        date_range = pd.date_range(start_date, end_date)

        # 丸三角バツ選択用テーブル
        st.write("各メンバーごとに日付ごと参加可否を入力してください")
        status_options = {"◯": "参加可", "△": "調整可", "×": "不可"}
        input_data = []
        for member in members:
            st.subheader(f"{member} の予定入力")
            member_status = {}
            for date in date_range:
                status = st.selectbox(f"{date.strftime('%Y-%m-%d')}", ["◯", "△", "×"], key=f"{member}_{date}")
                member_status[str(date.date())] = status
            input_data.append({"name": member, "status": member_status})

        memo = st.text_area("備考")
        submit = st.button("予定を保存・組み合わせ抽出")

        if submit:
            # スプレッドシート保存（1人1行、日付ごとにステータス）
            df_existing = conn.read(worksheet="schedule")
            new_rows = []
            for member in input_data:
                for date, status in member["status"].items():
                    new_rows.append({"日付": date, "名前": member["name"], "ステータス": status, "備考": memo})
            df_new = pd.DataFrame(new_rows)
            df_updated = pd.concat([df_existing, df_new], ignore_index=True)
            conn.update(worksheet="schedule", data=df_updated)
            st.success("予定を保存しました！")

            # 組み合わせ抽出
            # 各日付ごとに「◯」が4人揃う日を抽出
            df_pivot = df_updated.pivot_table(index="日付", columns="名前", values="ステータス", aggfunc="last")
            possible_days = []
            for date, row in df_pivot.iterrows():
                if (row == "◯").sum() >= 4:
                    ok_members = [m for m in members if m in row.index and row[m] == "◯"]
                    possible_days.append({"日付": date, "参加メンバー": ", ".join(ok_members)})
            if possible_days:
                st.subheader("4人揃う候補日")
                st.table(pd.DataFrame(possible_days))
            else:
                st.info("4人揃う日程はありませんでした。")

# ---------------------------------------------------------
# 2. スコア登録機能 (ウマ・オカ自動計算例)
# ---------------------------------------------------------
elif menu == "スコア登録":
    st.header("📝 対局スコア登録")
    
    with st.form("score_form"):
        date = st.date_input("対局日")
        
        # 4名分の入力欄
        cols = st.columns(4)
        player_data = []
        for i, col in enumerate(cols):
            with col:
                p_name = st.selectbox(f"プレイヤー {i+1}", ["山田", "田中", "佐藤", "鈴木", "高橋"], key=f"p{i}")
                p_point = st.number_input(f"素点 {i+1}", value=25000, step=100, key=f"pt{i}")
                player_data.append({"name": p_name, "point": p_point})
        
        memo = st.text_input("備考 (例: 半荘1回目)")
        submit = st.form_submit_button("計算して保存")

        if submit:
            # 1. 合計点チェック (25000*4=100,000点)
            total_points = sum(p["point"] for p in player_data)
            if total_points != 100000:
                st.error(f"合計点が {total_points} です。100,000点になるよう調整してください。")
                st.stop()

            # 2. 順位の決定 (同点時の処理は簡略化)
            # 素点の高い順にソート
            sorted_players = sorted(player_data, key=lambda x: x["point"], reverse=True)
            
            # 3. スコア計算 (30,000点返し / ウマ 10-30 / オカ +20)
            uma_list = [30, 10, -10, -30]
            final_results = {}
            
            for i, p in enumerate(sorted_players):
                # 基本スコア (素点 - 30,000) / 1000
                base_score = (p["point"] - 30000) / 1000
                # ウマ
                uma = uma_list[i]
                # オカ (1位のみ +20)
                oka = 20 if i == 0 else 0
                
                final_results[p["name"]] = round(base_score + uma + oka, 1)

            # 4. スプレッドシート保存用のデータ作成
            # resultsシートの列: 日付, プレイヤーA, スコアA, プレイヤーB, スコアB...
            new_row = {
                "日付": str(date),
                "プレイヤーA": sorted_players[0]["name"], "スコアA": final_results[sorted_players[0]["name"]],
                "プレイヤーB": sorted_players[1]["name"], "スコアB": final_results[sorted_players[1]["name"]],
                "プレイヤーC": sorted_players[2]["name"], "スコアC": final_results[sorted_players[2]["name"]],
                "プレイヤーD": sorted_players[3]["name"], "スコアD": final_results[sorted_players[3]["name"]],
                "備考": memo
            }
            
            # スプレッドシート更新
            try:
                df_existing = conn.read(worksheet="results")
                df_updated = pd.concat([df_existing, pd.DataFrame([new_row])], ignore_index=True)
                conn.update(worksheet="results", data=df_updated)
                st.success("計算完了！スプレッドシートに保存しました。")
                st.table(pd.DataFrame([final_results])) # 計算結果をプレビュー
            except Exception as e:
                st.error(f"保存に失敗しました: {e}")

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