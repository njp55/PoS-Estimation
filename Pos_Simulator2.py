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
        st.session_state.base_pos.to_excel(writer, sheet_name='Base_PoS', index=False)
        st.session_state.current_params.to_excel(writer, sheet_name='Global_Parameters', index=False)
        
        proj_export = []
        proj_params_export = []
        
        for p in st.session_state.projects:
            # プロジェクトのパラメータ名をカンマ区切りで取得
            applied_params_str = ",".join(p['Params']['Parameter Name'].tolist()) if not p['Params'].empty else ""
            
            proj_export.append({
                "ID": p["ID"],
                "Modality": p["Modality"],
                "Indication": p["Indication"],
                "Current Phase": p["Current Phase"],
                "Applied_Params": applied_params_str
            })
            
            if not p['Params'].empty:
                for _, r in p['Params'].iterrows():
                    proj_params_export.append({
                        "Project_ID": p["ID"],
                        "Parameter Name": r["Parameter Name"],
                        "Distribution": r["Distribution"],
                        "Value_Mean_Mode": r["Value_Mean_Mode"],
                        "Std_Min": r["Std_Min"],
                        "Max": r["Max"]
                    })
        
        pd.DataFrame(proj_export, columns=["ID", "Modality", "Indication", "Current Phase", "Applied_Params"]).to_excel(writer, sheet_name='Projects', index=False)
        
        if proj_params_export:
            pd.DataFrame(proj_params_export).to_excel(writer, sheet_name='Project_Parameters', index=False)
        else:
            pd.DataFrame(columns=["Project_ID", "Parameter Name", "Distribution", "Value_Mean_Mode", "Std_Min", "Max"]).to_excel(writer, sheet_name='Project_Parameters', index=False)
            
    return output.getvalue()

# ==========================================
# UI 構成とタブ設定
# ==========================================
st.set_page_config(page_title="臨床試験 PoS シミュレーター", layout="wide")
st.title("臨床試験 PoS シミュレーター (Enterprise Edition)")

tab1, tab2, tab3 = st.tabs(["⚙️ 初期設定 & I/O", "📝 プロジェクト・マスター", "📊 実行 & ダッシュボード"])

