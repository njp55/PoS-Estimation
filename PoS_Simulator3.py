import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import io

# ==========================================
# 1. 多言語辞書の設定
# ==========================================
LANG_DICT = {
    "JP": {
        "title": "臨床試験 PoS シミュレーター (Enterprise Edition)",
        "tab_config": ["⚙️ 初期設定 & I/O", "📝 プロジェクト・マスター", "📊 実行 & ダッシュボード"],
        "lang_label": "言語 / Language",
        "settings_header": "⚙️ システム設定とデータ入出力",
        "io_expander": "📥 データのインポート / 📤 エクスポート",
        "io_hint": "現在の設定とプロジェクトをExcelで入出力できます。Projectsシートの Applied_Params 列にカンマ区切りでパラメータ名を入力するとデフォルト値が適用されます。",
        "dl_btn": "テンプレート（現在のパイプライン一覧を含む）をダウンロード 📥",
        "ul_label": "設定・パイプラインのインポート (Excel)",
        "ul_btn": "インポートを実行",
        "mc_label": "モンテカルロ試行回数",
        "base_pos_header": "モダリティ別ベースPoSエディタ",
        "proj_header": "📝 プロジェクト・マスター",
        "new_proj_expander": "新規プロジェクトの登録",
        "proj_id": "プロジェクトID",
        "modality": "モダリティ",
        "indication": "対象疾患",
        "current_phase": "現在のフェーズ",
        "param_editor_header": "プロジェクト個別パラメータの設定",
        "register_btn": "プロジェクトを登録",
        "pipeline_list_header": "セッションベースのパイプライン一覧",
        "applied_params_label": "適用パラメータ",
        "del_btn": "削除",
        "exec_header": "📊 実行 & ダッシュボード",
        "run_btn": "🚀 シミュレーションを一斉起動",
        "summary_header": "ポートフォリオ・サマリー (標準 vs 調整後)",
        "funnel_header": "アトリション・ファンネル分析",
        "sensitivity_header": "🌪️ 感度分析 (トルネードチャート)",
        "standard_pos": "標準PoS (%)",
        "adjusted_pos": "調整後PoS 中央値 (%)",
        "pess_opt": "悲観(5%) - 楽観(95%)",
        "p3_prog": "P3到達確率 (%)",
        "phases": ["Phase 1", "Phase 2", "Phase 3", "NDA"],
        "funnel_stages": ["開始時", "Phase 1 通過", "Phase 2 通過", "Phase 3 通過", "NDA 承認"],
        "dist_options": ["Fixed", "Normal", "Triangular", "Uniform"]
    },
    "EN": {
        "title": "Clinical Trial PoS Simulator (Enterprise Edition)",
        "tab_config": ["⚙️ Settings & I/O", "📝 Project Master", "📊 Execution & Dashboard"],
        "lang_label": "Language / 言語",
        "settings_header": "⚙️ System Settings & Data I/O",
        "io_expander": "📥 Import / 📤 Export Data",
        "io_hint": "Export/Import settings and projects via Excel. You can apply default values by listing parameter names in the 'Applied_Params' column of the Projects sheet.",
        "dl_btn": "Download Template (Including current pipeline) 📥",
        "ul_label": "Import Settings/Pipeline (Excel)",
        "ul_btn": "Run Import",
        "mc_label": "Monte Carlo Trials",
        "base_pos_header": "Base PoS Editor by Modality",
        "proj_header": "📝 Project Master",
        "new_proj_expander": "Register New Project",
        "proj_id": "Project ID",
        "modality": "Modality",
        "indication": "Indication",
        "current_phase": "Current Phase",
        "param_editor_header": "Project-Specific Parameter Settings",
        "register_btn": "Register Project",
        "pipeline_list_header": "Session-Based Pipeline List",
        "applied_params_label": "Applied Parameters",
        "del_btn": "Delete",
        "exec_header": "📊 Execution & Dashboard",
        "run_btn": "🚀 Run Simulation",
        "summary_header": "Portfolio Summary (Standard vs adjusted)",
        "funnel_header": "Attrition Funnel Analysis",
        "sensitivity_header": "🌪️ Sensitivity Analysis (Tornado Chart)",
        "standard_pos": "Standard PoS (%)",
        "adjusted_pos": "Adjusted PoS Median (%)",
        "pess_opt": "Pessimistic(5%) - Optimistic(95%)",
        "p3_prog": "P3 Progression (%)",
        "phases": ["Phase 1", "Phase 2", "Phase 3", "NDA"],
        "funnel_stages": ["Start", "Pass Phase 1", "Pass Phase 2", "Pass Phase 3", "NDA Approved"],
        "dist_options": ["Fixed", "Normal", "Triangular", "Uniform"]
    }
}

