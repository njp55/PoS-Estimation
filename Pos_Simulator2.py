import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import io

# ==========================================
# 1. セッションステートの初期化
# ==========================================
if 'mc_trials' not in st.session_state:
    st.session_state.mc_trials = 10000

if 'base_pos' not in st.session_state:
    st.session_state.base_pos = pd.DataFrame({
        'Modality': ['Small Molecule', 'mAb', 'CAR-T', 'RNAi'],
        'Phase 1': [0.60, 0.70, 0.80, 0.65],
        'Phase 2': [0.30, 0.40, 0.50, 0.35],
        'Phase 3': [0.60, 0.70, 0.60, 0.65],
        'NDA': [0.90, 0.95, 0.85, 0.90]
    })

if 'projects' not in st.session_state:
    st.session_state.projects = []

def reset_current_params():
    # 評価項目ごとに適した確率分布とデフォルト値を設定
    st.session_state.current_params = pd.DataFrame({
        'Apply': [False] * 15,
        'Parameter Name': [
            "作用機序 (MoA) の明確性", "標的の性質 (Host vs Non-host)", "薬理作用 (刺激剤 vs 拮抗剤)",
            "組織曝露選択性 (STR/STAR)", "分子の物理化学的性質", "標的結合タンパク質数",
            "バイオマーカーの活用", "オンコロジー領域の効果", "代替エンドポイント相関",
            "疾患領域 (TA)", "モダリティ (創薬技術)", "臨床・免疫学的指標",
            "創薬の新規性 (FiC vs Me-too)", "導入経緯 (Licensed-in)", "リード適応症 (Lead indication)"
        ],
        'Distribution': [
            'Normal', 'Fixed', 'Normal', 
            'Triangular', 'Uniform', 'Fixed',
            'Normal', 'Normal', 'Triangular',
            'Fixed', 'Fixed', 'Normal',
            'Triangular', 'Fixed', 'Fixed'
        ],
        'Value_Mean_Mode': [1.2, 1.3, 1.1, 1.2, np.nan, 0.9, 2.1, 4.0, 0.8, 1.0, 1.0, 1.1, 0.76, 1.2, 1.0],
        'Std_Min': [0.1, np.nan, 0.2, 0.8, 0.8, np.nan, 0.5, 1.0, 0.5, np.nan, np.nan, 0.2, 0.5, np.nan, np.nan],
        'Max': [np.nan, np.nan, np.nan, 1.5, 1.2, np.nan, np.nan, np.nan, 1.0, np.nan, np.nan, np.nan, 1.0, np.nan, np.nan]
    })

if 'current_params' not in st.session_state:
    reset_current_params()

# ==========================================
# Excel エクスポート用関数
# ==========================================
def generate_excel_template():
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # 1. Base PoS
        st.session_state.base_pos.to_excel(writer, sheet_name='Base_PoS', index=False)
        # 2. Parameters
        st.session_state.current_params.to_excel(writer, sheet_name='Parameters', index=False)
        # 3. Projects (CSV/Excel互換用)
        proj_export = []
        for p in st.session_state.projects:
            params_str = ",".join(p['Params']['Parameter Name'].tolist()) if not p['Params'].empty else ""
            proj_export.append({
                "ID": p["ID"],
                "Modality": p["Modality"],
                "Indication": p["Indication"],
                "Current Phase": p["Current Phase"],
                "Applied_Params": params_str
            })
        pd.DataFrame(proj_export, columns=["ID", "Modality", "Indication", "Current Phase", "Applied_Params"]).to_excel(writer, sheet_name='Projects', index=False)
    return output.getvalue()

# ==========================================
# UI 構成とタブ設定
# ==========================================
st.set_page_config(page_title="臨床試験 PoS シミュレーター", layout="wide")
st.title("臨床試験 PoS シミュレーター (Enterprise Edition)")

tab1, tab2, tab3 = st.tabs(["⚙️ 初期設定 & I/O", "📝 プロジェクト・マスター", "📊 実行 & ダッシュボード"])

