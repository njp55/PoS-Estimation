import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==========================================
# 1. セッションステートの初期化
# ==========================================
# 試行回数の初期化
if 'mc_trials' not in st.session_state:
    st.session_state.mc_trials = 10000

# モダリティ別ベースPoSの初期化
if 'base_pos' not in st.session_state:
    st.session_state.base_pos = pd.DataFrame({
        'Modality': ['Small Molecule', 'mAb', 'CAR-T', 'RNAi'],
        'Phase 1': [0.60, 0.70, 0.80, 0.65],
        'Phase 2': [0.30, 0.40, 0.50, 0.35],
        'Phase 3': [0.60, 0.70, 0.60, 0.65],
        'NDA': [0.90, 0.95, 0.85, 0.90]
    })

# プロジェクトリストの初期化
if 'projects' not in st.session_state:
    st.session_state.projects = []

# プロジェクト入力用のデフォルトパラメータ初期化関数
def reset_current_params():
    st.session_state.current_params = pd.DataFrame({
        'Apply': [False, False, False], # デフォルトはチェックなし
        'Parameter Name': ['バイオマーカー活用', '新規MoAの技術的ハードル', '自社創製品'],
        'Distribution': ['Normal', 'Triangular', 'Fixed'],
        'Value_Mean_Mode': [2.0, 0.8, 1.2],
        'Std_Min': [0.2, 0.5, None],
        'Max': [None, 1.0, None]
    })

if 'current_params' not in st.session_state:
    reset_current_params()

# ==========================================
# UI 構成とタブ設定
# ==========================================
st.set_page_config(page_title="臨床試験 PoS シミュレーター", layout="wide")
st.title("臨床試験 PoS シミュレーター (Enterprise Edition)")

tab1, tab2, tab3 = st.tabs(["⚙️ 初期設定", "📝 プロジェクト・マスター", "📊 実行 & ダッシュボード"])

# ==========================================
# タブ1: 初期設定 (Global Settings)
# ==========================================
with tab1:
    st.header("⚙️ システム全体の初期設定")
    
    st.subheader("シミュレーション基本設定")
    # モンテカルロ試行回数の動的設定
    st.session_state.mc_trials = st.number_input(
        "モンテカルロ試行回数 (例: クイック=1000, 精緻=100000)", 
        min_value=1000, max_value=1000000, value=st.session_state.mc_trials, step=1000
    )
    
    st.subheader("モダリティ別ベースPoSエディタ")
    st.markdown("ここで設定した値が各プロジェクトのベースライン（起点）となります。")
    st.session_state.base_pos = st.data_editor(st.session_state.base_pos, num_rows="dynamic", use_container_width=True)

# ==========================================
# タブ2: プロジェクト・マスター (Project Master)
# ==========================================
with tab2:
    st.header("📝 プロジェクト・マスター")
    
    with st.expander("新規プロジェクトの登録", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            proj_id = st.text_input("プロジェクトID", "PRJ-001")
            modality = st.selectbox("モダリティ", st.session_state.base_pos['Modality'].tolist())
        with col2:
            indication = st.text_input("対象疾患", "Oncology")
            current_phase = st.selectbox("現在のフェーズ", ["Phase 1", "Phase 2", "Phase 3", "NDA"])
        
        st.subheader("プロジェクト個別パラメータの設定")
        st.markdown("このプロジェクト固有のPoS変動要因を設定します。`Apply`にチェックを入れた項目のみが計算に適用されます。<br>行の追加・削除も自由に行えます。", unsafe_allow_html=True)
        
        # 分布をプルダウンで選択できる Data Editor
        edited_params = st.data_editor(
            st.session_state.current_params,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Apply": st.column_config.CheckboxColumn("適用", default=False),
                "Parameter Name": st.column_config.TextColumn("パラメータ名", required=True),
                "Distribution": st.column_config.SelectboxColumn(
                    "分布 (Distribution)",
                    help="確率分布の種類を選択してください",
                    options=["Fixed", "Normal", "Triangular", "Uniform"],
                    required=True
                ),
                "Value_Mean_Mode": st.column_config.NumberColumn("Value / Mean / Mode"),
                "Std_Min": st.column_config.NumberColumn("Std / Min"),
                "Max": st.column_config.NumberColumn("Max")
            },
            key="param_editor"
        )

        if st.button("プロジェクトを登録", type="primary"):
            # 適用にチェックが入っている行だけを抽出
            applied_params = edited_params[edited_params['Apply'] == True].copy()
            
            st.session_state.projects.append({
                "ID": proj_id,
                "Modality": modality,
                "Indication": indication,
                "Current Phase": current_phase,
                "Params": applied_params
            })
            st.success(f"プロジェクト {proj_id} を登録しました！")
            reset_current_params() # 入力フォームを初期状態にリセット
            st.rerun()

    st.subheader("セッションベースのパイプライン一覧")
    if st.session_state.projects:
        # プロジェクトのリストと削除ボタンの生成
        for idx, proj in enumerate(st.session_state.projects):
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 3, 1])
                c1.write(f"**{proj['ID']}**")
                c2.write(f"{proj['Modality']} / {proj['Indication']}")
                c3.write(f"{proj['Current Phase']}")
                c4.write(f"個別パラメータ数: {len(proj['Params'])}")
                # 削除機能の実装
                if c5.button("削除 🗑️", key=f"del_proj_{idx}"):
                    st.session_state.projects.pop(idx)
                    st.rerun()
                    
        # パラメータデータを除外したサマリー表示用データフレーム
        summary_df = pd.DataFrame([{k: v for k, v in p.items() if k != 'Params'} for p in st.session_state.projects])
        st.dataframe(summary_df, use_container_width=True)
    else:
        st.info("登録されたプロジェクトはありません。")

