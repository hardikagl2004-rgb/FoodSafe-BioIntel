"""
FoodSafe BioIntel — Single-File Interactive Decision-Support App
==================================================================
An Integrated Bioinformatics & Machine-Learning Framework for
Foodborne Pathogen Risk Assessment.

Everything is in ONE file — the curated database (20 pathogens),
the FPRI risk model, and K-Means / Hierarchical clustering are all
embedded/computed here. No external Excel file needed.

RUN:
    pip install streamlit pandas numpy scikit-learn scipy plotly
    streamlit run app_single.py

Selecting a bacterium in the sidebar shows: genome, virulence,
AMR, toxin, food source, epidemiology, detection & prevention,
its FPRI score/risk category (with radar chart), and which
K-Means / Hierarchical cluster it falls into (with its cluster-mates).
"""

import re
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import plotly.figure_factory as ff
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
from scipy.cluster.hierarchy import linkage

st.set_page_config(page_title="FoodSafe BioIntel", layout="wide", page_icon="🦠")

# ---------------------------------------------------------------------------
# 0. CUSTOM THEME / CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"]  { font-family: 'Inter', sans-serif; }
h1, h2, h3 { font-family: 'Poppins', sans-serif !important; }

/* App background */
.stApp {
    background: radial-gradient(circle at 15% 0%, #eaf6f6 0%, #f7fbf9 35%, #ffffff 70%);
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #073b4c 0%, #0b5563 55%, #118a7e 100%);
}
section[data-testid="stSidebar"] * { color: #eafffb !important; }

/* Text input & selectbox boxes are white/light-backed — force dark, readable
   text and placeholder color INSIDE them, overriding the blanket rule above. */
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] div[data-baseweb="select"] > div,
section[data-testid="stSidebar"] div[data-baseweb="select"] span,
section[data-testid="stSidebar"] div[data-baseweb="popover"] * ,
section[data-testid="stSidebar"] ul[role="listbox"] * {
    color: #073b4c !important;
}
section[data-testid="stSidebar"] input {
    background-color: #ffffff !important;
    border-radius: 8px;
}
section[data-testid="stSidebar"] input::placeholder {
    color: #6b8a8f !important;
    opacity: 1 !important;
}
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background-color: #ffffff !important;
}
section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.25); }

/* Metric cards (e.g. "Pathogens tracked") keep white backgrounds even inside
   the dark sidebar — force dark, readable text/labels inside them. */
section[data-testid="stSidebar"] div[data-testid="stMetric"] * {
    color: #073b4c !important;
}
section[data-testid="stSidebar"] div[data-testid="stMetricValue"] {
    color: #0b5563 !important;
}

/* Bordered containers (search card, result cards, benefit cards) get a
   subtle glow + lift so they read as "professional" clickable panels. */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 16px !important;
    box-shadow: 0 6px 20px rgba(17, 138, 126, 0.10);
    transition: box-shadow 0.15s ease, transform 0.15s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow: 0 10px 28px rgba(17, 138, 126, 0.22);
    transform: translateY(-2px);
}