# ==========================================
# タブ1: 初期設定 (Global Settings & I/O)
# ==========================================
with tab1:
    st.header("⚙️ システム設定とデータ入出力")
    
    # データ入出力セクション (Excelベース)
    with st.expander("📥 データのインポート / 📤 エクスポート", expanded=True):
        st.markdown("設定した「ベースPoS」「パラメータ」「プロジェクト一覧」をExcelファイルとしてダウンロードしたり、アップロードして一括復元できます。（CSVデータのやり取りもこのExcel内のProjectsシートで完結します）")
        
        # エクスポート
        excel_data = generate_excel_template()
        st.download_button(
            label="テンプレート（現在の状態）をダウンロード 📥",
            data=excel_data,
            file_name="PoS_Simulator_Template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        # インポート
        uploaded_file = st.file_uploader("設定・パイプラインのインポート (Excel)", type=["xlsx"])
        if uploaded_file is not None:
            if st.button("インポートを実行", type="primary"):
                try:
                    xls = pd.ExcelFile(uploaded_file)
                    if 'Base_PoS' in xls.sheet_names:
                        st.session_state.base_pos = pd.read_excel(xls, 'Base_PoS')
                    if 'Parameters' in xls.sheet_names:
                        st.session_state.current_params = pd.read_excel(xls, 'Parameters')
                    if 'Projects' in xls.sheet_names:
                        proj_df = pd.read_excel(xls, 'Projects')
                        new_projects = []
                        for _, row in proj_df.iterrows():
                            # Applied_Params列からパラメータ情報を復元
                            applied_params = pd.DataFrame(columns=st.session_state.current_params.columns)
                            if pd.notna(row.get('Applied_Params', '')):
                                param_names = [x.strip() for x in str(row['Applied_Params']).split(',') if x.strip()]
                                applied_params = st.session_state.current_params[st.session_state.current_params['Parameter Name'].isin(param_names)]
                                applied_params['Apply'] = True
                            
                            new_projects.append({
                                "ID": row["ID"],
                                "Modality": row["Modality"],
                                "Indication": row["Indication"],
                                "Current Phase": row["Current Phase"],
                                "Params": applied_params
                            })
                        st.session_state.projects = new_projects
                    st.success("インポートが完了しました！")
                    st.rerun()
                except Exception as e:
                    st.error(f"読み込みエラー: {e}")

    st.subheader("シミュレーション基本設定")
    st.session_state.mc_trials = st.number_input(
        "モンテカルロ試行回数 (例: クイック=1000, 精緻=100000)", 
        min_value=1000, max_value=1000000, value=st.session_state.mc_trials, step=1000
    )
    
    st.subheader("モダリティ別ベースPoSエディタ")
    st.session_state.base_pos = st.data_editor(st.session_state.base_pos, num_rows="dynamic", use_container_width=True)

# ==========================================
# タブ2: プロジェクト・マスター (Project Master)
# ==========================================
with tab2:
    st.header("📝 プロジェクト・マスター")
    
    with st.expander("新規プロジェクトの登録", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            proj_id = st.text_input("プロジェクトID", f"PRJ-{len(st.session_state.projects)+1:03d}")
            modality = st.selectbox("モダリティ", st.session_state.base_pos['Modality'].tolist())
        with col2:
            indication = st.text_input("対象疾患", "Oncology")
            current_phase = st.selectbox("現在のフェーズ", ["Phase 1", "Phase 2", "Phase 3", "NDA"])
        
        st.subheader("プロジェクト個別パラメータの設定")
        st.markdown("このプロジェクト固有のPoS変動要因を設定します。`Apply`にチェックを入れた項目のみが計算に適用されます。")
        
        edited_params = st.data_editor(
            st.session_state.current_params,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Apply": st.column_config.CheckboxColumn("適用", default=False),
                "Parameter Name": st.column_config.TextColumn("パラメータ名", required=True),
                "Distribution": st.column_config.SelectboxColumn("分布", options=["Fixed", "Normal", "Triangular", "Uniform"], required=True),
                "Value_Mean_Mode": st.column_config.NumberColumn("Value / Mean / Mode"),
                "Std_Min": st.column_config.NumberColumn("Std / Min"),
                "Max": st.column_config.NumberColumn("Max")
            },
            key="param_editor"
        )

        if st.button("プロジェクトを登録", type="primary"):
            applied_params = edited_params[edited_params['Apply'] == True].copy()
            st.session_state.projects.append({
                "ID": proj_id,
                "Modality": modality,
                "Indication": indication,
                "Current Phase": current_phase,
                "Params": applied_params
            })
            st.success(f"プロジェクト {proj_id} を登録しました！")
            st.rerun()

    st.subheader("セッションベースのパイプライン一覧")
    if st.session_state.projects:
        # パイプライン一覧表示用のデータ作成（適用パラメータの文字列化を含む）
        summary_data = []
        for p in st.session_state.projects:
            # 適用されたパラメータ名を取り出してカンマ区切りにする
            applied_p_names = ", ".join(p['Params']['Parameter Name'].tolist()) if not p['Params'].empty else "適用なし"
            summary_data.append({
                "ID": p["ID"],
                "Modality": p["Modality"],
                "対象疾患": p["Indication"],
                "現在のフェーズ": p["Current Phase"],
                "適用パラメータ": applied_p_names
            })
            
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
        
        # 削除用UI
        st.markdown("#### プロジェクトの削除")
        cols = st.columns(min(len(st.session_state.projects), 5))
        for idx, proj in enumerate(st.session_state.projects):
            col_idx = idx % 5
            if cols[col_idx].button(f"🗑️ {proj['ID']} 削除", key=f"del_proj_{idx}"):
                st.session_state.projects.pop(idx)
                st.rerun()
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
        phase_order = ['Phase 1', 'Phase 2', 'Phase 3', 'NDA']
        
        for proj in st.session_state.projects:
            # ベースラインの取得と、完了済みフェーズの補正
            base_rates = st.session_state.base_pos[st.session_state.base_pos['Modality'] == proj['Modality']].iloc[0].copy()
            current_phase_idx = phase_order.index(proj['Current Phase'])
            for i in range(current_phase_idx):
                base_rates[phase_order[i]] = 1.0
            base_overall_pos = np.prod([base_rates[p] for p in phase_order])
            
            # 調整パラメータの分布サンプリング
            modifiers = np.ones(trials)
            for _, param_row in proj['Params'].iterrows():
                dist = param_row['Distribution']
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
                modifiers *= sample
            
            # オッズ比を用いた確率の補正計算
            if base_overall_pos == 1.0:
                adjusted_pos_array = np.ones(trials)
            else:
                base_odds = base_overall_pos / (1 - base_overall_pos)
                adjusted_odds = base_odds * modifiers
                adjusted_pos_array = adjusted_odds / (1 + adjusted_odds)
            
            # 統計結果の集約
            median_pos = np.median(adjusted_pos_array)
            p5_pos = np.percentile(adjusted_pos_array, 5)
            p95_pos = np.percentile(adjusted_pos_array, 95)
            
            delta_pts = (median_pos - base_overall_pos) * 100
            p3_progression = 1.0 if current_phase_idx >= 2 else base_rates['Phase 1'] * base_rates['Phase 2']
            
            results.append({
                "ID": proj["ID"],
                "Modality": proj["Modality"],
                "現在のPhase": proj["Current Phase"],
                "標準PoS (%)": base_overall_pos * 100,
                "調整後PoS 中央値 (%)": median_pos * 100,
                "悲観(5%) - 楽観(95%)": f"{p5_pos*100:.1f}% - {p95_pos*100:.1f}%",
                "Delta (pts)": delta_pts,
                "P3到達確率 (%)": p3_progression * 100,
                "eff_base_rates": base_rates
            })
            
        # 可視化
        res_df = pd.DataFrame(results)
        display_cols = ["ID", "Modality", "現在のPhase", "標準PoS (%)", "調整後PoS 中央値 (%)", "悲観(5%) - 楽観(95%)", "Delta (pts)", "P3到達確率 (%)"]
        
        st.subheader("ポートフォリオ・サマリー (標準 vs 調整後)")
        st.markdown("※「標準PoS」および「P3到達確率」は、現在のフェーズより前の生存率を100%として算出されています。")
        st.dataframe(res_df[display_cols].style.format({
            "標準PoS (%)": "{:.1f}",
            "調整後PoS 中央値 (%)": "{:.1f}",
            "Delta (pts)": "{:+.1f}",
            "P3到達確率 (%)": "{:.1f}"
        }), use_container_width=True)
        
        st.subheader("アトリション・ファンネル分析 (Attrition Funnel Chart)")
        for idx, row in res_df.iterrows():
            br = row['eff_base_rates']
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
            fig.update_layout(title=f"プロジェクト: {row['ID']} ({row['Modality']}) / 開始: {row['現在のPhase']}")
            st.plotly_chart(fig, use_container_width=True, key=f"funnel_chart_{row['ID']}_{idx}")

    elif not st.session_state.projects:
        st.warning("タブ2でプロジェクトを登録してから実行してください。")