# ==========================================
# タブ3: 実行 & ダッシュボード (Execution & Dashboard)
# ==========================================
with tab3:
    st.header("📊 実行 & ダッシュボード")
    
    if st.button("🚀 シミュレーションを一斉起動", type="primary") and st.session_state.projects:
        trials = st.session_state.mc_trials
        results = []
        
        for proj in st.session_state.projects:
            # 1. ベースラインの取得
            base_rates = st.session_state.base_pos[st.session_state.base_pos['Modality'] == proj['Modality']].iloc[0]
            phases = ['Phase 1', 'Phase 2', 'Phase 3', 'NDA']
            base_overall_pos = np.prod([base_rates[p] for p in phases])
            
            # 2. 調整パラメータの分布サンプリング (個別パラメータ適用)
            modifiers = np.ones(trials)
            
            for _, param_row in proj['Params'].iterrows():
                dist = param_row['Distribution']
                # NaN対策 (値が入力されていない場合は安全なデフォルト値を使用)
                val_mean = param_row['Value_Mean_Mode'] if pd.notna(param_row['Value_Mean_Mode']) else 1.0
                std_min = param_row['Std_Min'] if pd.notna(param_row['Std_Min']) else 0.0
                v_max = param_row['Max'] if pd.notna(param_row['Max']) else 1.0
                
                if dist == 'Fixed':
                    sample = np.full(trials, val_mean)
                elif dist == 'Normal':
                    sample = np.random.normal(val_mean, std_min, trials)
                elif dist == 'Triangular':
                    sample = np.random.triangular(std_min, val_mean, v_max, trials)
                elif dist == 'Uniform':
                    sample = np.random.uniform(std_min, v_max, trials)
                else:
                    sample = np.ones(trials)
                
                modifiers *= sample  # 総合モディファイアの算出
            
            # 3. オッズ比を用いた確率の補正計算
            base_odds = base_overall_pos / (1 - base_overall_pos)
            adjusted_odds = base_odds * modifiers
            adjusted_pos_array = adjusted_odds / (1 + adjusted_odds)
            
            # 統計結果の集約
            median_pos = np.median(adjusted_pos_array)
            p5_pos = np.percentile(adjusted_pos_array, 5)
            p95_pos = np.percentile(adjusted_pos_array, 95)
            
            # 差分（Delta）の計算
            delta_pts = (median_pos - base_overall_pos) * 100
            
            # Phase3到達確率（Phase1×Phase2）
            p3_progression = base_rates['Phase 1'] * base_rates['Phase 2']
            
            results.append({
                "ID": proj["ID"],
                "Modality": proj["Modality"],
                "標準PoS (%)": base_overall_pos * 100,
                "調整後PoS 中央値 (%)": median_pos * 100,
                "悲観(5%) - 楽観(95%)": f"{p5_pos*100:.1f}% - {p95_pos*100:.1f}%",
                "Delta (pts)": delta_pts,
                "P3到達確率 (%)": p3_progression * 100,
                "base_rates": base_rates
            })
            
        # ==========================================
        # ポートフォリオ・サマリーと可視化
        # ==========================================
        res_df = pd.DataFrame(results)
        display_cols = ["ID", "Modality", "標準PoS (%)", "調整後PoS 中央値 (%)", "悲観(5%) - 楽観(95%)", "Delta (pts)", "P3到達確率 (%)"]
        
        st.subheader("ポートフォリオ・サマリー (標準 vs 調整後)")
        st.dataframe(res_df[display_cols].style.format({
            "標準PoS (%)": "{:.1f}",
            "調整後PoS 中央値 (%)": "{:.1f}",
            "Delta (pts)": "{:+.1f}",
            "P3到達確率 (%)": "{:.1f}"
        }), use_container_width=True)
        
        st.subheader("アトリション・ファンネル分析 (Attrition Funnel Chart)")
        
        # [バグ修正] key引数を追加して一意なIDを割り当てる
        for idx, row in res_df.iterrows():
            br = row['base_rates']
            surv_p1 = 100.0
            surv_p2 = surv_p1 * br['Phase 1']
            surv_p3 = surv_p2 * br['Phase 2']
            surv_nda = surv_p3 * br['Phase 3']
            surv_market = surv_nda * br['NDA']
            
            fig = go.Figure(go.Funnel(
                y = ["開始時", "Phase 1 通過", "Phase 2 通過", "Phase 3 通過", "NDA 承認"],
                x = [surv_p1, surv_p2, surv_p3, surv_nda, surv_market],
                textinfo = "value+percent initial"
            ))
            fig.update_layout(title=f"プロジェクト: {row['ID']} ({row['Modality']}) の標準ベースラインファンネル")
            
            # key引数にプロジェクトIDとインデックスを組み合わせた一意の文字列を渡す
            st.plotly_chart(fig, use_container_width=True, key=f"funnel_chart_{row['ID']}_{idx}")

    elif not st.session_state.projects:
        st.warning("タブ2でプロジェクトを登録してから実行してください。")