# ==========================================
# 2. セッションステートの初期化
# ==========================================
if 'lang' not in st.session_state:
    st.session_state.lang = "JP"

L = LANG_DICT[st.session_state.lang]

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
    param_names = [
        "作用機序 (MoA) の明確性", "標的の性質 (Host vs Non-host)", "薬理作用 (刺激剤 vs 拮抗剤)",
        "組織曝露選択性 (STR/STAR)", "分子の物理化学的性質", "標的結合タンパク質数",
        "バイオマーカーの活用", "オンコロジー領域の効果", "代替エンドポイント相関",
        "疾患領域 (TA)", "モダリティ (創薬技術)", "臨床・免疫学的指標",
        "創薬の新規性 (FiC vs Me-too)", "導入経緯 (Licensed-in)", "リード適応症 (Lead indication)"
    ]
    st.session_state.current_params = pd.DataFrame({
        'Apply': [False] * 15,
        'Parameter Name': param_names,
        'Distribution': ['Normal', 'Fixed', 'Normal', 'Triangular', 'Uniform', 'Fixed', 'Normal', 'Normal', 'Triangular', 'Fixed', 'Fixed', 'Normal', 'Triangular', 'Fixed', 'Fixed'],
        'Value_Mean_Mode': [1.2, 1.3, 1.1, 1.2, np.nan, 0.9, 2.1, 4.0, 0.8, 1.0, 1.0, 1.1, 0.76, 1.2, 1.0],
        'Std_Min': [0.1, np.nan, 0.2, 0.8, 0.8, np.nan, 0.5, 1.0, 0.5, np.nan, np.nan, 0.2, 0.5, np.nan, np.nan],
        'Max': [np.nan, np.nan, np.nan, 1.5, 1.2, np.nan, np.nan, np.nan, 1.0, np.nan, np.nan, np.nan, 1.0, np.nan, np.nan]
    })

if 'current_params' not in st.session_state:
    reset_current_params()

# ==========================================
# 3. UI 構成
# ==========================================
st.set_page_config(page_title="PoS Simulator", layout="wide")

# サイドバーで言語切り替え
with st.sidebar:
    st.header(L["lang_label"])
    selected_lang = st.selectbox("Select Language", options=["JP", "EN"], index=0 if st.session_state.lang == "JP" else 1)
    if selected_lang != st.session_state.lang:
        st.session_state.lang = selected_lang
        st.rerun()

st.title(L["title"])
tab1, tab2, tab3 = st.tabs(L["tab_config"])

