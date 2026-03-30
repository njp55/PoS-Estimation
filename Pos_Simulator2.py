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

# 変動パラメータ・マスターの初期化 
if 'parameters' not in st.session_state:
    st.session_state.parameters = pd.DataFrame({
        'Parameter Name': ['バイオマーカー活用', '新規MoAの技術的ハードル', '自社創製品'],
        'Distribution': ['Normal', 'Triangular', 'Fixed'],
        'Value_Mean_Mode': [2.0, 0.8, 1.2],
        'Std_Min': [0.2, 0.5, np.nan],
        'Max': [np.nan, 1.0, np.nan]
    })

# プロジェクトリストの初期化 
if 'projects' not in st.session_state:
    st.session_state.projects = []


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
    # DataFrameを直接編集可能にするUI 
    st.session_state.base_pos = st.data_editor(st.session_state.base_pos, num_rows="dynamic", use_container_width=True)
    
    st.subheader("PoS変動パラメータ・マスター管理")
    st.markdown("分布の種類: `Fixed`(固定), `Normal`(正規分布: Mean, Std), `Triangular`(三角分布: Mode, Min, Max), `Uniform`(一様分布: Min, Max) [cite: 1, 2]")
    st.session_state.parameters = st.data_editor(st.session_state.parameters, num_rows="dynamic", use_container_width=True)

# ==========================================
# タブ2: プロジェクト・マスター (Project Master)
# ==========================================
with tab2:
    st.header("📝 プロジェクト・マスター")
    
    with st.expander("新規プロジェクトの登録", expanded=True):
        with st.form("project_form"):
            col1, col2 = st.columns(2)
            # 基本情報の入力 
            with col1:
                proj_id = st.text_input("プロジェクトID", "PRJ-001")
                modality = st.selectbox("モダリティ", st.session_state.base_pos['Modality'].tolist())
            with col2:
                indication = st.text_input("対象疾患", "Oncology")
                current_phase = st.selectbox("現在のフェーズ", ["Phase 1", "Phase 2", "Phase 3", "NDA"])
            
            st.subheader("共通パラメータの適用状況 (Dynamic Form)")
            st.markdown("このプロジェクトに該当するパラメータにチェックを入れてください。")
            
            applied_params = {}
            for idx, row in st.session_state.parameters.iterrows():
                param_name = row['Parameter Name']
                is_applied = st.checkbox(f"{param_name} を適用する", value=False)
                if is_applied:
                    applied_params[param_name] = True

            submitted = st.form_submit_button("プロジェクトを登録")
            if submitted:
                st.session_state.projects.append({
                    "ID": proj_id,
                    "Modality": modality,
                    "Indication": indication,
                    "Current Phase": current_phase,
                    "Applied Params": applied_params
                })
                st.success(f"プロジェクト {proj_id} を登録しました！")

    st.subheader("セッションベースのパイプライン一覧")
    # セッションメモリ上での安全な管理 
    if st.session_state.projects:
        st.dataframe(pd.DataFrame(st.session_state.projects), use_container_width=True)
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
            
            # 2. 調整パラメータの分布サンプリング (Monte Carlo Sampling) 
            modifiers = np.ones(trials)
            
            for param_name in proj['Applied Params'].keys():
                param_row = st.session_state.parameters[st.session_state.parameters['Parameter Name'] == param_name].iloc[0]
                dist = param_row['Distribution']
                val_mean = param_row['Value_Mean_Mode']
                std_min = param_row['Std_Min']
                v_max = param_row['Max']
                
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
            # ベースオッズ計算
            base_odds = base_overall_pos / (1 - base_overall_pos)
            
            # 調整後オッズの計算 [cite: 3]
            adjusted_odds = base_odds * modifiers
            
            # 確率への再変換 [cite: 3]
            adjusted_pos_array = adjusted_odds / (1 + adjusted_odds)
            
            # 統計結果の集約 [cite: 3]
            median_pos = np.median(adjusted_pos_array)
            p5_pos = np.percentile(adjusted_pos_array, 5)   # 悲観的シナリオ
            p95_pos = np.percentile(adjusted_pos_array, 95) # 楽観的シナリオ
            
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
                "base_rates": base_rates # チャート用
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
        st.markdown("各フェーズの生存率（脱落せずに次のフェーズへ進む確率）を視覚化します。")
        
        # Plotlyを使ったインタラクティブな漏斗図 
        for idx, row in res_df.iterrows():
            br = row['base_rates']
            # 生存率の累積計算
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
            st.plotly_chart(fig, use_container_width=True)

    elif not st.session_state.projects:
        st.warning("タブ2でプロジェクトを登録してから実行してください。")