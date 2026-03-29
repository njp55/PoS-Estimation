import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# --- Mathematical Logic Functions ---
def to_odds(p):
    """Convert probability to odds."""
    # Clip to avoid division by zero
    p = np.clip(p, 0.001, 0.999)
    return p / (1 - p)

def to_prob(o):
    """Convert odds to probability."""
    return o / (1 + o)

# --- Simulation Engine ---
def run_simulation(n_trials, base_pos, params):
    """Execute Monte Carlo simulation incorporating full specification parameters."""
    
    # Initialize base odds ratio modifier
    total_or = np.ones(n_trials)
    
    # 1. Scientific & Molecular Characteristics
    if params['moa'] == 'Established':
        total_or *= np.random.triangular(1.0, 1.2, 1.5, n_trials)
    else: # Novel
        total_or *= np.random.triangular(0.6, 0.8, 1.0, n_trials)
        
    if params['target_nature'] == 'Non-host (Bacteria/Virus)':
        total_or *= np.random.normal(1.3, 0.15, n_trials)
        
    # 2. Biomarkers & Disease Area
    if params['biomarker']:
        if params['ta'] == 'Oncology': # Corrected key to match the dictionary
            total_or *= np.random.normal(4.0, 0.5, n_trials) # Synergy effect
        else:
            total_or *= np.random.normal(2.1, 0.3, n_trials)
            
    # 3. Strategy & Portfolio
    if params['licensed_in']:
        total_or *= np.random.normal(1.2, 0.1, n_trials) # Due diligence premium
        
    if not params['lead_indication']:
        total_or *= np.random.triangular(0.5, 0.7, 0.9, n_trials) # Expansion penalty
        
    # First-in-Class (FiC) novelty tradeoff
    fic_score = params['fic_score']
    fic_penalty = 1.0 - (fic_score - 3) * np.random.normal(0.24, 0.05, n_trials)
    total_or *= np.clip(fic_penalty, 0.1, 2.0)
    
    # 4. Trial Design & Operations
    enrollment_ratio = params['enrollment'] / 100.0
    enroll_effect = enrollment_ratio * np.random.normal(1.0, 0.1, n_trials)
    total_or *= np.clip(enroll_effect, 0.1, 1.2) # Cap at 1.2 premium
    
    complexity = params['complexity']
    total_or *= np.exp(-0.01 * complexity) * np.random.normal(1.0, 0.1, n_trials)
    
    # 5. Organization, Psychology & Culture
    culture = params['culture']
    if culture == 'High (Truth-seeking)':
        total_or *= np.random.normal(1.5, 0.2, n_trials)
    elif culture == 'Low (Biased)':
        total_or *= np.random.triangular(0.4, 0.6, 0.8, n_trials)
        
    experience = params['sponsor_exp']
    total_or *= (1.0 + (experience * 0.05)) # Experience curve
    
    # Clip extreme overall outliers to prevent simulation breakage
    total_or = np.clip(total_or, 0.01, 20.0)

    # Calculate outcomes
    results = []
    for i in range(n_trials):
        current_phase = 1 # 1: P1, 2: P2, 3: P3, 4: NDA, 5: Approved
        
        pos_p1_adj = to_prob(to_odds(base_pos['P1']) * total_or[i])
        if np.random.rand() <= pos_p1_adj:
            current_phase = 2
            
            pos_p2_adj = to_prob(to_odds(base_pos['P2']) * total_or[i])
            if np.random.rand() <= pos_p2_adj:
                current_phase = 3
                
                pos_p3_adj = to_prob(to_odds(base_pos['P3']) * total_or[i])
                if np.random.rand() <= pos_p3_adj:
                    current_phase = 4
                    
                    pos_nda_adj = to_prob(to_odds(base_pos['NDA']) * total_or[i])
                    if np.random.rand() <= pos_nda_adj:
                        current_phase = 5
        
        results.append(current_phase)
        
    return np.array(results)

# --- App Initialization & State Management ---
st.set_page_config(page_title="Enterprise PoS Simulator", layout="wide")

if 'projects' not in st.session_state:
    st.session_state.projects = []

st.title("Clinical Trial PoS Simulator - Enterprise Edition")
st.markdown("Full Monte Carlo simulation platform incorporating scientific, strategic, and operational uncertainties.")

# --- Tab Navigation ---
tab1, tab2, tab3 = st.tabs(["⚙️ Initial Settings", "📝 Project Master", "📊 Execution & Dashboard"])

# --- TAB 1: Initial Settings ---
with tab1:
    st.header("Simulation Settings & Base Data")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Engine Configuration")
        n_trials = st.number_input("Number of Monte Carlo Trials", min_value=1000, max_value=100000, value=10000, step=1000)
    
    with col2:
        st.subheader("Base PoS by Modality")
        # Default Base PoS Dataframe
        default_df = pd.DataFrame({
            "Modality": ["Small Molecule", "Antibody", "CAR-T", "RNAi"],
            "P1": [0.60, 0.70, 0.80, 0.75],
            "P2": [0.30, 0.40, 0.45, 0.35],
            "P3": [0.65, 0.70, 0.60, 0.65],
            "NDA": [0.90, 0.92, 0.85, 0.90]
        })
        # Users can edit this table directly in the UI
        base_pos_df = st.data_editor(default_df, num_rows="dynamic", hide_index=True)