# --- Tab 1: Settings & I/O ---
with tab1:
    st.header(L["settings_header"])
    with st.expander(L["io_expander"], expanded=True):
        st.markdown(L["io_hint"])
        
        # エクスポート処理
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            st.session_state.base_pos.to_excel(writer, sheet_name='Base_PoS', index=False)
            st.session_state.current_params.to_excel(writer, sheet_name='Global_Parameters', index=False)
            proj_export = []
            proj_params_export = []
            for p in st.session_state.projects:
                applied_params_str = ",".join(p['Params']['Parameter Name'].tolist())
                proj_export.append({"ID": p["ID"], "Modality": p["Modality"], "Indication": p["Indication"], "Current Phase": p["Current Phase"], "Applied_Params": applied_params_str})
                for _, r in p['Params'].iterrows():
                    proj_params_export.append({"Project_ID": p["ID"], "Parameter Name": r["Parameter Name"], "Distribution": r["Distribution"], "Value_Mean_Mode": r["Value_Mean_Mode"], "Std_Min": r["Std_Min"], "Max": r["Max"]})
            pd.DataFrame(proj_export).to_excel(writer, sheet_name='Projects', index=False)
            pd.DataFrame(proj_params_export).to_excel(writer, sheet_name='Project_Parameters', index=False)
        
        st.download_button(label=L["dl_btn"], data=output.getvalue(), file_name="PoS_Template.xlsx")
        
        # インポート処理
        uploaded_file = st.file_uploader(L["ul_label"], type=["xlsx"])
        if uploaded_file and st.button(L["ul_btn"]):
            xls = pd.ExcelFile(uploaded_file)
            if 'Base_PoS' in xls.sheet_names: st.session_state.base_pos = pd.read_excel(xls, 'Base_PoS')
            if 'Global_Parameters' in xls.sheet_names: st.session_state.current_params = pd.read_excel(xls, 'Global_Parameters')
            if 'Projects' in xls.sheet_names:
                proj_df = pd.read_excel(xls, 'Projects')
                pp_df = pd.read_excel(xls, 'Project_Parameters') if 'Project_Parameters' in xls.sheet_names else pd.DataFrame()
                new_projs = []
                for _, row in proj_df.iterrows():
                    my_params = pd.DataFrame()
                    if not pp_df.empty and 'Project_ID' in pp_df.columns:
                        my_params = pp_df[pp_df['Project_ID'] == row['ID']].drop(columns=['Project_ID']).copy()
                        my_params['Apply'] = True
                    elif pd.notna(row.get('Applied_Params')):
                        p_names = [x.strip() for x in str(row['Applied_Params']).split(',')]
                        my_params = st.session_state.current_params[st.session_state.current_params['Parameter Name'].isin(p_names)].copy()
                        my_params['Apply'] = True
                    new_projs.append({"ID": row["ID"], "Modality": row["Modality"], "Indication": row["Indication"], "Current Phase": row["Current Phase"], "Params": my_params})
                st.session_state.projects = new_projs
            st.success("Import Complete!")
            st.rerun()

    st.subheader(L["mc_label"])
    st.session_state.mc_trials = st.number_input(L["mc_label"], 1000, 1000000, st.session_state.mc_trials, 1000)
    st.subheader(L["base_pos_header"])
    st.session_state.base_pos = st.data_editor(st.session_state.base_pos, num_rows="dynamic", use_container_width=True)

# --- Tab 2: Project Master ---
with tab2:
    st.header(L["proj_header"])
    with st.expander(L["new_proj_expander"], expanded=True):
        c1, c2 = st.columns(2)
        p_id = c1.text_input(L["proj_id"], f"PRJ-{len(st.session_state.projects)+1:03d}")
        p_mod = c1.selectbox(L["modality"], st.session_state.base_pos['Modality'].tolist())
        p_ind = c2.text_input(L["indication"], "Oncology")
        p_phs = c2.selectbox(L["current_phase"], L["phases"])
        
        st.subheader(L["param_editor_header"])
        edited_p = st.data_editor(st.session_state.current_params, num_rows="dynamic", use_container_width=True, key="p_edit",
                                  column_config={"Distribution": st.column_config.SelectboxColumn("Distribution", options=L["dist_options"])})
        if st.button(L["register_btn"]):
            st.session_state.projects.append({"ID": p_id, "Modality": p_mod, "Indication": p_ind, "Current Phase": p_phs, "Params": edited_p[edited_p['Apply']].copy()})
            st.rerun()

    st.subheader(L["pipeline_list_header"])
    if st.session_state.projects:
        sum_data = [{"ID": p["ID"], L["modality"]: p["Modality"], L["indication"]: p["Indication"], L["current_phase"]: p["Current Phase"], L["applied_params_label"]: ", ".join(p['Params']['Parameter Name'].tolist())} for p in st.session_state.projects]
        st.dataframe(pd.DataFrame(sum_data), use_container_width=True)
        cols = st.columns(5)
        for i, p in enumerate(st.session_state.projects):
            if cols[i%5].button(f"🗑️ {p['ID']}", key=f"del_{i}"):
                st.session_state.projects.pop(i)
                st.rerun()