/* Hero banner */
.hero-banner {
    background: linear-gradient(120deg, #0b5563 0%, #118a7e 45%, #06d6a0 100%);
    padding: 26px 34px; border-radius: 18px; margin-bottom: 18px;
    box-shadow: 0 8px 24px rgba(6, 214, 160, 0.25);
}
.hero-banner h1 { color: #ffffff !important; margin: 0; font-size: 2.1rem; }
.hero-banner p { color: #eafff7; margin: 4px 0 0 0; font-size: 0.95rem; }

/* Risk badges */
.risk-badge {
    display:inline-block; padding: 5px 16px; border-radius: 999px;
    font-weight: 600; font-size: 0.85rem; color: white; letter-spacing: 0.3px;
}
.risk-Critical { background: linear-gradient(120deg,#d90429,#a4133c); }
.risk-High     { background: linear-gradient(120deg,#f77f00,#e85d04); }
.risk-Moderate { background: linear-gradient(120deg,#ffca3a,#e6ac00); color:#3a2e00 !important; }
.risk-Low      { background: linear-gradient(120deg,#06d6a0,#2e8b57); }

/* Metric cards */
div[data-testid="stMetric"] {
    background: #ffffff; border-radius: 14px; padding: 14px 18px;
    box-shadow: 0 4px 14px rgba(17, 138, 126, 0.12); border: 1px solid #e3f3ef;
}
div[data-testid="stMetricValue"] { color: #0b5563; font-weight: 700; }

/* Tabs */
button[data-baseweb="tab"] {
    border-radius: 10px 10px 0 0 !important; font-weight: 600; color: #0b5563;
}
button[data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(120deg,#118a7e,#06d6a0) !important; color: white !important;
}

/* Section subheaders */
h3 { color: #0b5563 !important; border-bottom: 2px solid #e3f3ef; padding-bottom: 4px; }

/* Dataframe corners */
[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }

/* Buttons */
.stDownloadButton button, .stButton button {
    background: linear-gradient(120deg,#118a7e,#06d6a0); color: white; border: none;
    border-radius: 8px; font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# Consistent color palette used across every chart in the app
BRAND_COLORWAY = ["#118a7e", "#06d6a0", "#ffca3a", "#f77f00", "#e85d04",
                   "#d90429", "#073b4c", "#4cc9f0", "#7209b7", "#43aa8b"]
import plotly.io as pio
pio.templates["foodsafe"] = pio.templates["plotly_white"]
pio.templates["foodsafe"].layout.colorway = BRAND_COLORWAY
pio.templates.default = "foodsafe"

# ---------------------------------------------------------------------------
# 1. EMBEDDED CURATED DATABASE  (20 foodborne pathogens)
# ---------------------------------------------------------------------------
PATHOGEN_DATA = [
    {
        "name": "Salmonella enterica",
        "reference_strain": "Typhimurium LT2",
        "ncbi_accession": "NC_003197.2",
        "toxins_short": "Required",
        "food_sources_short": "Poultry, eggs, meat",
        "disease": "Salmonellosis",
        "symptoms": "nausea, stomach cramps, watery diarrhea, mild fever, headache; severe: high fever, bloody diarrhea, dehydration, vomiting",
        "onset": "6–72 hours after eating (usually 12–36 hrs)",
        "genome": "LT2; NC_003197; ~4.86 Mb; ~52% GC",
        "virulence": "SPI-1, SPI-2, fimbriae, flagella",
        "amr": "β-lactam, quinolone, aminoglycoside",
        "toxin": "Endotoxin, enterotoxin",
        "food": "Poultry, eggs, meat, produce",
        "epidemiology": "Salmonellosis; frequent outbreaks",
        "detection": "Culture, PCR, WGS",
        "prevention": "Cooking, hygiene, prevent cross-contamination",
        "V": 80.0,
        "A": 75.0,
        "O": 90.0,
        "P": 75.0,
        "D": 70.0,
        "FPRI": 79.25,
        "Risk": "Critical",
    },
    {
        "name": "E. coli O157:H7",
        "reference_strain": "",
        "ncbi_accession": "",
        "toxins_short": "",
        "food_sources_short": "",
        "disease": "",
        "symptoms": "mild stomach cramps, nausea; moderate: severe abdominal cramps, watery-then-bloody diarrhea, low-grade fever, vomiting; severe: hemolytic uremic syndrome (HUS) — decreased urination, fatigue, pale skin, easy bruising, kidney failure",
        "onset": "1–10 days after eating (usually 3–4 days)",
        "genome": "Sakai; NC_002695; ~5.5 Mb; ~50% GC",
        "virulence": "stx, eae, T3SS",
        "amr": "β-lactam, tetracycline, sulfonamide",
        "toxin": "Shiga toxin Stx1/Stx2",
        "food": "Beef, raw milk, leafy greens",
        "epidemiology": "STEC; HUS; severe disease",
        "detection": "Culture, PCR, WGS",
        "prevention": "Thorough cooking, pasteurization, hygiene",
        "V": 90.0,
        "A": 65.0,
        "O": 85.0,
        "P": 70.0,
        "D": 90.0,
        "FPRI": 80.75,
        "Risk": "Critical",
    },
    {
        "name": "Listeria monocytogenes",
        "reference_strain": "EGD-e",
        "ncbi_accession": "NC_003210",
        "toxins_short": "Listeriolysin O",
        "food_sources_short": "RTE foods, dairy, meat",
        "disease": "Listeriosis",
        "symptoms": "fever, muscle aches, nausea, mild diarrhea, headache; severe: stiff neck, confusion, loss of balance, convulsions (meningitis); in pregnancy: miscarriage, stillbirth, or life-threatening infection in the newborn",
        "onset": "1–4 weeks after eating (rarely up to 70 days) — unusually slow onset",
        "genome": "EGD-e; NC_003210; ~2.94 Mb; ~38% GC",
        "virulence": "hly, inlA, inlB, actA",
        "amr": "β-lactam, tetracycline, macrolide",
        "toxin": "Listeriolysin O",
        "food": "RTE foods, dairy, meat",
        "epidemiology": "Listeriosis; high-risk groups",
        "detection": "Culture, PCR, WGS",
        "prevention": "Refrigeration control, hygiene, RTE controls",
        "V": 85.0,
        "A": 55.0,
        "O": 70.0,
        "P": 85.0,
        "D": 95.0,
        "FPRI": 76.75,
        "Risk": "Critical",
    },
    {
        "name": "Campylobacter jejuni",
        "reference_strain": "NCTC 11168",
        "ncbi_accession": "NC_002163",
        "toxins_short": "CDT",
        "food_sources_short": "Poultry, milk",
        "disease": "Campylobacteriosis",
        "symptoms": "mild abdominal cramps, nausea, malaise; moderate: fever, watery-to-bloody diarrhea, vomiting; rare: Guillain-Barré syndrome (temporary paralysis, weeks after illness)",
        "onset": "2–5 days after eating",
        "genome": "NCTC 11168; NC_002163; ~1.64 Mb; ~30.6% GC",
        "virulence": "cadF, ciaB, flaA",
        "amr": "Fluoroquinolone, macrolide, tetracycline",
        "toxin": "CDT",
        "food": "Poultry, raw milk",
        "epidemiology": "Campylobacteriosis; common bacterial gastroenteritis",
        "detection": "Culture, PCR, WGS",
        "prevention": "Cook poultry, pasteurize milk, hygiene",
        "V": 75.0,
        "A": 70.0,
        "O": 90.0,
        "P": 65.0,
        "D": 65.0,
        "FPRI": 75.25,
        "Risk": "High",
    },
    {
        "name": "Staphylococcus aureus",
        "reference_strain": "NCTC 8325",
        "ncbi_accession": "NC_007795",
        "toxins_short": "Enterotoxins",
        "food_sources_short": "Meat, dairy, RTE foods",
        "disease": "Food intoxication",
        "symptoms": "sudden nausea, stomach cramping; moderate: vomiting, watery diarrhea within hours of eating; usually short-lived, no fever; severe cases: dehydration",
        "onset": "30 minutes–8 hours after eating (usually 2–4 hrs) — very fast onset",
        "genome": "NCTC 8325; NC_007795; ~2.82 Mb; ~33% GC",
        "virulence": "Adhesins, coagulase, immune evasion",
        "amr": "β-lactam, macrolide, tetracycline",
        "toxin": "Staphylococcal enterotoxins",
        "food": "Meat, dairy, RTE foods",
        "epidemiology": "Food intoxication; rapid onset",
        "detection": "Culture, PCR, toxin assays",
        "prevention": "Personal hygiene, temperature control",
        "V": 80.0,
        "A": 80.0,
        "O": 65.0,
        "P": 70.0,
        "D": 70.0,
        "FPRI": 75.0,
        "Risk": "High",
    },
    {
        "name": "Bacillus cereus",
        "reference_strain": "ATCC 10987",
        "ncbi_accession": "NC_003909",
        "toxins_short": "Cereulide, HBL, NHE",
        "food_sources_short": "Rice, cereals, dairy",
        "disease": "Food poisoning",
        "symptoms": "mild nausea; emetic form: rapid-onset vomiting (within 1-6 hours); diarrheal form: watery diarrhea and abdominal cramps (8-16 hours after eating), rarely severe",
        "onset": "emetic form: 30 min–6 hrs; diarrheal form: 6–15 hrs after eating",
        "genome": "ATCC 10987; NC_003909; ~5.4 Mb",
        "virulence": "hbl, nhe, cytK",
        "amr": "β-lactam, macrolide, tetracycline",
        "toxin": "Cereulide, HBL, NHE",
        "food": "Rice, cereals, dairy",
        "epidemiology": "Emetic/diarrheal food poisoning",
        "detection": "Culture, PCR, toxin detection",
        "prevention": "Rapid cooling, refrigeration",
        "V": 70.0,
        "A": 45.0,
        "O": 65.0,
        "P": 75.0,
        "D": 60.0,
        "FPRI": 63.75,
        "Risk": "High",
    },
    {
        "name": "Clostridium botulinum",
        "reference_strain": "ATCC 3502",
        "ncbi_accession": "NC_009495",
        "toxins_short": "Botulinum neurotoxin",
        "food_sources_short": "Canned/preserved foods",
        "disease": "Botulism",
        "symptoms": "early: fatigue, weakness, dizziness, dry mouth, blurred or double vision, drooping eyelids; progressing to: slurred speech, difficulty swallowing, muscle weakness spreading down the body; severe: difficulty breathing, respiratory failure (medical emergency)",
        "onset": "12–36 hours after eating (up to 10 days in rare cases)",
        "genome": "ATCC 3502; NC_009495; ~3.9 Mb",
        "virulence": "Neurotoxin-associated factors",
        "amr": "Variable",
        "toxin": "Botulinum neurotoxin",
        "food": "Canned/preserved foods",
        "epidemiology": "Botulism; severe neurological disease",
        "detection": "Culture, toxin assay, PCR",
        "prevention": "Proper canning, preservation, storage",
        "V": 95.0,
        "A": 30.0,
        "O": 40.0,
        "P": 85.0,
        "D": 100.0,
        "FPRI": 70.25,
        "Risk": "High",
    },
    {
        "name": "Clostridium perfringens",
        "reference_strain": "Strain 13",
        "ncbi_accession": "NC_003366",
        "toxins_short": "CPE",
        "food_sources_short": "Meat, poultry, gravy",
        "disease": "Foodborne gastroenteritis",
        "symptoms": "mild abdominal cramping; moderate: watery diarrhea, gas; usually no fever or vomiting, symptoms resolve within 24 hours",
        "onset": "6–24 hours after eating (usually ~10 hrs)",
        "genome": "Strain 13; NC_003366; ~3.0 Mb",
        "virulence": "cpa, plc, pfoA",
        "amr": "Variable",
        "toxin": "CPE",
        "food": "Meat, poultry, gravy",
        "epidemiology": "Foodborne gastroenteritis",
        "detection": "Culture, PCR, toxin detection",
        "prevention": "Proper cooking and hot/cold holding",
        "V": 75.0,
        "A": 35.0,
        "O": 60.0,
        "P": 80.0,
        "D": 65.0,
        "FPRI": 63.0,
        "Risk": "High",
    },
    {
        "name": "Shigella sonnei",
        "reference_strain": "Ss046",
        "ncbi_accession": "NC_007384",
        "toxins_short": "Shiga toxin*",
        "food_sources_short": "RTE foods, salads",
        "disease": "Shigellosis",
        "symptoms": "mild stomach cramps; moderate: fever, watery diarrhea, urgency/straining; severe: bloody or mucus-streaked diarrhea, high fever, dehydration",
        "onset": "1–4 days after exposure",
        "genome": "Ss046; NC_007384; ~5.0 Mb",
        "virulence": "ipa, virG/icsA",
        "amr": "Ampicillin, TMP-SMX, quinolone",
        "toxin": "Shiga toxin in some strains",
        "food": "Salads, RTE foods, water",
        "epidemiology": "Shigellosis; person-to-person spread",
        "detection": "Culture, PCR",
        "prevention": "Hand hygiene, sanitation",
        "V": 75.0,
        "A": 70.0,
        "O": 65.0,
        "P": 55.0,
        "D": 65.0,
        "FPRI": 66.75,
        "Risk": "High",
    },
    {
        "name": "Shigella flexneri",
        "reference_strain": "2a 301",
        "ncbi_accession": "NC_004337",
        "toxins_short": "Shiga toxin*",
        "food_sources_short": "Produce, salads",
        "disease": "Shigellosis",
        "symptoms": "mild abdominal pain; moderate: fever, watery diarrhea, urgency to defecate; severe: bloody diarrhea, high fever, dehydration, seizures (in young children)",
        "onset": "1–4 days after exposure",
        "genome": "2a 301; NC_004337; ~4.6 Mb",
        "virulence": "ipa, virG/icsA, T3SS",
        "amr": "Ampicillin, tetracycline, quinolone",
        "toxin": "Shiga toxin in some strains",
        "food": "Produce, salads, water",
        "epidemiology": "Shigellosis; outbreaks",
        "detection": "Culture, PCR, WGS",
        "prevention": "Hygiene, sanitation, safe water",
        "V": 80.0,
        "A": 75.0,
        "O": 70.0,
        "P": 55.0,
        "D": 70.0,
        "FPRI": 70.75,
        "Risk": "High",
    },
    {
        "name": "Vibrio cholerae",
        "reference_strain": "N16961",
        "ncbi_accession": "NC_002505 + NC_002506",
        "toxins_short": "Cholera toxin",
        "food_sources_short": "Seafood, water",
        "disease": "Cholera",
        "symptoms": "mild loose stools; moderate: watery diarrhea, mild cramps; severe: profuse 'rice-water' diarrhea, vomiting, rapid dehydration, muscle cramps, low blood pressure — can be fatal within hours if untreated",
        "onset": "a few hours–5 days after eating (usually 2–3 days)",
        "genome": "N16961; NC_002505/506; ~4.0 Mb",
        "virulence": "ctx, tcp",
        "amr": "Tetracycline, macrolide, quinolone",
        "toxin": "Cholera toxin",
        "food": "Seafood, contaminated water",
        "epidemiology": "Cholera; epidemic potential",
        "detection": "Culture, PCR",
        "prevention": "Safe water, sanitation, seafood cooking",
        "V": 90.0,
        "A": 65.0,
        "O": 85.0,
        "P": 60.0,
        "D": 85.0,
        "FPRI": 78.5,
        "Risk": "Critical",
    },
    {
        "name": "Vibrio parahaemolyticus",
        "reference_strain": "RIMD 2210633",
        "ncbi_accession": "NC_004603 + NC_004605",
        "toxins_short": "TDH/TRH",
        "food_sources_short": "Raw seafood",
        "disease": "Gastroenteritis",
        "symptoms": "mild nausea; moderate: watery diarrhea, abdominal cramps, vomiting; severe: fever, chills, bloody diarrhea (less common)",
        "onset": "4–96 hours after eating (usually ~24 hrs)",
        "genome": "RIMD 2210633; NC_004603/605; ~5.2 Mb",
        "virulence": "tdh, trh, T3SS",
        "amr": "Tetracycline, quinolone",
        "toxin": "TDH/TRH",
        "food": "Raw/undercooked seafood",
        "epidemiology": "Seafood-associated gastroenteritis",
        "detection": "Culture, PCR",
        "prevention": "Cook seafood, prevent cross-contamination",
        "V": 80.0,
        "A": 55.0,
        "O": 70.0,
        "P": 55.0,
        "D": 60.0,
        "FPRI": 66.0,
        "Risk": "High",
    },
    {
        "name": "Yersinia enterocolitica",
        "reference_strain": "8081",
        "ncbi_accession": "NC_008800",
        "toxins_short": "Yersiniabactin-associated",
        "food_sources_short": "Pork, dairy",
        "disease": "Yersiniosis",
        "symptoms": "mild abdominal discomfort; moderate: fever, watery-to-bloody diarrhea, abdominal pain that can mimic appendicitis (especially in teens/young adults); later: joint pain (reactive arthritis) in some cases",
        "onset": "4–7 days after eating",
        "genome": "8081; NC_008800; ~4.6 Mb",
        "virulence": "ail, inv, yadA",
        "amr": "β-lactam, tetracycline",
        "toxin": "Yersinia-associated factors",
        "food": "Pork, dairy, produce",
        "epidemiology": "Yersiniosis; gastroenteritis",
        "detection": "Culture, PCR",
        "prevention": "Cook pork, pasteurization, hygiene",
        "V": 70.0,
        "A": 50.0,
        "O": 55.0,
        "P": 60.0,
        "D": 60.0,
        "FPRI": 60.25,
        "Risk": "High",
    },
    {
        "name": "Cronobacter sakazakii",
        "reference_strain": "ATCC BAA-894",
        "ncbi_accession": "NC_009778",
        "toxins_short": "Toxin/virulence factors",
        "food_sources_short": "Infant formula",
        "disease": "Neonatal infection",
        "symptoms": "in infants — mild: poor feeding, irritability, low energy; moderate: fever, crying; severe: sepsis, meningitis — bulging soft spot on head, seizures, high fever (medical emergency in infants)",
        "onset": "2–4 days after exposure (variable, infants)",
        "genome": "ATCC BAA-894; NC_009778; ~4.4 Mb",
        "virulence": "OmpA, adhesins, invasion factors",
        "amr": "β-lactam, aminoglycoside",
        "toxin": "Strain-dependent toxins/factors",
        "food": "Powdered infant formula",
        "epidemiology": "Neonatal infection; severe in infants",
        "detection": "Culture, PCR, WGS",
        "prevention": "Formula hygiene, safe preparation/storage",
        "V": 75.0,
        "A": 60.0,
        "O": 40.0,
        "P": 65.0,
        "D": 90.0,
        "FPRI": 64.75,
        "Risk": "High",
    },
    {
        "name": "Aeromonas hydrophila",
        "reference_strain": "ATCC 7966",
        "ncbi_accession": "NC_008570",
        "toxins_short": "Aerolysin, hemolysin",
        "food_sources_short": "Fish, seafood",
        "disease": "Gastroenteritis",
        "symptoms": "mild watery diarrhea; moderate: abdominal pain, nausea, occasional fever; wound exposure: redness, swelling, and pain at the site (can worsen quickly)",
        "onset": "1–2 days after eating",
        "genome": "ATCC 7966; NC_008570; ~4.7 Mb",
        "virulence": "aerA, hlyA, alt, ast",
        "amr": "β-lactam, tetracycline, quinolone",
        "toxin": "Aerolysin, hemolysin",
        "food": "Fish, seafood, water",
        "epidemiology": "Gastroenteritis; opportunistic infections",
        "detection": "Culture, PCR",
        "prevention": "Seafood hygiene, water quality",
        "V": 70.0,
        "A": 55.0,
        "O": 50.0,
        "P": 70.0,
        "D": 55.0,
        "FPRI": 59.25,
        "Risk": "High",
    },
    {
        "name": "Enterococcus faecalis",
        "reference_strain": "V583",
        "ncbi_accession": "NC_004668",
        "toxins_short": "Cytolysin",
        "food_sources_short": "Dairy, meat, RTE foods",
        "disease": "Opportunistic infection",
        "symptoms": "often no symptoms (gut coloniser); opportunistic infection: urinary burning/frequency, wound redness/pain; severe (bloodstream/heart valve infection): fever, chills, fatigue, rapid heartbeat",
        "onset": "variable — opportunistic infection, not a classic food-poisoning timeline",
        "genome": "V583; NC_004668; ~3.2 Mb",
        "virulence": "Adhesins, biofilm, cytolysin",
        "amr": "Vancomycin, β-lactam, aminoglycoside",
        "toxin": "Cytolysin in some strains",
        "food": "Dairy, meat, RTE foods",
        "epidemiology": "Mainly opportunistic; AMR concern",
        "detection": "Culture, PCR, WGS",
        "prevention": "Hygiene, contamination control",
        "V": 65.0,
        "A": 75.0,
        "O": 40.0,
        "P": 60.0,
        "D": 50.0,
        "FPRI": 59.25,
        "Risk": "High",
    },
    {
        "name": "Enterococcus faecium",
        "reference_strain": "DO",
        "ncbi_accession": "NC_017022",
        "toxins_short": "Cytolysin*",
        "food_sources_short": "Meat, dairy",
        "disease": "Opportunistic infection",
        "symptoms": "often no symptoms (gut coloniser); opportunistic infection: urinary discomfort, wound infection signs; severe: fever, chills, fatigue — higher concern due to antibiotic (vancomycin) resistance",
        "onset": "variable — opportunistic infection, not a classic food-poisoning timeline",
        "genome": "DO; NC_017022; ~2.7 Mb",
        "virulence": "Adhesins, biofilm factors",
        "amr": "Vancomycin, β-lactam, aminoglycoside",
        "toxin": "Cytolysin in some strains",
        "food": "Meat, dairy, RTE foods",
        "epidemiology": "Opportunistic; VRE concern",
        "detection": "Culture, PCR, WGS",
        "prevention": "Hygiene, AMR surveillance",
        "V": 60.0,
        "A": 85.0,
        "O": 40.0,
        "P": 60.0,
        "D": 50.0,
        "FPRI": 61.25,
        "Risk": "High",
    },
    {
        "name": "Streptococcus suis",
        "reference_strain": "P1/7",
        "ncbi_accession": "NC_012925",
        "toxins_short": "Suilysin",
        "food_sources_short": "Pork",
        "disease": "Zoonotic disease",
        "symptoms": "mild fever, headache; moderate: high fever, stiff neck, vomiting (meningitis signs); severe: confusion, hearing loss, sepsis, septic shock — mainly an occupational risk (pork handlers)",
        "onset": "hours to several days after exposure (mainly direct contact, not classic food timeline)",
        "genome": "P1/7; NC_012925; ~2.0 Mb",
        "virulence": "sly, mrp, epf",
        "amr": "β-lactam, macrolide, tetracycline",
        "toxin": "Suilysin",
        "food": "Pork",
        "epidemiology": "Zoonotic infection; occupational risk",
        "detection": "Culture, PCR",
        "prevention": "Safe pork handling, cooking, hygiene",
        "V": 75.0,
        "A": 60.0,
        "O": 35.0,
        "P": 55.0,
        "D": 70.0,
        "FPRI": 59.5,
        "Risk": "High",
    },
    {
        "name": "Vibrio vulnificus",
        "reference_strain": "YJ016",
        "ncbi_accession": "NC_005139 + NC_005140",
        "toxins_short": "Hemolysin/cytolysin",
        "food_sources_short": "Raw oysters",
        "disease": "Septicemia/wound infection",
        "symptoms": "mild nausea, watery diarrhea; moderate: vomiting, abdominal pain, fever, chills; wound exposure: rapidly spreading redness, swelling, blistering skin lesions; severe: bloodstream infection, sepsis — can be life-threatening, especially in liver disease/immunocompromised",
        "onset": "12–72 hours after eating (usually ~24 hrs)",
        "genome": "YJ016; NC_005139/140; ~5.0 Mb",
        "virulence": "Capsule, vvhA, iron acquisition",
        "amr": "Variable; strain-dependent",
        "toxin": "Hemolysin/cytolysin",
        "food": "Raw oysters, seafood",
        "epidemiology": "Severe wound infection/septicemia",
        "detection": "Culture, PCR",
        "prevention": "Thorough seafood cooking; avoid raw oysters for high-risk people",
        "V": 90.0,
        "A": 45.0,
        "O": 40.0,
        "P": 65.0,
        "D": 100.0,
        "FPRI": 68.0,
        "Risk": "High",
    },
    {
        "name": "Campylobacter coli",
        "reference_strain": "Reference genome",
        "ncbi_accession": "CP006702",
        "toxins_short": "CDT",
        "food_sources_short": "Poultry, meat",
        "disease": "Campylobacteriosis",
        "symptoms": "mild abdominal cramps, nausea; moderate: fever, watery-to-bloody diarrhea, vomiting; usually resolves within a week without treatment",
        "onset": "2–5 days after eating",
        "genome": "Reference genome; CP006702; ~1.7 Mb",
        "virulence": "Flagella, adhesins, invasion factors",
        "amr": "Fluoroquinolone, macrolide, tetracycline",
        "toxin": "CDT",
        "food": "Poultry, meat",
        "epidemiology": "Campylobacteriosis",
        "detection": "Culture, PCR, WGS",
        "prevention": "Cook meat/poultry, hygiene",
        "V": 70.0,
        "A": 70.0,
        "O": 65.0,
        "P": 60.0,
        "D": 60.0,
        "FPRI": 67.5,
        "Risk": "High",
    },
]

RISK_COLORS = {"Critical": "#d90429", "High": "#f77f00", "Moderate": "#ffca3a", "Low": "#06d6a0"}

# Plain-language names for the Common Person / Community Guide view
RISK_SIMPLE = {
    "Critical": ("🔴", "Very High Concern", "Historically linked to frequent, severe outbreaks — take extra care."),
    "High":     ("🟠", "High Concern",      "A well-known cause of food poisoning — normal precautions matter a lot."),
    "Moderate": ("🟡", "Moderate Concern",  "Less common, but still worth basic food-safety habits."),
    "Low":      ("🟢", "Lower Concern",     "Relatively rarer, but good hygiene still helps."),
}

# Map each pathogen to everyday food categories using keyword search over its
# food-related text fields, so a common person can browse "by food" instead
# of by bacteria name.
FOOD_CATEGORY_KEYWORDS = {
    "🍗 Poultry & Eggs": ["poultry", "egg", "chicken"],
    "🥩 Red Meat": ["meat", "beef", "pork"],
    "🐟 Seafood & Fish": ["seafood", "fish", "shellfish", "oyster"],
    "🥛 Dairy": ["dairy", "milk", "cheese"],
    "🥬 Fruits & Vegetables": ["produce", "vegetable", "fruit", "salad", "leafy"],
    "💧 Water & Environment": ["water", "environment"],
    "🍼 Infant / Powdered Foods": ["infant", "formula", "powdered"],
}


def food_categories_for(row):
    text = f"{row.get('food','')} {row.get('food_sources_short','')}".lower()
    cats = [cat for cat, kws in FOOD_CATEGORY_KEYWORDS.items() if any(kw in text for kw in kws)]
    return cats or ["🍽️ Other / Mixed sources"]


def plain_help(term_dict):
    """Render a simple, jargon-free explanation box."""
    with st.expander("❓ What do these terms mean? (plain-language)"):
        for term, meaning in term_dict.items():
            st.markdown(f"**{term}** — {meaning}")


def download_df_button(dataframe, label, filename, key=None):
    """Small CSV download button placed right under a table, so every table
    in the app can be saved and reopened in Excel/Sheets."""
    csv_bytes = dataframe.to_csv(index=False).encode("utf-8")
    st.download_button(
        f"⬇️ {label} (CSV)", data=csv_bytes, file_name=filename,
        mime="text/csv", key=key,
    )


def download_chart_button(fig, label, filename, key=None):
    """Points to the chart's own built-in PNG download (camera icon in its
    toolbar) — this runs entirely in the browser, so it always works,
    unlike a server-side image export which would require Chrome to be
    installed on whichever machine is running the app."""
    st.caption(f"📷 Use the camera icon in the top-right of the chart above to save **{label}** as a PNG image.")


# Plain-language descriptors for what "High" or "Low" on each FPRI feature
# actually means, used to auto-generate a human-readable cluster summary.
FEATURE_TRAITS = {
    "V": {"High": "spread and invade the body aggressively",
          "Low": "be less invasive than most"},
    "A": {"High": "be hard to treat with common antibiotics",
          "Low": "be generally easier to treat with antibiotics"},
    "O": {"High": "be linked to frequent food-poisoning outbreaks",
          "Low": "be rarely linked to reported outbreaks"},
    "P": {"High": "survive a long time on food or surfaces",
          "Low": "not survive long outside the body"},
    "D": {"High": "cause severe illness",
          "Low": "cause milder illness"},
}
FEATURE_NAMES = {"V": "Virulence", "A": "AMR", "O": "Outbreaks",
                  "P": "Persistence", "D": "Severity"}
CLUSTER_ICONS = ["🔥", "💊", "📈", "🧫", "⚔️", "🌡️", "🦠", "⚠️"]


def describe_cluster(cluster_centers_row, overall_means, icon="🔬"):
    """Turn a cluster's raw centroid (0-100 units) into a plain-language
    one-line summary, by comparing it to the dataset's overall averages."""
    diffs = {feat: cluster_centers_row[feat] - overall_means[feat] for feat in "VAOPD"}
    # Rank features by how distinctive this cluster is on them
    ranked = sorted(diffs.items(), key=lambda kv: abs(kv[1]), reverse=True)
    traits = []
    for feat, diff in ranked:
        if abs(diff) > 8:  # meaningfully different from the dataset average
            level = "High" if diff > 0 else "Low"
            traits.append(FEATURE_TRAITS[feat][level])
        if len(traits) == 2:
            break
    if not traits:
        summary = "have a fairly average risk profile across the board"
    else:
        summary = " and ".join(traits)
    top_feat = ranked[0][0]
    label = f"{FEATURE_NAMES[top_feat]}-Driven"
    return label, f"Germs in this group tend to {summary}."


# ---------------------------------------------------------------------------
# Plain-language glossary for every gene code / antibiotic class / virulence
# term used anywhere in the 20-pathogen database, so the Genomics tab never
# shows an unexplained abbreviation.
# ---------------------------------------------------------------------------
GLOSSARY = {
    # --- Virulence genes / factors ---
    "spi-1": "a gene cluster that lets the bacterium invade the gut lining",
    "spi-2": "a gene cluster that helps the bacterium survive and multiply inside immune cells",
    "fimbriae": "hair-like structures that help the bacterium stick to surfaces or cells",
    "flagella": "whip-like tails that let the bacterium swim and move around",
    "stx": "the gene for Shiga toxin — damages blood vessels and can cause kidney failure",
    "eae": "a gene that lets the bacterium attach tightly to gut cells, causing damage",
    "t3ss": "'Type III Secretion System' — a molecular syringe bacteria use to inject harmful proteins directly into host cells",
    "hly": "a gene that makes a toxin which punches holes in host cells (hemolysin)",
    "inla": "a protein that lets the bacterium invade gut cells",
    "inlb": "a protein that helps the bacterium invade other cell types, including the liver",
    "acta": "a protein that lets the bacterium hijack a cell's internal skeleton to spread to neighboring cells",
    "cadf": "a protein that helps the bacterium stick to gut cells",
    "ciab": "a gene that helps the bacterium invade host cells",
    "flaa": "the main protein building block of the flagellum (movement tail)",
    "adhesins": "surface proteins that let the bacterium stick to host cells or tissue",
    "coagulase": "an enzyme that clots blood, helping the bacterium hide from the immune system",
    "immune evasion": "general term for tricks the bacterium uses to avoid being detected/killed by the immune system",
    "hbl": "'Hemolysin BL' — a toxin that damages cells and causes diarrhea",
    "nhe": "'Non-hemolytic Enterotoxin' — a toxin that causes diarrhea",
    "cytk": "'Cytotoxin K' — a toxin that damages host cell membranes",
    "cpa": "'Alpha toxin' — damages cell membranes and tissue",
    "plc": "'Phospholipase C' — an enzyme that breaks down cell membranes",
    "pfoa": "'Perfringolysin O' — a toxin that punches holes in host cells",
    "ipa": "'Invasion plasmid antigen' — proteins that let the bacterium invade gut cells",
    "virg/icsa": "a protein that lets the bacterium spread directly from cell to cell, dodging the immune system",
    "ctx": "the gene for cholera toxin — causes massive fluid loss (watery diarrhea)",
    "tcp": "'Toxin-Coregulated Pilus' — a hair-like structure that helps the bacterium colonize the gut and helps it pick up the cholera toxin gene",
    "tdh": "'Thermostable Direct Hemolysin' — a toxin that damages host cells",
    "trh": "'TDH-Related Hemolysin' — a toxin similar to TDH",
    "ail": "'Attachment Invasion Locus' — helps the bacterium stick to and invade host cells",
    "inv": "a gene that helps the bacterium invade host cells",
    "yada": "'Yersinia Adhesin A' — a surface protein that helps the bacterium stick to host tissue",
    "ompa": "'Outer Membrane Protein A' — helps the bacterium invade cells and resist the immune system",
    "invasion factors": "general term for proteins that help the bacterium get inside host cells",
    "aera": "a gene for aerolysin, a toxin that punches holes in host cells",
    "hlya": "a gene for hemolysin, a toxin that destroys red blood cells",
    "alt": "'Heat-Labile Cytotonic Enterotoxin' — a toxin that causes fluid loss/diarrhea",
    "ast": "'Heat-Stable Cytotonic Enterotoxin' — a toxin that causes fluid loss/diarrhea",
    "biofilm": "a protective slimy layer bacteria build together, making them harder to kill",
    "cytolysin": "a toxin that destroys host cells by breaking open their outer membrane",
    "sly": "'Suilysin' — a toxin that punches holes in host cells",
    "mrp": "'Muramidase-Released Protein' — a marker linked to more severe disease",
    "epf": "'Extracellular Protein Factor' — a marker linked to more severe disease",
    "capsule": "a protective outer coating that helps the bacterium hide from the immune system",
    "vvha": "a toxin gene that damages host cells and tissue",
    "iron acquisition": "the bacterium's system for stealing iron from the host's body, which it needs to grow",
    "neurotoxin-associated factors": "genes/proteins that help produce and release the nerve-damaging botulinum toxin",
    # --- AMR / antibiotic classes ---
    "β-lactam": "a common antibiotic family that includes penicillin — works by breaking the bacterium's cell wall",
    "quinolone": "an antibiotic family that stops bacteria from copying their DNA",
    "fluoroquinolone": "a stronger, modern version of the quinolone antibiotic family",
    "aminoglycoside": "an antibiotic family that stops bacteria from building proteins they need to survive",
    "tetracycline": "an antibiotic family that blocks bacterial protein production",
    "macrolide": "an antibiotic family (includes azithromycin) that blocks bacterial protein production",
    "sulfonamide": "an older antibiotic family that blocks a vitamin (folate) the bacterium needs to grow",
    "ampicillin": "a specific penicillin-type antibiotic",
    "tmp-smx": "'Trimethoprim-Sulfamethoxazole' — a combination antibiotic (co-trimoxazole)",
    "vancomycin": "a 'last-resort' antibiotic used when other options fail — resistance to it is a serious concern",
    "variable": "resistance differs a lot from strain to strain, so no single pattern applies",
    "strain-dependent": "resistance depends on which specific strain is involved",
    # --- Toxins ---
    "endotoxin": "part of the bacterium's own outer wall (LPS) that triggers fever, inflammation, and shock when released",
    "enterotoxin": "a toxin that specifically targets the gut, causing fluid loss and diarrhea",
    "listeriolysin o": "a toxin that lets the bacterium punch out of the cell compartment it's trapped in and spread inside the body",
    "cdt": "'Cytolethal Distending Toxin' — damages host cell DNA, stopping infected cells from dividing normally",
    "staphylococcal enterotoxins": "heat-resistant toxins (survive cooking) that cause rapid-onset vomiting — this is why food left out too long can still make you sick even after reheating",
    "cereulide": "a heat-stable toxin (survives cooking) that causes rapid vomiting, mainly from reheated rice",
    "botulinum neurotoxin": "one of the most potent toxins known — blocks nerve signals to muscles, causing paralysis",
    "cpe": "'Clostridium perfringens Enterotoxin' — damages the gut lining, causing watery diarrhea and cramps",
    "shiga toxin in some strains": "some strains of this species carry the Shiga toxin gene (see 'stx' above), which damages blood vessels and can cause kidney failure",
    "cholera toxin": "causes gut cells to pump out massive amounts of fluid, leading to the severe watery diarrhea typical of cholera",
    "yersinia-associated factors": "a general term for toxins/proteins this species uses to invade tissue and cause inflammation",
    "aerolysin": "a toxin that punches holes in host cell membranes, killing them",
    "hemolysin": "a toxin that destroys red blood cells",
    "suilysin": "a toxin that punches holes in host cells, contributing to severe infections like meningitis",
}


def explain_terms(text):
    """Split a comma-separated field like 'stx, eae, T3SS' into individual
    terms and look each one up in the glossary, so raw gene codes are never
    shown without a plain-language explanation."""
    if not text:
        return []
    raw_terms = [t.strip() for t in re.split(r"[,;]", text) if t.strip()]
    explained = []
    for term in raw_terms:
        key = term.lower().strip()
        meaning = GLOSSARY.get(key)
        if meaning is None:
            # try stripping trailing/leading descriptive words for a fuzzy match
            for gk, gv in GLOSSARY.items():
                if gk in key or key in gk:
                    meaning = gv
                    break
        explained.append((term, meaning))
    return explained



df = pd.DataFrame(PATHOGEN_DATA)

# ---------------------------------------------------------------------------
# 2. FPRI MODEL (recomputed live from V/A/O/P/D, per proposal §9-10)
#    FPRI = 0.30*V + 0.25*A + 0.20*O + 0.15*P + 0.10*D
# ---------------------------------------------------------------------------
def classify_risk(score):
    if score <= 25:
        return "Low"
    elif score <= 50:
        return "Moderate"
    elif score <= 75:
        return "High"
    else:
        return "Critical"

df["FPRI_calc"] = (0.30 * df["V"] + 0.25 * df["A"] + 0.20 * df["O"]
                    + 0.15 * df["P"] + 0.10 * df["D"])
# Keep the sheet's own FPRI/Risk as authoritative display value, but verify consistency
df["Risk_calc"] = df["FPRI_calc"].apply(classify_risk)

# ---------------------------------------------------------------------------
# 3. MACHINE LEARNING: K-Means + Hierarchical Clustering (Objective 4)
# ---------------------------------------------------------------------------
@st.cache_resource
def run_clustering(k):
    """Fits and returns the ACTUAL model objects (not just labels/scores) so the
    trained KMeans, AgglomerativeClustering, StandardScaler and PCA instances
    are all inspectable/downloadable from the app."""
    X = df[["V", "A", "O", "P", "D"]].values
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    km = KMeans(n_clusters=k, n_init=10, random_state=42)
    km_labels = km.fit_predict(Xs)

    hier = AgglomerativeClustering(n_clusters=k, linkage="ward")
    hier_labels = hier.fit_predict(Xs)

    Z = linkage(Xs, method="ward")
    sil = silhouette_score(Xs, km_labels) if k > 1 else np.nan
    sample_sil = None
    if k > 1:
        from sklearn.metrics import silhouette_samples
        sample_sil = silhouette_samples(Xs, km_labels)

    pca = PCA(n_components=2, random_state=42)
    X2 = pca.fit_transform(Xs)

    return {
        "Xs": Xs, "km_labels": km_labels, "hier_labels": hier_labels, "Z": Z,
        "sil": sil, "sample_sil": sample_sil, "X2": X2,
        "scaler": scaler, "km_model": km, "hier_model": hier, "pca_model": pca,
    }


@st.cache_data
def best_k_search(data, k_min=2, k_max=8):
    X = data[["V", "A", "O", "P", "D"]].values
    Xs = StandardScaler().fit_transform(X)
    ks, inertias, sils = [], [], []
    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, n_init=10, random_state=42)
        labels = km.fit_predict(Xs)
        ks.append(k)
        inertias.append(km.inertia_)
        sils.append(silhouette_score(Xs, labels))
    return ks, inertias, sils


# ---------------------------------------------------------------------------
# 3b. APP FLOW — a guided, professional multi-step journey:
#     Welcome -> Symptom/Food Search -> Results grid -> Full Detail page.
#     No bacteria name is ever required to get in.
# ---------------------------------------------------------------------------
if "stage" not in st.session_state:
    st.session_state.stage = "welcome"       # welcome -> search -> results -> detail
if "selected_pathogen" not in st.session_state:
    st.session_state.selected_pathogen = None
if "search_query" not in st.session_state:
    st.session_state.search_query = ""
if "search_matches" not in st.session_state:
    st.session_state.search_matches = df["name"].tolist()


def _go(stage, **kwargs):
    st.session_state.stage = stage
    for key, val in kwargs.items():
        st.session_state[key] = val
    st.rerun()


# Common everyday words that don't literally appear in the curated text but
# should still find the right pathogens (e.g. "chicken" -> the data says
# "poultry"). Search expands each query word through this map.
SEARCH_SYNONYMS = {
    "chicken": ["poultry"], "hen": ["poultry"], "turkey": ["poultry"],
    "beef": ["meat"], "steak": ["meat"], "burger": ["meat"],
    "pork": ["meat", "pork"], "bacon": ["meat", "pork"], "ham": ["meat", "pork"],
    "milk": ["dairy", "milk"], "cheese": ["dairy", "cheese"], "yogurt": ["dairy"],
    "egg": ["egg", "poultry"], "eggs": ["egg", "poultry"],
    "fish": ["seafood", "fish"], "shrimp": ["seafood"], "prawn": ["seafood"],
    "oyster": ["seafood", "oyster"], "oysters": ["seafood", "oyster"],
    "shellfish": ["seafood"], "sushi": ["seafood", "fish"],
    "vegetable": ["produce"], "vegetables": ["produce"], "veggie": ["produce"],
    "salad": ["produce", "salad"], "greens": ["produce", "leafy"],
    "fruit": ["produce", "fruit"], "sprouts": ["produce"],
    "rice": ["rice", "cereals"], "leftovers": ["reheat"],
    "formula": ["infant", "formula"], "baby": ["infant"], "infant": ["infant"],
    "puking": ["vomit"], "throwing": ["vomit"], "sick": ["nausea", "vomit"],
    "poop": ["diarrhea", "stool"], "poo": ["diarrhea", "stool"],
    "stomachache": ["cramps", "abdominal"], "cramping": ["cramps"],
    "loose": ["diarrhea", "watery"], "runny": ["diarrhea", "watery"],
    "tired": ["fatigue"], "exhausted": ["fatigue"],
    "cold": ["chills"], "shivering": ["chills"],
    "confused": ["confusion"], "dizzy": ["dizziness"],
    "paralysis": ["paralysis", "weakness"], "numbness": ["weakness"],
}


def _search_matches(q):
    q = q.strip().lower()
    if not q:
        return df["name"].tolist()

    def _text(r):
        return (f"{r['food']} {r['food_sources_short']} {r['disease']} "
                f"{r['epidemiology']} {r['symptoms']} {r['name']}").lower()

    # 1) Exact-phrase match first (most precise)
    hits = df[df.apply(lambda r: q in _text(r), axis=1)]
    if not hits.empty:
        return hits["name"].tolist()

    # 2) Fall back to per-word matching (with synonym expansion) so phrases
    #    like "fever and vomiting" or everyday words like "chicken" still
    #    work, and word-form differences (vomit/vomiting, diarrhea/diarrheal)
    #    match via simple substring-either-way stemming.
    raw_words = [w for w in re.split(r"[^a-z]+", q) if len(w) >= 3]
    query_words = set(raw_words)
    for w in raw_words:
        query_words.update(SEARCH_SYNONYMS.get(w, []))

    def _word_hits(text_words, qw):
        return any(qw in tw or tw in qw for tw in text_words if len(tw) >= 3)

    def _row_matches(r):
        text_words = re.split(r"[^a-z]+", _text(r))
        return any(_word_hits(text_words, qw) for qw in query_words)

    if query_words:
        hits = df[df.apply(_row_matches, axis=1)]
    return hits["name"].tolist()


# ============================== WELCOME STAGE ==============================
if st.session_state.stage == "welcome":
    st.markdown("""
    <div class="hero-banner" style="text-align:center; padding: 40px 30px;">
        <h1 style="font-size:2.6rem;">🦠 FoodSafe BioIntel</h1>
        <p style="font-size:1.1rem;">An Integrated Bioinformatics & Machine-Learning Framework
        for Foodborne Pathogen Risk Assessment</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🌍 Why this project exists")
    st.write(
        "Food poisoning affects millions of people every year, yet information about which "
        "germs cause it, how dangerous each one is, and how to avoid them is scattered across "
        "technical databases most people never see. **You don't need to know any bacteria "
        "names to use this tool** — you can start from a food you eat or a symptom you're "
        "worried about, and the system finds the relevant information for you."
    )

    st.markdown("### 👥 Who this helps, and how")
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        with st.container(border=True):
            st.markdown("#### 🏠 Everyday People")
            st.write("Search by the **food you're eating** — no science background needed. "
                     "Get plain-language risk levels and kitchen safety tips.")
    with b2:
        with st.container(border=True):
            st.markdown("#### 🍳 Food Vendors & Cooks")
            st.write("Quickly check which germs are linked to specific ingredients "
                     "(poultry, seafood, dairy, etc.) and what handling practices reduce risk.")
    with b3:
        with st.container(border=True):
            st.markdown("#### 🩺 Health Workers & Educators")
            st.write("Use the risk categories and high-risk-group guidance to counsel "
                     "patients or communities during outbreak seasons.")
    with b4:
        with st.container(border=True):
            st.markdown("#### 🎓 Students & Researchers")
            st.write("Explore the full curated genomic/virulence/AMR database, the FPRI "
                     "scoring model, and live K-Means/Hierarchical clustering.")

    st.markdown("---")
    _, mid, _ = st.columns([1, 1, 1])
    with mid:
        if st.button("🚀 Enter the System", use_container_width=True):
            _go("search")
    st.stop()

# ============================== SEARCH STAGE ================================
if st.session_state.stage == "search":
    st.sidebar.title("🦠 FoodSafe BioIntel")
    if st.sidebar.button("⬅️ Back to welcome page"):
        _go("welcome")

    st.markdown("<div style='height:6vh'></div>", unsafe_allow_html=True)
    left, mid, right = st.columns([1, 2, 1])
    with mid:
        with st.container(border=True):
            st.markdown(
                "<h1 style='text-align:center; letter-spacing:3px; margin-bottom:4px;'>"
                "SYMPTOM CHECK</h1>"
                "<p style='text-align:center; color:#5a8a85; margin-bottom:28px;'>"
                "No bacteria names needed — just tell us what's worrying you.</p>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<p style='color:#118a7e; font-weight:600; margin-bottom:2px;'>"
                "Symptom or Food</p>", unsafe_allow_html=True,
            )
            query = st.text_input(
                "Symptom or food", label_visibility="collapsed",
                placeholder="e.g. 'diarrhea', 'vomiting', 'chicken', 'seafood'...",
                value=st.session_state.search_query,
            )
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            if st.button("FIND POSSIBLE CAUSES", use_container_width=True):
                matches = _search_matches(query)
                _go("results", search_query=query, search_matches=matches)
            if st.button("Browse all 20 pathogens instead", use_container_width=True):
                _go("results", search_query="", search_matches=df["name"].tolist())

            st.markdown(
                "<p style='text-align:center; color:#5a8a85; margin-top:20px;'>"
                "Not sure what to type? Tap a common symptom:</p>",
                unsafe_allow_html=True,
            )
            common_symptoms = ["Diarrhea", "Vomiting", "Fever", "Stomach cramps",
                                "Nausea", "Bloody diarrhea", "Chills", "Dehydration"]
            chip_cols = st.columns(4)
            for i, sym in enumerate(common_symptoms):
                with chip_cols[i % 4]:
                    if st.button(sym, key=f"chip_{sym}", use_container_width=True):
                        matches = _search_matches(sym)
                        _go("results", search_query=sym, search_matches=matches)
    st.stop()

# ============================== RESULTS STAGE ================================
if st.session_state.stage == "results":
    st.sidebar.title("🦠 FoodSafe BioIntel")
    if st.sidebar.button("⬅️ Back to welcome page"):
        _go("welcome")
    if st.sidebar.button("🔍 New search"):
        _go("search")

    q = st.session_state.search_query
    matches = st.session_state.search_matches
    header = f"Results for “{q}”" if q else "All 20 Pathogens"
    st.markdown(f"""
    <div class="hero-banner">
        <h1 style="font-size:1.8rem;">🔎 {header}</h1>
        <p>{len(matches)} match{"es" if len(matches) != 1 else ""} found.
           Click any card below to see full details.</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("← New search"):
        _go("search")

    with st.expander("🚨 When to seek medical help right away (read this first)"):
        st.error(
            "**Get medical care immediately if you or someone else has any of these:**\n\n"
            "- Difficulty breathing or swallowing, blurred/double vision, or drooping eyelids\n"
            "- Signs of severe dehydration — very little or no urination, extreme thirst, "
            "dizziness, or confusion\n"
            "- Bloody diarrhea combined with a high fever\n"
            "- Diarrhea or vomiting that won't stop after 3 days\n"
            "- A stiff neck, severe headache, or confusion\n"
            "- Any of the above in a **pregnant person, infant, older adult, or someone "
            "with a weakened immune system** — don't wait, seek care sooner\n\n"
            "This is general awareness information, not a diagnosis — when in doubt, "
            "contact a doctor or your local emergency services."
        )

    if not matches:
        st.warning("No matches found for that term. Try a different food or symptom, "
                    "or browse all pathogens from the search page.")
    else:
        result_rows = df[df["name"].isin(matches)].sort_values("FPRI", ascending=False)
        cols = st.columns(3)
        for i, (_, m) in enumerate(result_rows.iterrows()):
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(
                        f"<span class='risk-badge risk-{m['Risk']}'>{m['Risk']}</span>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"#### {m['name']}")
                    st.caption(f"Causes: {m['disease']}")
                    st.write(f"🤒 **Symptoms:** {m['symptoms'].split(';')[0].strip()}")
                    st.write(f"⏱️ **Usually appears:** {m['onset']}")
                    st.write(f"FPRI Score: **{m['FPRI']:.1f}**")
                    if st.button("View Full Details →", key=f"view_{m['name']}",
                                 use_container_width=True):
                        _go("detail", selected_pathogen=m["name"])
    st.stop()

# ============================== DETAIL STAGE =================================
# (stage == "detail" from here on)
st.sidebar.title("🦠 FoodSafe BioIntel")
st.sidebar.caption("A simple food-safety guide + a research-grade risk model, "
                    "built from one shared dataset of 20 common foodborne germs.")

nav1, nav2 = st.sidebar.columns(2)
with nav1:
    if st.button("⬅️ Results", use_container_width=True):
        _go("results")
with nav2:
    if st.button("🔍 New search", use_container_width=True):
        _go("search")
if st.sidebar.button("🏠 Welcome page"):
    _go("welcome")

st.sidebar.markdown("#### Jump to another pathogen")
selected = st.sidebar.selectbox(
    "Select a bacterium", df["name"].tolist(),
    index=df["name"].tolist().index(st.session_state.selected_pathogen)
    if st.session_state.selected_pathogen in df["name"].tolist() else 0,
)
st.session_state.selected_pathogen = selected

k = st.sidebar.slider("Number of clusters (k)", min_value=2, max_value=8, value=6)

M = run_clustering(k)
Xs, km_labels, hier_labels, Z, sil, sample_sil, X2 = (
    M["Xs"], M["km_labels"], M["hier_labels"], M["Z"], M["sil"], M["sample_sil"], M["X2"]
)
scaler, km_model, hier_model, pca_model = M["scaler"], M["km_model"], M["hier_model"], M["pca_model"]
df["KMeans_Cluster"] = km_labels
df["Hierarchical_Cluster"] = hier_labels

st.sidebar.markdown("---")
st.sidebar.metric("Pathogens tracked", len(df))
st.sidebar.metric("Silhouette score (current k)", f"{sil:.3f}")
st.sidebar.download_button(
    "⬇️ Download full database (CSV)",
    data=df.drop(columns=["FPRI_calc", "Risk_calc"]).to_csv(index=False).encode("utf-8"),
    file_name="foodsafe_bioint_full_database.csv", mime="text/csv",
    use_container_width=True,
)
st.sidebar.markdown("---")
st.sidebar.caption("FPRI is a proposed, provisional scoring model for framework "
                    "testing — not a validated clinical/public-health index.")

# ---------------------------------------------------------------------------
# 5. MAIN PANEL — everything about the selected bacterium
# ---------------------------------------------------------------------------
row = df[df["name"] == selected].iloc[0]

st.markdown(f"""
<div class="hero-banner">
    <h1>🦠 {row['name']}</h1>
    <p>Reference strain: <b>{row['reference_strain']}</b> &nbsp;|&nbsp;
       NCBI Accession: <b>{row['ncbi_accession']}</b> &nbsp;|&nbsp;
       <span class="risk-badge risk-{row['Risk']}">{row['Risk']} RISK</span>
    </p>
</div>
""", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
c1.metric("FPRI Score", f"{row['FPRI']:.2f}")
c2.metric("Risk Category", row["Risk"])
c3.metric("K-Means Cluster", f"#{int(row['KMeans_Cluster'])}")
st.markdown("<br>", unsafe_allow_html=True)

tab_community, tab_try, tab_overview, tab_biology, tab_risk, tab_cluster, tab_compare, tab_model, tab_manual = st.tabs(
    ["🍽️ Community Guide", "🧪 Try the Model", "📋 Overview", "🧬 Genomics & Biology",
     "📊 FPRI Breakdown", "🌐 Clustering", "⚖️ Compare All Pathogens", "🤖 Model Details",
     "📖 Manual & Sources"]
)

# --- Community Guide tab (plain language, for everyone) --------------------
with tab_community:
    st.subheader("🍽️ Food Safety Guide — in plain language")
    st.caption("No science background needed. Pick a food you're curious about, "
               "or read the general kitchen safety tips below.")

    chosen_cat = st.selectbox(
        "What food are you concerned about?",
        sorted(set(c for _, r in df.iterrows() for c in food_categories_for(r))),
    )
    matches = df[df.apply(lambda r: chosen_cat in food_categories_for(r), axis=1)]

    st.markdown(f"### Germs commonly linked to **{chosen_cat}**")
    for _, m in matches.sort_values("FPRI", ascending=False).iterrows():
        icon, label, blurb = RISK_SIMPLE[m["Risk"]]
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**{m['name']}** — commonly causes *{m['disease']}*")
                st.write(f"🤒 **Watch for:** {m['symptoms'].split(';')[0].strip()}")
                st.write(f"🛡️ **How to protect yourself:** {m['prevention']}")
            with c2:
                st.markdown(f"<div style='text-align:center; font-size:1.8rem'>{icon}</div>"
                             f"<div style='text-align:center; font-weight:600'>{label}</div>",
                             unsafe_allow_html=True)
    if len(matches) == 0:
        st.info("No specific entries found for this category in the current database.")

    st.markdown("---")
    st.markdown("### 🧊 General Kitchen Safety Checklist")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            "- **Cook thoroughly** — use a food thermometer where possible; "
            "juices should run clear, no pink/raw centers.\n"
            "- **Chill promptly** — refrigerate leftovers within 2 hours.\n"
            "- **Separate** raw meat/poultry/seafood from ready-to-eat food "
            "(use different cutting boards).\n"
        )
    with c2:
        st.markdown(
            "- **Wash hands, surfaces & produce** before and after handling food.\n"
            "- **Avoid unpasteurized** milk, juice, or soft cheeses if unsure of source.\n"
            "- **When in doubt, throw it out** — don't taste-test food you suspect has spoiled.\n"
        )

    st.markdown("### 👪 Who should be extra careful")
    st.markdown(
        "Pregnant women, young children, older adults, and people with weakened immune "
        "systems are generally more vulnerable to severe food poisoning. If someone in "
        "these groups develops persistent vomiting, diarrhea, high fever, or dehydration "
        "after eating, contact a doctor rather than waiting it out."
    )

    st.markdown("### 🚨 When to seek medical help right away")
    st.error(
        "**Don't wait if you see:** difficulty breathing/swallowing, blurred or double "
        "vision, drooping eyelids, signs of severe dehydration (little/no urination, "
        "extreme thirst, dizziness), bloody diarrhea with high fever, symptoms lasting "
        "more than 3 days, a stiff neck or confusion — or **any** symptom in a pregnant "
        "person, infant, older adult, or immunocompromised person."
    )

    st.markdown("### 🚦 What the colors mean")
    for risk, (icon, label, blurb) in RISK_SIMPLE.items():
        st.markdown(f"{icon} **{label}** ({risk}) — {blurb}")

    st.caption(
        "This guide simplifies the same curated dataset used in the technical tabs. "
        "It is for general awareness only and does not replace medical or public-health advice."
    )


# --- Overview tab -----------------------------------------------------
with tab_overview:
    st.info(f"⏱️ **Symptoms usually appear:** {row['onset']}")

    st.subheader("🤒 Symptoms (minor → severe)")
    parts = [p.strip() for p in row["symptoms"].split(";")]
    sev_cols = st.columns(len(parts))
    sev_labels = ["Mild", "Moderate", "Severe"][:len(parts)]
    for col, label, part in zip(sev_cols, sev_labels, parts):
        with col:
            st.markdown(f"**{label}**")
            st.write(part.split(":", 1)[-1].strip() if ":" in part else part)

    left, right = st.columns(2)
    with left:
        st.subheader("Disease & Epidemiology")
        st.write(f"**Disease:** {row['disease']}")
        st.write(f"**Epidemiology:** {row['epidemiology']}")
        st.subheader("Food Sources")
        st.write(row["food"])
        st.subheader("Toxins")
        st.write(row["toxin"])
    with right:
        st.subheader("Detection Methods")
        st.write(row["detection"])
        st.subheader("Prevention & Control")
        st.write(row["prevention"])
        st.subheader("Antimicrobial Resistance (AMR)")
        st.write(row["amr"])

# --- Genomics & Biology tab --------------------------------------------
with tab_biology:
    st.info(
        "🧬 **Reading this page:** each field below shows the most cited genes, "
        "resistance types, or toxins for this species in the literature — it's a "
        "**representative summary, not the complete genome**. A real bacterial genome "
        "has thousands of genes; only the handful most relevant to how dangerous it is "
        "are listed here. Tap any expander below to see what each short code actually means."
    )

    st.subheader("Genome")
    st.write(row["genome"])
    st.caption("The reference genome this species was sequenced from, its NCBI ID, "
               "approximate genome size (in megabases), and GC content (a measure of "
               "the genome's DNA composition, often used to compare/identify species).")

    st.subheader("🦠 Virulence Factors — what makes it able to cause disease")
    st.write(row["virulence"])
    vir_terms = explain_terms(row["virulence"])
    if vir_terms:
        with st.expander("🔍 What do these mean, in plain language?"):
            for term, meaning in vir_terms:
                if meaning:
                    st.markdown(f"**{term}** — {meaning}")
                else:
                    st.markdown(f"**{term}** — a specific virulence factor for this species "
                                f"(not yet in the glossary; ask a microbiology reference for detail).")

    st.subheader("💊 AMR Profile — which antibiotic families it resists")
    st.write(row["amr"])
    amr_terms = explain_terms(row["amr"])
    if amr_terms:
        with st.expander("🔍 What do these mean, in plain language?"):
            for term, meaning in amr_terms:
                if meaning:
                    st.markdown(f"**{term}** — {meaning}")
                else:
                    st.markdown(f"**{term}** — an antibiotic class this species can resist.")
    st.caption("This lists antibiotic **families** the species has shown resistance to in "
               "at least some strains — not every individual bacterium of this species is "
               "resistant to every drug listed.")

    st.subheader("☠️ Toxin Details — what actually makes people sick")
    st.write(row["toxin"])
    tox_terms = explain_terms(row["toxin"])
    if tox_terms:
        with st.expander("🔍 What do these mean, in plain language?"):
            for term, meaning in tox_terms:
                if meaning:
                    st.markdown(f"**{term}** — {meaning}")
                else:
                    st.markdown(f"**{term}** — the specific toxin (or toxin type) this "
                                f"species produces.")

# --- FPRI Breakdown tab --------------------------------------------------
with tab_risk:
    st.subheader("FPRI = 0.30·V + 0.25·A + 0.20·O + 0.15·P + 0.10·D")
    plain_help({
        "Virulence (V)": "How well this germ can invade the body and cause harm.",
        "AMR (A)": "Antimicrobial resistance — how hard it is to treat with common antibiotics.",
        "Outbreak (O)": "How often this germ has been linked to reported food-poisoning outbreaks.",
        "Persistence (P)": "How long the germ can survive on food, surfaces, or in the environment.",
        "Severity (D)": "How serious the illness tends to be if someone gets infected.",
        "FPRI": "A single 0–100 'risk score' combining all five factors above, weighted by importance.",
    })
    colA, colB = st.columns([1, 1])
    with colA:
        radar_df = pd.DataFrame(dict(
            metric=["Virulence (V)", "AMR (A)", "Outbreak (O)", "Persistence (P)", "Severity (D)"],
            value=[row["V"], row["A"], row["O"], row["P"], row["D"]],
        ))
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=radar_df["value"], theta=radar_df["metric"],
                                       fill="toself", name=row["name"]))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                           showlegend=False, height=450)
        st.plotly_chart(fig, use_container_width=True)
        download_chart_button(fig, f"{row['name']} radar chart", f"{row['name'].replace(' ', '_')}_radar.png")
    with colB:
        fpri_table = pd.DataFrame({
            "Component": ["Virulence (V)", "AMR (A)", "Outbreak (O)", "Persistence (P)", "Severity (D)"],
            "Score (0-100)": [row["V"], row["A"], row["O"], row["P"], row["D"]],
            "Weight": ["30%", "25%", "20%", "15%", "10%"],
        })
        st.dataframe(fpri_table, hide_index=True, use_container_width=True)
        download_df_button(fpri_table, f"{row['name']} FPRI breakdown",
                            f"{row['name'].replace(' ', '_')}_fpri_breakdown.csv", key="dl_fpri_breakdown")
        st.metric("Computed FPRI", f"{row['FPRI_calc']:.2f}", row["Risk_calc"])
        st.caption(f"Sheet-reported FPRI: {row['FPRI']:.2f} ({row['Risk']})")

# --- Clustering tab -------------------------------------------------------
with tab_cluster:
    st.subheader(f"Cluster membership at k = {k}")
    plain_help({
        "Clustering": "An automatic way of grouping similar pathogens together, "
                      "based on their risk scores — like sorting fruit by size and color "
                      "without being told the names of the fruit first.",
        "K-Means": "One clustering method — it groups pathogens around a set number of 'centers'.",
        "Hierarchical Clustering": "Another method that builds a family tree of similarity, "
                                   "shown as the dendrogram below.",
        "Cluster": "A group of pathogens the model found to be similar to each other.",
    })

    overall_means = df[["V", "A", "O", "P", "D"]].mean()
    my_cluster_id = int(row["KMeans_Cluster"])
    my_members = df[df["KMeans_Cluster"] == my_cluster_id]
    my_center = my_members[["V", "A", "O", "P", "D"]].mean()
    icon = CLUSTER_ICONS[my_cluster_id % len(CLUSTER_ICONS)]
    label, summary = describe_cluster(my_center, overall_means, icon)

    st.markdown(f"### {icon} {row['name']} is in the **“{label}”** group")
    st.info(summary)
    other_members = [n for n in my_members["name"] if n != row["name"]]
    if other_members:
        st.write(f"**Other germs in this group:** " + ", ".join(other_members))
    else:
        st.write("**Other germs in this group:** — none, this pathogen forms its own distinct group.")

    with st.expander("🗂️ See all groups explained in plain language"):
        for cid in sorted(df["KMeans_Cluster"].unique()):
            members = df[df["KMeans_Cluster"] == cid]
            center = members[["V", "A", "O", "P", "D"]].mean()
            icn = CLUSTER_ICONS[cid % len(CLUSTER_ICONS)]
            lbl, summ = describe_cluster(center, overall_means, icn)
            st.markdown(f"**{icn} Group #{cid} — “{lbl}”**")
            st.caption(summ)
            st.write(", ".join(members["name"].tolist()))
            st.markdown("")

    with st.expander("🔬 Advanced view: PCA scatter plot & dendrogram (for research/coursework)"):
        same_km = df[df["KMeans_Cluster"] == row["KMeans_Cluster"]]["name"].tolist()
        same_hier = df[df["Hierarchical_Cluster"] == row["Hierarchical_Cluster"]]["name"].tolist()
        colA, colB = st.columns(2)
        with colA:
            st.markdown(f"**K-Means cluster #{int(row['KMeans_Cluster'])} members:**")
            st.write(", ".join(same_km))
        with colB:
            st.markdown(f"**Hierarchical cluster #{int(row['Hierarchical_Cluster'])} members:**")
            st.write(", ".join(same_hier))

        var_pct = pca_model.explained_variance_ratio_ * 100
        st.info(
            "📐 **What PC1 and PC2 mean:** the real data has 5 dimensions "
            "(V, A, O, P, D), too many to plot on a flat screen. PCA "
            "(Principal Component Analysis) compresses those 5 dimensions "
            f"down to the 2 that capture the most spread in the data — "
            f"**PC1 explains {var_pct[0]:.1f}%** of the differences between "
            f"pathogens, and **PC2 explains {var_pct[1]:.1f}%** more "
            f"(together {var_pct[0]+var_pct[1]:.1f}%). They have no single "
            "real-world unit — think of PC1/PC2 as 'directions of biggest "
            "difference,' not an actual measurement. Points close together "
            "are similar overall; points far apart are very different."
        )

        plot_df = pd.DataFrame(dict(
            PC1=X2[:, 0], PC2=X2[:, 1], Bacteria=df["name"],
            Cluster=df["KMeans_Cluster"].astype(str), Risk=df["Risk"],
        ))
        plot_df["is_selected"] = plot_df["Bacteria"] == selected
        fig = px.scatter(plot_df, x="PC1", y="PC2", color="Cluster", text="Bacteria",
                          hover_data=["Risk"], height=550,
                          symbol="is_selected", symbol_map={True: "star", False: "circle"})
        fig.update_traces(textposition="top center")
        fig.update_layout(
            xaxis_title=f"PC1 ({var_pct[0]:.1f}% of variance)",
            yaxis_title=f"PC2 ({var_pct[1]:.1f}% of variance)",
        )
        st.plotly_chart(fig, use_container_width=True)
        download_chart_button(fig, "PCA scatter plot", "pca_scatter.png")
        download_df_button(plot_df.drop(columns=["is_selected"]), "PCA coordinates & clusters",
                            "pca_coordinates.csv", key="dl_pca_coords")

        fig2 = ff.create_dendrogram(Xs, labels=df["name"].tolist(), linkagefun=lambda x: Z)
        fig2.update_layout(height=550, title="Hierarchical Clustering Dendrogram (Ward linkage)",
                            xaxis_title="Pathogen", yaxis_title="Merge distance (Ward linkage)")
        st.plotly_chart(fig2, use_container_width=True)
        download_chart_button(fig2, "dendrogram", "dendrogram.png")

# --- Compare All tab -------------------------------------------------------
with tab_compare:
    st.subheader("All 20 pathogens ranked by FPRI")
    ordered = df.sort_values("FPRI", ascending=False)
    colors = ordered["name"].apply(lambda n: "gold" if n == selected else None)
    fig = px.bar(ordered, x="FPRI", y="name", orientation="h", color="Risk",
                 color_discrete_map=RISK_COLORS, height=650)
    fig.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="FPRI Score", yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)
    download_chart_button(fig, "FPRI ranking chart", "fpri_ranking.png")

    st.subheader("Full data table")
    compare_tbl = df[["name", "V", "A", "O", "P", "D", "FPRI", "Risk",
                       "KMeans_Cluster", "Hierarchical_Cluster"]].sort_values("FPRI", ascending=False)
    styled = (
        compare_tbl.style
        .background_gradient(subset=["V", "A", "O", "P", "D", "FPRI"], cmap="YlOrRd")
        .map(lambda v: f"background-color: {RISK_COLORS.get(v, '#fff')}; color: white; font-weight: 600;",
             subset=["Risk"])
        .format({"FPRI": "{:.2f}"})
    )
    st.dataframe(styled, use_container_width=True, hide_index=True)
    download_df_button(compare_tbl, "Full pathogen comparison table", "all_20_pathogens.csv",
                        key="dl_compare_table")

    st.subheader("Elbow & Silhouette (choosing k)")
    ks, inertias, sils = best_k_search(df)
    elbow_sil_df = pd.DataFrame({"k": ks, "Inertia": inertias, "Silhouette": sils})
    c1, c2 = st.columns(2)
    with c1:
        fig_elbow = px.line(x=ks, y=inertias, markers=True,
                             labels={"x": "k", "y": "Inertia"}, title="Elbow Method")
        st.plotly_chart(fig_elbow, use_container_width=True)
    with c2:
        fig_sil_line = px.line(x=ks, y=sils, markers=True,
                                labels={"x": "k", "y": "Silhouette Score"}, title="Silhouette Analysis")
        st.plotly_chart(fig_sil_line, use_container_width=True)
    download_df_button(elbow_sil_df, "Elbow & silhouette data (all k values)",
                        "elbow_silhouette_data.csv", key="dl_elbow_sil")

# --- Try the Model tab (the main, no-jargon way for ANYONE to use the AI) --
with tab_try:
    st.markdown("## 🧪 Try the Real AI Model — right here, free, no download, no code")
    st.success(
        "👋 **This works for anyone, whatever your background.** Just move the 5 sliders "
        "below. You're not looking at a demo or a mockup — these sliders are wired "
        "directly to the same trained model used everywhere else in this app."
    )

    default_row = row  # pre-fill with the currently selected pathogen's own scores
    st.caption("Each slider is a score from 0 (lowest) to 100 (highest). They're pre-filled "
               f"with **{default_row['name']}**'s own values — try moving them around.")
    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
    with sc1:
        in_V = st.slider("Virulence (V)", 0, 100, int(default_row["V"]),
                          help="How well this germ can invade the body and cause harm.")
    with sc2:
        in_A = st.slider("AMR (A)", 0, 100, int(default_row["A"]),
                          help="How hard this germ is to treat with common antibiotics.")
    with sc3:
        in_O = st.slider("Outbreak (O)", 0, 100, int(default_row["O"]),
                          help="How often this germ is linked to reported outbreaks.")
    with sc4:
        in_P = st.slider("Persistence (P)", 0, 100, int(default_row["P"]),
                          help="How long this germ survives on food or surfaces.")
    with sc5:
        in_D = st.slider("Severity (D)", 0, 100, int(default_row["D"]),
                          help="How serious the illness tends to be.")

    raw_input = np.array([[in_V, in_A, in_O, in_P, in_D]], dtype=float)
    scaled_input = scaler.transform(raw_input)  # the REAL fitted scaler

    st.markdown("### 🔮 Here's what the AI thinks")
    km_pred = int(km_model.predict(scaled_input)[0])  # the REAL fitted KMeans model
    pred_members = df[df["KMeans_Cluster"] == km_pred]
    pred_center = pred_members[["V", "A", "O", "P", "D"]].mean()
    pred_icon = CLUSTER_ICONS[km_pred % len(CLUSTER_ICONS)]
    pred_label, pred_summary = describe_cluster(pred_center, overall_means, pred_icon)
    st.success(f"{pred_icon} Your input belongs to the **“{pred_label}”** group")
    st.write(pred_summary)
    st.write(f"**Real pathogens already in this same group:** " + ", ".join(pred_members["name"]))

    dists = np.linalg.norm(Xs - scaled_input, axis=1)
    nearest_idx = int(np.argmin(dists))
    nearest_row = df.iloc[nearest_idx]
    st.info(f"🧭 Out of all 20 real pathogens, the one your input is **most similar to** "
            f"is **{nearest_row['name']}**.")

    with st.expander("🔧 I'm technical — show me what's actually happening under the hood"):
        st.write("**Step 1 — scaling:** the same `StandardScaler` fitted on all 20 pathogens "
                 "transforms your 5 raw numbers so they're comparable:")
        st.dataframe(
            pd.DataFrame({
                "Feature": ["V", "A", "O", "P", "D"],
                "Your input (0-100)": raw_input[0],
                "Scaled value (what the model actually sees)": scaled_input[0].round(3),
            }),
            hide_index=True, use_container_width=True,
        )
        st.write(f"**Step 2 — KMeans:** `km_model.predict()` (k={k}) assigns cluster "
                 f"**#{km_pred}** directly from the trained model object — not a lookup table.")
        st.write("**Step 3 — Hierarchical:** `AgglomerativeClustering` has no built-in way to "
                 "place a brand-new point (a real mathematical limitation, not a shortcut we "
                 f"took), so we find the nearest neighbor in real trained feature space: "
                 f"**{nearest_row['name']}** at distance **{dists[nearest_idx]:.3f}**, which "
                 f"sits in hierarchical cluster **#{int(nearest_row['Hierarchical_Cluster'])}**.")
        st.write(
            "**Proof this is real:** set every slider above to exactly match an existing "
            "pathogen's own V/A/O/P/D scores (see the **Compare All Pathogens** tab for the "
            "numbers) — the prediction will always match that pathogen's actual assigned "
            "cluster, because it's calling the identical fitted model, not a re-implementation."
        )
    st.caption("Want the full technical breakdown (model internals, downloadable files, "
               "code)? See the **🤖 Model Details** tab.")

# --- Model Details tab -----------------------------------------------------
with tab_model:
    st.info(
        "🎓 **In simple terms:** this app takes each germ's 5 risk scores, "
        "puts similar germs into the same group automatically (no human labeling), "
        "and shows you *why* it grouped them that way. For a plain-language "
        "explanation of what each group actually means, see the **🌐 Clustering** tab."
    )
    st.success(
        "🧪 **Want to try the model yourself first?** Head to the **Try the Model** tab — "
        "it's the same real trained model, with sliders, no jargon required. Everything "
        "below here is the deep technical detail, for research/coursework."
    )

    with st.expander("✅ Verify this is the real model (not a fake demo)"):
        st.write(
            "Set every slider in the **Try the Model** tab to exactly match an existing "
            "pathogen's own V/A/O/P/D scores (see the **Compare All Pathogens** tab for the "
            "numbers) — the KMeans prediction will always match that pathogen's actual "
            "assigned cluster, because it's calling the identical fitted model object, not "
            "because it's calling the identical fitted model object, not a re-implementation."
        )

    with st.expander("🔬 Full technical details (for research & coursework)"):
        st.subheader("Pipeline")
        st.markdown(
            "`Raw features (V, A, O, P, D)` → **StandardScaler** (zero mean / unit variance) "
            "→ **KMeans** *and* **AgglomerativeClustering (Ward linkage)** in parallel → "
            "**PCA (2 components)** for visualization only."
        )

        st.subheader("Feature scaling (StandardScaler)")
        scale_df = pd.DataFrame({
            "Feature": ["V", "A", "O", "P", "D"],
            "Mean (fit on data)": scaler.mean_.round(3),
            "Std. deviation": np.sqrt(scaler.var_).round(3),
        })
        st.dataframe(scale_df, hide_index=True, use_container_width=True)
        download_df_button(scale_df, "Feature scaling table", "scaler_mean_std.csv", key="dl_scale_df")

        st.subheader("K-Means model")
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"**Algorithm:** `sklearn.cluster.KMeans`")
            st.write(f"**n_clusters:** {km_model.n_clusters}")
            st.write(f"**n_init:** 10   **random_state:** 42")
            st.write(f"**Inertia (within-cluster SSE):** {km_model.inertia_:.3f}")
            st.write(f"**Silhouette score:** {sil:.3f}")
            st.write(f"**Iterations to converge:** {km_model.n_iter_}")
        with c2:
            centers = pd.DataFrame(
                scaler.inverse_transform(km_model.cluster_centers_),
                columns=["V", "A", "O", "P", "D"],
            ).round(1)
            centers.insert(0, "Cluster", [f"#{i}" for i in range(km_model.n_clusters)])
            st.markdown("**Cluster centers (unscaled, original 0–100 units):**")
            st.dataframe(centers, hide_index=True, use_container_width=True)
            download_df_button(centers, "Cluster centers table", "kmeans_cluster_centers.csv",
                                key="dl_centers")

        st.markdown("**Per-pathogen silhouette (fit quality of its own cluster assignment):**")
        sil_df = pd.DataFrame({
            "Bacteria": df["name"], "Cluster": df["KMeans_Cluster"],
            "Silhouette": sample_sil if sample_sil is not None else np.nan,
        }).sort_values("Silhouette")
        fig_sil = px.bar(sil_df, x="Silhouette", y="Bacteria", orientation="h",
                          color="Cluster", height=550)
        st.plotly_chart(fig_sil, use_container_width=True)
        download_chart_button(fig_sil, "silhouette chart", "silhouette_chart.png")
        download_df_button(sil_df, "Per-pathogen silhouette table", "silhouette_scores.csv",
                            key="dl_sil_df")

        st.subheader("Hierarchical Clustering model")
        st.write(f"**Algorithm:** `sklearn.cluster.AgglomerativeClustering`")
        st.write(f"**Linkage:** {hier_model.linkage}   **n_clusters:** {hier_model.n_clusters_}")
        st.write(f"**Distance metric:** Euclidean (on standardized features)")
        st.caption("The dendrogram in the Clustering tab is built from the same Ward-linkage "
                   "distance matrix (`scipy.cluster.hierarchy.linkage`).")

        st.subheader("PCA (used only for 2-D visualization, not for clustering itself)")
        var_df = pd.DataFrame({
            "Component": ["PC1", "PC2"],
            "Explained variance ratio": pca_model.explained_variance_ratio_.round(3),
        })
        st.dataframe(var_df, hide_index=True, use_container_width=True)
        download_df_button(var_df, "PCA explained variance", "pca_explained_variance.csv",
                            key="dl_var_df")
        loadings = pd.DataFrame(
            pca_model.components_.T, columns=["PC1", "PC2"], index=["V", "A", "O", "P", "D"]
        ).round(3)
        st.markdown("**PCA loadings** (how much each original feature contributes to PC1/PC2):")
        st.dataframe(loadings, use_container_width=True)
        download_df_button(loadings.reset_index(names="Feature"), "PCA loadings table",
                            "pca_loadings.csv", key="dl_loadings")

    st.success(
        "✅ **If you just played with the sliders above, you're already done.** "
        "You used the real model and got a real answer — nothing below this point "
        "is required for that. The rest of this section is only for people who want "
        "to keep using the model in their *own* code (developers, researchers, "
        "students continuing this project)."
    )

    with st.expander("🔧 For developers & researchers: download the trained model files"):
        st.subheader("Download trained models")
        import pickle, io, zipfile

        readme_text = f"""FoodSafe BioIntel — Trained Model Package
==========================================

This ZIP contains the ACTUAL trained machine-learning models from the
dashboard (not example code — the real fitted objects), saved with
Python's pickle format.

FILES INCLUDED
--------------
- kmeans_model.pkl        -> a fitted sklearn.cluster.KMeans object (k={k})
- hierarchical_model.pkl  -> a fitted sklearn.cluster.AgglomerativeClustering object
- scaler.pkl              -> the fitted StandardScaler used to normalize the data
- load_and_predict.py     -> a ready-to-run script showing how to use them

IMPORTANT: You CANNOT open .pkl files by double-clicking them.
They are not documents — they only work when loaded by Python code,
using the script below (load_and_predict.py).

HOW TO USE
----------
1. Install Python 3.9+ if you don't already have it: https://www.python.org
2. Open a terminal in the folder where you unzipped this package.
3. Install requirements:
       pip install scikit-learn numpy
4. Run the example script:
       python load_and_predict.py

That script loads all three files and predicts which cluster a NEW
pathogen would belong to, given its Virulence/AMR/Outbreak/Persistence/
Severity (V/A/O/P/D) scores — no retraining needed.

WHAT THE MODEL DOES
--------------------
The KMeans and Hierarchical models group foodborne pathogens into
{k} clusters of similar overall risk profile, based on 5 features:
Virulence (V), AMR (A), Outbreak frequency (O), Persistence (P), and
Disease Severity (D), each scored 0-100. The StandardScaler must
always be applied first, so new data is on the same scale the models
were trained on.

Generated by the FoodSafe BioIntel dashboard.
"""

        example_script = f"""\"\"\"
Example: load the trained FoodSafe BioIntel models and use them
on a NEW pathogen's scores, without retraining anything.
\"\"\"
import pickle

with open("scaler.pkl", "rb") as f:
    scaler = pickle.load(f)
with open("kmeans_model.pkl", "rb") as f:
    kmeans = pickle.load(f)
with open("hierarchical_model.pkl", "rb") as f:
    hierarchical = pickle.load(f)

# Replace these five numbers with a new pathogen's own scores (0-100 each):
# [Virulence, AMR, Outbreak, Persistence, Severity]
new_pathogen_scores = [[75, 60, 80, 65, 70]]

scaled = scaler.transform(new_pathogen_scores)
predicted_cluster = kmeans.predict(scaled)

print("This pathogen would be assigned to KMeans cluster:", predicted_cluster[0])
print("(Hierarchical clustering does not support predicting new points directly —")
print(" it only describes the grouping of the original {len(df)} pathogens it was fit on.)")
"""

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("kmeans_model.pkl", pickle.dumps(km_model))
            zf.writestr("hierarchical_model.pkl", pickle.dumps(hier_model))
            zf.writestr("scaler.pkl", pickle.dumps(scaler))
            zf.writestr("load_and_predict.py", example_script)
            zf.writestr("README.txt", readme_text)
        zip_buffer.seek(0)

        st.download_button(
            "📦 Download All Models (ZIP, with instructions)",
            data=zip_buffer.getvalue(),
            file_name="foodsafe_bioint_models.zip",
            mime="application/zip",
            use_container_width=True,
        )
        st.caption(
            "Recommended — includes all 3 trained models, a README, and a ready-to-run "
            "Python script, so you're not stuck with an unopenable .pkl file."
        )

        with st.expander("⬇️ Or download the individual files separately (even more advanced)"):
            st.warning(
                "⚠️ These `.pkl` files can't be opened by double-clicking — they only "
                "work when loaded with Python code (see the ZIP download above for a "
                "ready-made example script)."
            )
            dl1, dl2, dl3 = st.columns(3)
            with dl1:
                st.download_button("⬇️ KMeans model (.pkl)", data=pickle.dumps(km_model),
                                    file_name="kmeans_model.pkl")
            with dl2:
                st.download_button("⬇️ Hierarchical model (.pkl)", data=pickle.dumps(hier_model),
                                    file_name="hierarchical_model.pkl")
            with dl3:
                st.download_button("⬇️ StandardScaler (.pkl)", data=pickle.dumps(scaler),
                                    file_name="scaler.pkl")

            st.subheader("Reproducibility snippet")
            st.code(
                "from sklearn.preprocessing import StandardScaler\n"
                "from sklearn.cluster import KMeans, AgglomerativeClustering\n\n"
                "X = df[['V','A','O','P','D']].values\n"
                "Xs = StandardScaler().fit_transform(X)\n"
                f"km = KMeans(n_clusters={k}, n_init=10, random_state=42).fit(Xs)\n"
                f"hier = AgglomerativeClustering(n_clusters={k}, linkage='ward').fit(Xs)",
                language="python",
            )

# --- Manual & Sources tab ---------------------------------------------------
with tab_manual:
    st.header("📖 User Manual & Data Sources")
    st.caption("How this dashboard works, and exactly where every piece of data in it came from.")

    manual_tab, sources_tab = st.tabs(["🧭 Stepwise User Manual", "🗂️ Data Sources & References"])

    with manual_tab:
        st.subheader("How to use this dashboard, step by step")
        steps = [
            ("1. Welcome page",
             "You land here first. It explains why the project exists and who it helps "
             "(everyday people, food vendors, health workers, students/researchers). "
             "Click **🚀 Enter the System** to continue."),
            ("2. Find a pathogen — no name needed",
             "On the Symptom Check page, either: type a food or symptom in the box "
             "(e.g. 'chicken', 'diarrhea'), tap one of the common-symptom quick buttons, "
             "or click **Browse all 20 pathogens instead** to see everything."),
            ("3. Browse the results",
             "Matching pathogens appear as cards with their risk badge, main symptom, "
             "how soon symptoms usually appear, and FPRI score. Click **View Full "
             "Details →** on any card to open it."),
            ("4. Explore the seven detail tabs",
             "🍽️ Community Guide — plain-language symptoms/prevention by food category.\n\n"
             "📋 Overview — symptoms (mild→severe), onset time, food sources, detection, prevention.\n\n"
             "🧬 Genomics & Biology — genome stats, virulence factors, AMR profile, toxins.\n\n"
             "📊 FPRI Breakdown — the risk-score formula, radar chart, weighted components.\n\n"
             "🌐 Clustering — which group of similar pathogens this one belongs to, in plain language.\n\n"
             "⚖️ Compare All Pathogens — every pathogen ranked, full data table, elbow/silhouette charts.\n\n"
             "🤖 Model Details — the technical ML pipeline, PLUS the live 'Try the Model' sliders."),
            ("5. Try the trained model live",
             "In the Model Details tab, move the five sliders (Virulence, AMR, Outbreak, "
             "Persistence, Severity) to any values. The page instantly shows what the "
             "real trained StandardScaler, KMeans, and Hierarchical models output for "
             "that input — no download or coding needed."),
            ("6. Download the models (optional, for developers)",
             "Still in Model Details, the '📦 Download All Models' button gives you a ZIP "
             "with the actual trained .pkl files, a README, and a ready-to-run Python "
             "script — for anyone who wants to keep using the models outside this app."),
            ("7. Navigate anytime",
             "The sidebar always has: a dropdown to jump straight to another pathogen, "
             "a k-value slider to change how many clusters the model uses, and buttons "
             "to go back to Results, start a New search, or return to the Welcome page."),
        ]
        for title, body in steps:
            with st.container(border=True):
                st.markdown(f"**{title}**")
                st.write(body)

    with sources_tab:
        st.subheader("Where each category of data comes from")
        st.write(
            "This dashboard's curated database was assembled following the original "
            "project's data-collection plan, drawing each category of information from "
            "the standard public bioinformatics/public-health database for that category:"
        )
        source_table = pd.DataFrame({
            "Data category": ["Genome", "Virulence", "Antimicrobial Resistance (AMR)",
                               "Protein information", "Biological pathways",
                               "Food source & disease/epidemiology", "Symptom & onset literature",
                               "Detection & prevention practices"],
            "Source database": ["NCBI (Nucleotide/Genome)", "VFDB (Virulence Factor Database)",
                                 "CARD / AMRFinderPlus", "UniProt", "KEGG",
                                 "FDA / CDC / WHO / FAO", "PubMed", "FDA / CDC / WHO / FAO"],
        })
        st.dataframe(source_table, hide_index=True, use_container_width=True)
        download_df_button(source_table, "Data sources table", "data_sources.csv", key="dl_sources")

        st.subheader("Per-pathogen reference strain & accession")
        st.caption(
            "The exact reference genome each pathogen's genomic figures (genome size, "
            "GC content, gene inventory) are based on, with its NCBI accession number "
            "for independent verification."
        )
        ref_table = df[["name", "reference_strain", "ncbi_accession"]].rename(
            columns={"name": "Pathogen", "reference_strain": "Reference strain",
                     "ncbi_accession": "NCBI accession"}
        )
        st.dataframe(ref_table, hide_index=True, use_container_width=True)
        download_df_button(ref_table, "Reference strain & accession table", "reference_accessions.csv",
                            key="dl_ref_table")

        st.subheader("Limitations & honest caveats")
        st.warning(
            "- **FPRI is a provisional, proposed scoring model** built for this project — "
            "it is not a validated clinical or public-health index. The V/A/O/P/D scores "
            "are framework-testing values; production use would require deriving them "
            "directly from VFDB/CARD/genome analysis rather than curated estimates.\n\n"
            "- **Only 20 pathogens** are included — real-world foodborne illness involves "
            "many more organisms; this is a proof-of-concept, not an exhaustive database.\n\n"
            "- **Clustering is statistical, not diagnostic** — groupings reflect numeric "
            "similarity in the five FPRI features, not confirmed biological relatedness.\n\n"
            "- **This tool is educational**, not medical advice. Always consult a doctor, "
            "public-health authority, or food-safety regulator for real decisions."
        )