# --- TAB 2: Project Master ---
with tab2:
    st.header("Register New Project")
    
    with st.form("project_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Basic Information")
            p_id = st.text_input("Project ID", "PRJ-001")
            p_name = st.text_input("Project Name", "Alpha Compound")
            p_ta = st.selectbox("Therapeutic Area (TA)", ["Oncology", "Immunology", "Neurology", "Rare Disease", "Other"])
            p_modality = st.selectbox("Modality", base_pos_df["Modality"].tolist())
            
            st.subheader("Scientific & Molecular")
            p_moa = st.radio("Mechanism of Action (MoA)", ["Novel", "Established"], horizontal=True)
            p_target = st.radio("Target Nature", ["Host (Human)", "Non-host (Bacteria/Virus)"], horizontal=True)
            p_biomarker = st.checkbox("Utilizes Patient Selection Biomarker")
            
        with col2:
            st.subheader("Strategy & Portfolio")
            p_licensed = st.checkbox("Licensed-in (External Asset)")
            p_lead = st.checkbox("Lead Indication", value=True)
            p_fic = st.slider("First-in-Class (FiC) Novelty Score", 1, 5, 3, help="1=Me-too, 5=Highly Novel (Higher risk)")
            
            st.subheader("Trial Design & Operations")
            p_enrollment = st.number_input("Enrollment Speed Prediction (%)", min_value=10, max_value=150, value=100)
            p_complexity = st.slider("Protocol Complexity Score (0-100)", 0, 100, 50)
            
            st.subheader("Organization & Culture")
            p_culture = st.select_slider("Truth-seeking Culture", options=["Low (Biased)", "Medium", "High (Truth-seeking)"], value="Medium")
            p_exp = st.number_input("Sponsor's Past Approvals in TA", min_value=0, max_value=50, value=2)
            
        submit_btn = st.form_submit_button("➕ Add to Portfolio")
        
        if submit_btn:
            # Standardized dictionary keys
            project_data = {
                "id": p_id, 
                "name": p_name, 
                "ta": p_ta, 
                "modality": p_modality,
                "moa": p_moa, 
                "target_nature": p_target, 
                "biomarker": p_biomarker,
                "licensed_in": p_licensed, 
                "lead_indication": p_lead, 
                "fic_score": p_fic,
                "enrollment": p_enrollment, 
                "complexity": p_complexity,
                "culture": p_culture, 
                "sponsor_exp": p_exp
            }
            st.session_state.projects.append(project_data)
            st.success(f"Project {p_name} added successfully!")

    # Display currently registered projects
    if st.session_state.projects:
        st.subheader("Registered Projects Pipeline")
        display_df = pd.DataFrame(st.session_state.projects)
        # Reorder columns for better readability
        display_df = display_df[['id', 'name', 'ta', 'modality', 'moa', 'biomarker', 'licensed_in']]
        st.dataframe(display_df, hide_index=True)
        
        if st.button("🗑️ Clear All Projects"):
            st.session_state.projects = []
            st.rerun()

# --- TAB 3: Execution & Dashboard ---
with tab3:
    st.header("Portfolio Simulation Dashboard")
    
    if len(st.session_state.projects) == 0:
        st.info("No projects registered. Please add projects in the 'Project Master' tab.")
    else:
        # Run Simulation Button
        if st.button("🚀 Run Portfolio Simulation", type="primary"):
            with st.spinner('Running Monte Carlo Engine across Portfolio...'):
                
                results_summary = []
                st.session_state.sim_data = {} 
                
                for proj in st.session_state.projects:
                    # Retrieve base PoS for the specific modality
                    try:
                        modality_row = base_pos_df[base_pos_df['Modality'] == proj['modality']].iloc[0]
                    except IndexError:
                        st.error(f"Modality '{proj['modality']}' not found in Base PoS table.")
                        continue
                        
                    base_pos = {"P1": modality_row['P1'], "P2": modality_row['P2'], "P3": modality_row['P3'], "NDA": modality_row['NDA']}
                    
                    # Execute simulation
                    res = run_simulation(n_trials, base_pos, proj)
                    st.session_state.sim_data[proj['name']] = res
                    
                    # Aggregate results
                    approved = np.sum(res == 5) / n_trials
                    reached_p3 = np.sum(res >= 3) / n_trials
                    
                    # Calculate baseline for comparison
                    std_cum_pos = base_pos['P1'] * base_pos['P2'] * base_pos['P3'] * base_pos['NDA']
                    
                    results_summary.append({
                        "Project Name": proj['name'],
                        "TA": proj['ta'],
                        "Modality": proj['modality'],
                        "Standard PoS": f"{std_cum_pos*100:.1f}%",
                        "Simulated PoS": f"{approved*100:.1f}%",
                        "Delta (pts)": round((approved - std_cum_pos)*100, 1),
                        "P3 Reached": f"{reached_p3*100:.1f}%"
                    })
                
                # Save results to session state
                if results_summary:
                    st.session_state.results_df = pd.DataFrame(results_summary)
                    st.success("Simulation Complete!")

        # Display Summary Table & Visuals
        if 'results_df' in st.session_state:
            st.subheader("Portfolio Summary Overview")
            st.dataframe(st.session_state.results_df, hide_index=True)
            
            st.subheader("Deep Dive: Project Funnel Analysis")
            selected_proj = st.selectbox("Select Project to View Details", list(st.session_state.sim_data.keys()))
            
            if selected_proj:
                res = st.session_state.sim_data[selected_proj]
                stages = ['Phase I Start', 'Phase II Reached', 'Phase III Reached', 'NDA Submitted', 'Approved']
                counts = [n_trials, np.sum(res >= 2), np.sum(res >= 3), np.sum(res >= 4), np.sum(res == 5)]
                
                fig = go.Figure(go.Funnel(
                    y = stages,
                    x = counts,
                    textinfo = "value+percent initial",
                    marker = {"color": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]}
                ))
                fig.update_layout(title=f"Attrition Funnel for {selected_proj} (N={n_trials})", margin=dict(t=40, l=0, r=0, b=0))
                st.plotly_chart(fig, use_container_width=True)