with tab1:
    st.header("⚙️ システム設定とデータ入出力")
    with st.expander("📥 データのインポート / 📤 エクスポート", expanded=True):
        st.markdown("""
        現在の設定とプロジェクトをExcelで入出力できます。  
        **【ヒント】** プロジェクトの登録時、`Projects`シートの `Applied_Params` 列にカンマ区切りでパラメータ名（例: `バイオマーカーの活用, オンコロジー領域の効果`）を入力してインポートするだけで、グローバル設定のデフォルト値を自動適用できます。
        """)
        
        excel_data = generate_excel_template()
        st.download_button(
            label="テンプレート（現在のパイプライン一覧を含む）をダウンロード 📥",
            data=excel_data,
            file_name="PoS_Simulator_Template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        uploaded_file = st.file_uploader("設定・パイプラインのインポート (Excel)", type=["xlsx"])
        if uploaded_file is not None:
            if st.button("インポートを実行", type="primary"):
                try:
                    xls = pd.ExcelFile(uploaded_file)
                    if 'Base_PoS' in xls.sheet_names:
                        st.session_state.base_pos = pd.read_excel(xls, 'Base_PoS')
                    
                    if 'Global_Parameters' in xls.sheet_names:
                        st.session_state.current_params = pd.read_excel(xls, 'Global_Parameters')
                    elif 'Parameters' in xls.sheet_names: 
                        st.session_state.current_params = pd.read_excel(xls, 'Parameters')
                        
                    if 'Projects' in xls.sheet_names:
                        proj_df = pd.read_excel(xls, 'Projects')
                        proj_params_df = pd.read_excel(xls, 'Project_Parameters') if 'Project_Parameters' in xls.sheet_names else pd.DataFrame()
                            
                        new_projects = []
                        for _, row in proj_df.iterrows():
                            my_params = pd.DataFrame(columns=st.session_state.current_params.columns)
                            
                            # 1. まず Project_Parameters シートに詳細な個別設定があれば、それを優先して読み込む
                            if not proj_params_df.empty and 'Project_ID' in proj_params_df.columns:
                                specific_params = proj_params_df[proj_params_df['Project_ID'] == row['ID']].copy()
                                if not specific_params.empty:
                                    my_params = specific_params
                                    my_params['Apply'] = True
                                    my_params = my_params.drop(columns=['Project_ID'])
                            
                            # 2. 個別設定がなく、Projects シートの Applied_Params 列に記載がある場合は、グローバル設定のデフォルト値を適用する
                            if my_params.empty and 'Applied_Params' in row and pd.notna(row['Applied_Params']):
                                param_names = [x.strip() for x in str(row['Applied_Params']).split(',') if x.strip()]
                                if param_names:
                                    # グローバル設定（current_params）から該当するパラメータの行を抽出
                                    my_params = st.session_state.current_params[st.session_state.current_params['Parameter Name'].isin(param_names)].copy()
                                    my_params['Apply'] = True

                            new_projects.append({
                                "ID": row["ID"],
                                "Modality": row["Modality"],
                                "Indication": row["Indication"],
                                "Current Phase": row["Current Phase"],
                                "Params": my_params
                            })
                        st.session_state.projects = new_projects
                    st.success("パイプラインとパラメータのインポートが完了しました！")
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
        summary_data = []
        for p in st.session_state.projects:
            applied_p_names = ", ".join(p['Params']['Parameter Name'].tolist()) if not p['Params'].empty else "適用なし"
            summary_data.append({
                "ID": p["ID"],
                "Modality": p["Modality"],
                "対象疾患": p["Indication"],
                "現在のフェーズ": p["Current Phase"],
                "適用パラメータ": applied_p_names
            })
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
        
        st.markdown("#### プロジェクトの削除")
        cols = st.columns(min(len(st.session_state.projects), 5))
        for idx, proj in enumerate(st.session_state.projects):
            col_idx = idx % 5
            if cols[col_idx].button(f"🗑️ {proj['ID']} 削除", key=f"del_proj_{idx}"):
                st.session_state.projects.pop(idx)
                st.rerun()
    else:
        st.info("登録されたプロジェクトはありません。")

with tab3:
    st.header("📊 実行 & ダッシュボード")
    
    if st.button("🚀 シミュレーションを一斉起動", type="primary") and st.session_state.projects:
        trials = st.session_state.mc_trials
        results = []
        phase_order = ['Phase 1', 'Phase 2', 'Phase 3', 'NDA']
        
        for proj in st.session_state.projects:
            base_rates = st.session_state.base_pos[st.session_state.base_pos['Modality'] == proj['Modality']].iloc[0].copy()
            current_phase_idx = phase_order.index(proj['Current Phase'])
            for i in range(current_phase_idx):
                base_rates[phase_order[i]] = 1.0
            base_overall_pos = np.prod([base_rates[p] for p in phase_order])
            
            param_samples = {}
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
                
                if dist != 'Fixed':
                    param_samples[param_row['Parameter Name']] = sample
            
            if base_overall_pos == 1.0:
                adjusted_pos_array = np.ones(trials)
            else:
                base_odds = base_overall_pos / (1 - base_overall_pos)
                adjusted_odds = base_odds * modifiers
                adjusted_pos_array = adjusted_odds / (1 + adjusted_odds)
            
            sensitivities = {}
            if np.std(adjusted_pos_array) > 0:
                for p_name, p_sample in param_samples.items():
                    if np.std(p_sample) > 0:
                        corr = np.corrcoef(p_sample, adjusted_pos_array)[0, 1]
                        sensitivities[p_name] = corr

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
                "eff_base_rates": base_rates,
                "Sensitivities": sensitivities
            })
            
        res_df = pd.DataFrame(results)
        display_cols = ["ID", "Modality", "現在のPhase", "標準PoS (%)", "調整後PoS 中央値 (%)", "悲観(5%) - 楽観(95%)", "Delta (pts)", "P3到達確率 (%)"]
        
        st.subheader("ポートフォリオ・サマリー (標準 vs 調整後)")
        st.dataframe(res_df[display_cols].style.format({
            "標準PoS (%)": "{:.1f}",
            "調整後PoS 中央値 (%)": "{:.1f}",
            "Delta (pts)": "{:+.1f}",
            "P3到達確率 (%)": "{:.1f}"
        }), use_container_width=True)
        
        col_charts1, col_charts2 = st.columns(2)
        
        with col_charts1:
            st.subheader("アトリション・ファンネル分析")
            for idx, row in res_df.iterrows():
                br = row['eff_base_rates']
                surv_p1 = 100.0
                surv_p2 = surv_p1 * br['Phase 1']
                surv_p3 = surv_p2 * br['Phase 2']
                surv_nda = surv_p3 * br['Phase 3']
                surv_market = surv_nda * br['NDA']
                
                fig = go.Figure(go.Funnel(
                    y = ["開始時", "Phase 1", "Phase 2", "Phase 3", "NDA 承認"],
                    x = [surv_p1, surv_p2, surv_p3, surv_nda, surv_market],
                    textinfo = "value+percent initial"
                ))
                fig.update_layout(
                    title=f"【{row['ID']}】 生存確率ファンネル",
                    margin=dict(l=20, r=20, t=40, b=20)
                )
                st.plotly_chart(fig, use_container_width=True, key=f"funnel_{row['ID']}_{idx}")

        with col_charts2:
            st.subheader("🌪️ 感度分析 (トルネードチャート)")
            for idx, row in res_df.iterrows():
                sens = row['Sensitivities']
                if sens:
                    sorted_sens = sorted(sens.items(), key=lambda x: abs(x[1]), reverse=False)
                    y_vals = [x[0] for x in sorted_sens]
                    x_vals = [x[1] for x in sorted_sens]
                    
                    colors = ['#EF553B' if val < 0 else '#636EFA' for val in x_vals]
                    
                    fig_sens = go.Figure(go.Bar(
                        x=x_vals, 
                        y=y_vals, 
                        orientation='h',
                        marker_color=colors,
                        text=[f"{v:.2f}" for v in x_vals],
                        textposition='auto'
                    ))
                    fig_sens.update_layout(
                        title=f"【{row['ID']}】 感度分析",
                        xaxis_title="相関係数 (Correlation with Final PoS)",
                        margin=dict(l=20, r=20, t=40, b=20)
                    )
                    st.plotly_chart(fig_sens, use_container_width=True, key=f"tornado_{row['ID']}_{idx}")
                else:
                    st.info(f"【{row['ID']}】 変動するパラメータ（分布設定）がないため、感度分析はスキップされました。")

    elif not st.session_state.projects:
        st.warning("タブ2でプロジェクトを登録してから実行してください。")