# --- Tab 3: Execution ---
with tab3:
    st.header(L["exec_header"])
    if st.button(L["run_btn"]) and st.session_state.projects:
        results = []
        for proj in st.session_state.projects:
            # Calculation logic (same as previous version)
            base = st.session_state.base_pos[st.session_state.base_pos['Modality'] == proj['Modality']].iloc[0].copy()
            idx = L["phases"].index(proj['Current Phase'])
            for i in range(idx): base[L["phases"][i]] = 1.0
            overall_base = np.prod([base[p] for p in L["phases"]])
            
            modifiers = np.ones(st.session_state.mc_trials)
            samples = {}
            for _, r in proj['Params'].iterrows():
                d, m, s, mx = r['Distribution'], r['Value_Mean_Mode'], r['Std_Min'], r['Max']
                if d == 'Fixed': smp = np.full(st.session_state.mc_trials, m)
                elif d == 'Normal': smp = np.random.normal(m, s, st.session_state.mc_trials)
                elif d == 'Triangular': smp = np.random.triangular(s, m, mx, st.session_state.mc_trials)
                elif d == 'Uniform': smp = np.random.uniform(s, mx, st.session_state.mc_trials)
                modifiers *= smp
                if d != 'Fixed': samples[r['Parameter Name']] = smp
            
            odds = overall_base / (1 - overall_base) if overall_base < 1.0 else 1e9
            adj_pos = (odds * modifiers) / (1 + odds * modifiers)
            
            sens = {n: np.corrcoef(smp, adj_pos)[0,1] for n, smp in samples.items() if np.std(adj_pos)>0 and np.std(smp)>0}
            
            results.append({"ID": proj["ID"], "Modality": proj["Modality"], "Standard": overall_base*100, "Adjusted": np.median(adj_pos)*100, "Range": f"{np.percentile(adj_pos,5)*100:.1f}-{np.percentile(adj_pos,95)*100:.1f}%", "Delta": (np.median(adj_pos)-overall_base)*100, "P3": (base[L['phases'][0]]*base[L['phases'][1]]*100 if idx<2 else 100), "EffRates": base, "Sens": sens})

        res_df = pd.DataFrame(results)
        st.subheader(L["summary_header"])
        st.dataframe(res_df[["ID", "Modality", "Standard", "Adjusted", "Range", "Delta", "P3"]].rename(columns={"Standard": L["standard_pos"], "Adjusted": L["adjusted_pos"], "Range": L["pess_opt"], "P3": L["p3_prog"]}))

        c1, c2 = st.columns(2)
        for i, r in res_df.iterrows():
            with c1: # Funnel
                fig = go.Figure(go.Funnel(y=L["funnel_stages"], x=[100, 100*r['EffRates'][L['phases'][0]], 100*np.prod(r['EffRates'][:2]), 100*np.prod(r['EffRates'][:3]), 100*np.prod(r['EffRates'][:4])]))
                st.plotly_chart(fig, key=f"f_{i}")
            with c2: # Tornado
                if r['Sens']:
                    s_sens = sorted(r['Sens'].items(), key=lambda x: abs(x[1]))
                    fig2 = go.Figure(go.Bar(x=[x[1] for x in s_sens], y=[x[0] for x in s_sens], orientation='h'))
                    st.plotly_chart(fig2, key=f"t_{i}")
