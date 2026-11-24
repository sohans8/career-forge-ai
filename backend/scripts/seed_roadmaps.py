"""Builds backend/data/roadmaps_india.json, the Indian education knowledge graph.

The graph is the seed. The weekly watcher (update_education_data.py) stages
JSON patches against it, so individual nodes can change without a rewrite.
Salary ranges are indicative entry-to-mid-level figures in INR per annum and
must be re-verified against current sources.

Usage: python -m backend.scripts.seed_roadmaps [--force]
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
OUT = DATA_DIR / "roadmaps_india.json"
SCHEMA_VERSION = "1.0"
TODAY = date.today().isoformat()

NODES: list[dict] = []


def n(id, stage, title, duration, eligibility, exams, roles, nxt, salary, streams,
      summary, kind="path", college_type=None, branch_keywords=None, links=None):
    NODES.append({
        "id": id,
        "stage": stage,
        "kind": kind,
        "title": title,
        "summary": summary,
        "duration": duration,
        "eligibility": eligibility,
        "entrance_exams": exams,
        "top_branches_or_roles": roles,
        "next_nodes": nxt,
        "avg_salary_range": salary,
        "streams": streams,
        "college_type": college_type,
        "branch_keywords": branch_keywords or [],
        "official_links": links or [],
        "last_updated": TODAY,
    })


NA = "Not applicable (study track)"

# ----------------------------------------------------------------- AFTER 10th
n("a10_start", "after_10th", "After 10th: Choose Your Path", "-", "Passed Class 10 (SSC/CBSE/ICSE)", [],
  ["11th-12th (Science, Commerce, Arts)", "3-year Polytechnic Diploma", "ITI", "Vocational / skill tracks"],
  ["a10_sci_pcm", "a10_sci_pcb", "a10_commerce", "a10_arts", "a10_dip_cs", "a10_dip_it", "a10_dip_aiml",
   "a10_dip_mech", "a10_dip_civil", "a10_dip_ece", "a10_dip_elec", "a10_dip_pharm", "a10_iti", "a10_vocational"],
  NA, ["all"], "Every student starts here. Pick between academic (11th-12th), technical (Diploma/ITI) and skill routes.",
  kind="root")

n("a10_sci_pcm", "after_10th", "11th-12th Science (PCM)", "2 years", "Class 10 pass; Maths and Science recommended",
  ["JEE Main", "JEE Advanced", "MHT-CET", "Other state CETs", "BITSAT", "CUET-UG", "NDA"],
  ["B.E./B.Tech", "B.Sc (Physics/Maths/CS)", "B.Arch", "NDA/Defence", "Data Science", "AI/ML"],
  ["a12_btech", "a12_emerging", "a12_bsc", "a12_defence", "a12_design"], "Study track", ["science_pcm"],
  "Physics, Chemistry and Maths with an optional Computer Science or Biology subject. Main route to engineering.",
  links=["https://www.cbse.gov.in", "https://jeemain.nta.nic.in"])

n("a10_sci_pcb", "after_10th", "11th-12th Science (PCB)", "2 years", "Class 10 pass; Science recommended",
  ["NEET-UG", "CUET-UG", "State pharmacy/agri CETs"],
  ["MBBS", "BDS", "B.Pharm", "B.Sc Nursing", "BAMS/BHMS", "B.Sc Biotech"],
  ["a12_mbbs", "a12_pharm", "a12_bsc"], "Study track", ["science_pcb"],
  "Physics, Chemistry and Biology. Main route to medical, dental, pharmacy and life sciences.",
  links=["https://neet.nta.nic.in"])

n("a10_commerce", "after_10th", "11th-12th Commerce", "2 years", "Class 10 pass; Maths helpful for finance/economics",
  ["CUET-UG", "IPMAT", "CA Foundation", "CS Foundation (CSEET)", "CLAT"],
  ["B.Com", "BBA/BMS", "CA", "CS", "CMA", "Economics", "Law (BA LLB)"],
  ["a12_bcom", "a12_bba", "a12_ca", "a12_cs", "a12_law"], "Study track", ["commerce"],
  "Accountancy, Business Studies and Economics. Route to finance, management, CA/CS and law.",
  links=["https://www.icai.org", "https://www.icsi.edu"])

n("a10_arts", "after_10th", "11th-12th Arts / Humanities", "2 years", "Class 10 pass",
  ["CUET-UG", "CLAT", "UCEED/NID DAT", "NIFT", "State CETs"],
  ["BA", "Law", "Design", "Journalism/Mass Comm", "Civil Services (UPSC) base", "Psychology", "Hotel Mgmt"],
  ["a12_arts_ba", "a12_law", "a12_design"], "Study track", ["arts"],
  "History, Political Science, Economics, Psychology, Languages and more. Route to law, design, media and civil services.")

DIPLOMA_COMMON = dict(
    duration="3 years (6 semesters)",
    eligibility="Class 10 pass (Maths and Science required for most engineering diplomas)",
    exams=["State DTE / CAP admission (merit-based)", "Direct admission via polytechnic CAP rounds"],
    nxt=["ad_dse", "ad_ssc_je", "ad_rrb_je", "ad_state_je", "ad_industry", "ad_apprentice"],
)

for _id, title, roles, salary, keys, summ in [
    ("a10_dip_cs", "Diploma in Computer Engineering", ["Junior Developer", "Web Developer", "Software Tester", "IT Support"],
     "INR 2.4-5 LPA entry", ["COMPUTER"], "Programming, DBMS, web, networking. Strong DSE route to B.Tech CSE."),
    ("a10_dip_it", "Diploma in Information Technology", ["Web Developer", "Network Technician", "Database Assistant", "QA Tester"],
     "INR 2.4-5 LPA entry", ["INFORMATION TECHNOLOGY"], "Web technologies, networking and software basics."),
    ("a10_dip_aiml", "Diploma in AI & Machine Learning / Data Science", ["Junior ML Technician", "Data Annotator/Analyst", "Python Developer"],
     "INR 2.4-5 LPA entry", ["ARTIFICIAL", "MACHINE LEARNING", "DATA SCIENCE"],
     "Newer AICTE-approved branch at selected polytechnics. Check that your target institute offers it."),
    ("a10_dip_mech", "Diploma in Mechanical Engineering", ["Production Technician", "CAD Designer", "Maintenance Engineer (Jr)", "Quality Inspector"],
     "INR 2.4-4.5 LPA entry", ["MECHANICAL"], "Manufacturing, thermal, design and CAD/CAM."),
    ("a10_dip_civil", "Diploma in Civil Engineering", ["Site Supervisor", "Draftsman", "Junior Engineer (PWD)", "Quantity Surveyor"],
     "INR 2.4-4.5 LPA entry", ["CIVIL"], "Construction, surveying, estimation. Large state and central JE demand."),
    ("a10_dip_ece", "Diploma in Electronics & Telecommunication", ["Electronics Technician", "Embedded Support", "Telecom Technician"],
     "INR 2.4-4.8 LPA entry", ["ELECTRONICS", "TELECOMMUNICATION"], "Circuits, embedded systems, communication."),
    ("a10_dip_elec", "Diploma in Electrical Engineering", ["Electrical Technician", "Substation Operator", "Junior Engineer (Electrical)"],
     "INR 2.4-4.8 LPA entry", ["ELECTRICAL"], "Power systems, machines and controls. Strong PSU/State board JE demand."),
]:
    n(_id, "after_10th", title, DIPLOMA_COMMON["duration"], DIPLOMA_COMMON["eligibility"], DIPLOMA_COMMON["exams"],
      roles, DIPLOMA_COMMON["nxt"], salary, ["diploma", _id.replace("a10_", "")], summ,
      college_type="diploma", branch_keywords=keys,
      links=["https://www.aicte-india.org", "https://dte.maharashtra.gov.in"])

n("a10_dip_pharm", "after_10th", "Diploma in Pharmacy (D.Pharm)", "2 years", "Class 12 Science (PCB/PCM) generally required",
  ["State D.Pharm CET/merit"], ["Pharmacist", "Medical Store Owner", "Pharma Sales"], ["a12_pharm"],
  "INR 2-4 LPA entry", ["diploma", "dip_pharm", "science_pcb"],
  "Regulated by the Pharmacy Council of India. Eligibility starts after 12th in most states; listed here for completeness.",
  # Pharmacy institutions are approved by PCI, not AICTE, so the AICTE college list has none.
  links=["https://www.pci.nic.in"])

n("a10_iti", "after_10th", "ITI (Industrial Training Institute)", "6 months - 2 years", "Class 8-10 pass depending on trade",
  ["State ITI admission (merit)", "NCVT/SCVT trade tests"],
  ["Electrician", "Fitter", "Welder", "COPA (computer operator)", "Mechanic (Motor Vehicle)", "Plumber"],
  ["ad_apprentice", "ad_industry", "ad_dse", "a10_vocational"], "INR 1.8-3.6 LPA entry", ["iti", "vocational"],
  "Hands-on trade training under DGT. NCVT certificate leads to apprenticeships and government technician jobs. Some states allow lateral entry to diploma.",
  links=["https://dgt.gov.in"])

n("a10_vocational", "after_10th", "Vocational & Skill Tracks (NSQF / Skill India)", "3 months - 2 years", "Class 8-10 pass depending on programme",
  ["Programme-specific assessment (Sector Skill Councils)"],
  ["Retail/BFSI associate", "Electronics repair", "Beauty/Wellness", "IT-ITeS associate", "Healthcare assistant", "Digital marketing"],
  ["ad_apprentice", "ad_industry"], "INR 1.5-3.5 LPA entry", ["vocational", "iti"],
  "NSQF-aligned short courses (PMKVY, NAPS, Sector Skill Councils). Fast route to jobs and apprenticeships.",
  links=["https://www.skillindiadigital.gov.in"])

# ---------------------------------------------------------------- AFTER 12th
n("a12_start", "after_12th", "After 12th: Choose Your Degree", "-", "Passed Class 12", [],
  ["Engineering", "Medical", "Commerce & Finance", "Arts, Law & Design", "Emerging tech degrees", "Defence"],
  ["a12_btech", "a12_emerging", "a12_mbbs", "a12_pharm", "a12_bcom", "a12_bba", "a12_ca", "a12_cs", "a12_law",
   "a12_design", "a12_arts_ba", "a12_bsc", "a12_defence"], NA, ["all"],
  "Your options depend on the Class 12 stream. Pick a stream to filter.", kind="root")

n("a12_btech", "after_12th", "B.E. / B.Tech (Engineering)", "4 years",
  "Class 12 PCM with minimum aggregate set by the counselling authority (commonly 45-50%, relaxations for reserved categories)",
  ["JEE Main (NTA)", "JEE Advanced (IITs)", "MHT-CET (Maharashtra)", "Other state CETs", "BITSAT", "VITEEE"],
  ["Computer Science/IT", "AI & Data Science", "Electronics & Communication", "Mechanical", "Civil", "Electrical"],
  ["ad_industry", "a12_mtech"], "INR 4-12 LPA fresher (varies widely by college)", ["science_pcm", "engineering"],
  "Admission via JoSAA/CSAB (central) or state CAP rounds. Seats are filled by rank, branch and category.",
  college_type="engineering", branch_keywords=["COMPUTER", "INFORMATION TECHNOLOGY", "ELECTRONICS", "MECHANICAL", "CIVIL", "ELECTRICAL"],
  links=["https://jeemain.nta.nic.in", "https://cetcell.mahacet.org", "https://josaa.nic.in"])

n("a12_mtech", "after_12th", "M.Tech / MBA / Higher Studies (via GATE/CAT)", "2 years", "B.E./B.Tech degree",
  ["GATE", "CAT", "State PGCET"], ["R&D Engineer", "Professor", "PSU via GATE", "Manager"], [],
  "INR 6-18 LPA", ["science_pcm", "engineering"], "Postgraduate route after engineering. GATE scores are also used for PSU recruitment.")

n("a12_emerging", "after_12th", "Emerging-Tech Degrees (AI/ML, Data Science, Cyber Security, Robotics)", "4 years",
  "Class 12 PCM (Maths required)", ["JEE Main", "State CETs", "University entrance tests (VITEEE, SRMJEEE etc.)"],
  ["ML Engineer", "Data Scientist", "Cyber Security Analyst", "Robotics Engineer", "IoT Engineer"],
  ["ad_industry"], "INR 5-15 LPA fresher", ["science_pcm", "engineering", "emerging"],
  "Specialised B.Tech branches in AI & ML, Data Science, Cyber Security and similar. Check AICTE approval and placement record.",
  college_type="engineering", branch_keywords=["ARTIFICIAL", "MACHINE LEARNING", "DATA SCIENCE", "CYBER", "ROBOTICS", "INTERNET OF THINGS"])

n("a12_mbbs", "after_12th", "MBBS / BDS (Medical & Dental)", "5.5 years (MBBS incl. internship), 5 years (BDS)",
  "Class 12 PCB with minimum 50% (General); NEET-UG qualified", ["NEET-UG (NTA)", "MCC counselling", "State counselling"],
  ["Doctor (MBBS)", "Dentist (BDS)", "Specialist after NEET-PG"], [], "INR 6-15 LPA (varies widely)",
  ["science_pcb", "medical"], "Admission only through NEET-UG merit and MCC/state counselling.",
  links=["https://neet.nta.nic.in", "https://mcc.nic.in"])

n("a12_pharm", "after_12th", "B.Pharm / Allied Health / B.Sc Nursing", "3-4 years", "Class 12 PCB or PCM (pharmacy), PCB (nursing)",
  ["State pharmacy CET", "NEET (some programmes)", "University entrance"], ["Pharmacist", "Drug Inspector", "Clinical Research", "Nurse"],
  [], "INR 3-7 LPA entry", ["science_pcb", "medical", "dip_pharm"], "Regulated by PCI and INC. Diploma holders may enter B.Pharm lateral (2nd year) in many states.",
  links=["https://www.pci.nic.in", "https://www.indiannursingcouncil.org"])

n("a12_bcom", "after_12th", "B.Com / B.Com (Hons)", "3-4 years", "Class 12 any stream (Commerce preferred)",
  ["CUET-UG", "University merit"], ["Accountant", "Tax Consultant", "Bank PO/Clerk", "Financial Analyst"],
  ["a12_ca", "a12_cs"], "INR 2.5-6 LPA entry", ["commerce", "arts"], "Core degree for finance, banking and accounting.")

n("a12_bba", "after_12th", "BBA / BMS / Integrated MBA", "3-5 years", "Class 12 any stream",
  ["CUET-UG", "IPMAT", "NPAT", "SET", "University tests"], ["Business Analyst", "Marketing Executive", "HR Executive", "Entrepreneur"],
  [], "INR 3-8 LPA entry", ["commerce", "arts", "science_pcm"], "Management foundation, often followed by MBA via CAT/CMAT.")

n("a12_ca", "after_12th", "Chartered Accountancy (CA)", "4.5-5 years", "Class 12 pass; register for Foundation after Class 12 (ICAI)",
  ["CA Foundation", "CA Intermediate", "CA Final (ICAI)"], ["Chartered Accountant", "Auditor", "Tax Advisor", "CFO track"], [],
  "INR 7-12 LPA at qualification", ["commerce"], "Conducted by ICAI. Attempt schedule and rules are updated periodically.",
  links=["https://www.icai.org"])

n("a12_cs", "after_12th", "Company Secretary (CS)", "3-4 years", "Class 12 pass; CSEET (ICSI)",
  ["CSEET", "CS Executive", "CS Professional"], ["Company Secretary", "Compliance Officer", "Legal Advisor"], [],
  "INR 5-10 LPA", ["commerce", "arts"], "Conducted by ICSI.", links=["https://www.icsi.edu"])

n("a12_law", "after_12th", "Law (BA LLB / BBA LLB / B.Com LLB)", "5 years", "Class 12 any stream with minimum 45-50%",
  ["CLAT (NLUs)", "AILET", "LSAT-India", "University entrance"], ["Advocate", "Corporate Counsel", "Judiciary (after LLB)", "Legal Analyst"],
  [], "INR 4-14 LPA (varies widely)", ["arts", "commerce", "science_pcm", "science_pcb"],
  "Bar Council of India approval is required for the law college.", links=["https://consortiumofnlus.ac.in"])

n("a12_design", "after_12th", "Design / Architecture (B.Des, B.Arch, NIFT)", "4-5 years",
  "Class 12 any stream (B.Arch needs PCM and NATA/JEE Paper 2)", ["UCEED", "NID DAT", "NIFT", "NATA", "JEE Main Paper 2"],
  ["UI/UX Designer", "Architect", "Fashion Designer", "Product Designer"], [], "INR 3-10 LPA", ["arts", "science_pcm", "commerce"],
  "Portfolio and aptitude-based admissions.")

n("a12_arts_ba", "after_12th", "BA / B.Sc / Mass Communication / Civil Services base", "3 years", "Class 12 any stream",
  ["CUET-UG", "University merit"], ["Teacher", "Journalist", "Psychologist", "UPSC/State PSC aspirant", "Content Strategist"], [],
  "INR 2.5-6 LPA entry", ["arts", "commerce"], "Broad degrees with CUET-based central university admissions.")

n("a12_bsc", "after_12th", "B.Sc (Physics, Chemistry, Maths, CS, Biotech, Data Science)", "3-4 years (NEP: 4-year honours)",
  "Class 12 Science", ["CUET-UG", "University entrance"], ["Research Associate", "Data Analyst", "Lab Scientist", "Teacher"],
  [], "INR 3-7 LPA entry", ["science_pcm", "science_pcb"], "NEP 2020 allows multiple entry/exit and a 4-year honours option.")

n("a12_defence", "after_12th", "Defence (NDA / CDS / Technical Entry)", "3-4 years training", "Class 12 PCM for Army/Navy/AF technical; unmarried, age limits apply",
  ["NDA (UPSC)", "CDS (UPSC)", "TES (JEE Main based)", "SSB interview"], ["Army/Navy/Air Force Officer"], [],
  "Officer pay scale (level 10 and above)", ["science_pcm", "arts", "commerce"],
  "Selection via UPSC and SSB. Check UPSC for current age and eligibility rules.", links=["https://upsc.gov.in"])

# ------------------------------------------------------------- AFTER DIPLOMA
n("ad_start", "after_diploma", "After Diploma: Choose Your Route", "-", "Passed 3-year Diploma (any engineering branch)", [],
  ["Direct Second Year (DSE) B.E./B.Tech", "SSC JE / RRB JE", "State JE", "Industry job", "Apprenticeship"],
  ["ad_dse", "ad_ssc_je", "ad_rrb_je", "ad_state_je", "ad_industry", "ad_apprentice"], NA, ["all"],
  "A diploma is a complete qualification. You can work, apply to government JE posts or continue to a degree.", kind="root")

n("ad_dse", "after_diploma", "Direct Second Year (DSE) B.E./B.Tech", "3 years", "Passed 3-year diploma in a relevant branch; minimum marks set by the state (commonly 45-50%)",
  ["State DSE CAP (e.g. Maharashtra DSE via CET Cell)", "Merit-based on diploma marks", "Some states: ECET (Telangana/AP), LEET (Gujarat/Rajasthan)"],
  ["B.Tech CSE/IT", "Mechanical", "Civil", "Electrical", "Electronics"], ["ad_industry", "a12_mtech"],
  "INR 4-10 LPA fresher", ["diploma", "engineering"],
  "Lateral entry into 2nd year of B.E./B.Tech. Counselling and cut-offs are state-specific.",
  college_type="engineering", branch_keywords=["COMPUTER", "INFORMATION TECHNOLOGY", "MECHANICAL", "CIVIL", "ELECTRICAL", "ELECTRONICS"],
  links=["https://cetcell.mahacet.org", "https://www.aicte-india.org"])

n("ad_ssc_je", "after_diploma", "SSC JE (Junior Engineer)", "Exam cycle ~1 year", "Diploma in Civil/Mechanical/Electrical (age limit as per notification)",
  ["SSC JE Paper I and II (SSC)"], ["JE Civil/Mech/Electrical in CPWD, MES, CWC, etc."], ["ad_industry"],
  "Pay Level 6 (approx INR 35,400-1,12,400 base scale)", ["diploma", "dip_civil", "dip_mech", "dip_elec"],
  "Central government JE recruitment. Check SSC notification for current eligibility and syllabus.", links=["https://ssc.gov.in"])

n("ad_rrb_je", "after_diploma", "RRB JE (Railways Junior Engineer)", "Exam cycle ~1 year", "Diploma in relevant branch (age limit per notification)",
  ["RRB JE CBT-1, CBT-2 (RRB)"], ["Railways JE (Civil, Mech, Elec, Electronics, IT)"], ["ad_industry"],
  "Pay Level 6 (approx INR 35,400 base)", ["diploma", "dip_civil", "dip_mech", "dip_elec", "dip_ece", "dip_cs", "dip_it"],
  "Indian Railways recruitment via RRBs.", links=["https://indianrailways.gov.in"])

n("ad_state_je", "after_diploma", "State JE & PSU Jobs (MSEB, PWD, MPSC etc.)", "Exam cycle ~1 year", "Diploma in relevant branch",
  ["State PSC / Board exams", "PSU-specific written tests"], ["JE (PWD/Irrigation/Electricity Board)", "PSU Diploma Trainee"], ["ad_industry"],
  "INR 3.5-7 LPA", ["diploma", "dip_civil", "dip_mech", "dip_elec", "dip_ece"], "State and PSU openings follow separate notifications.")

n("ad_industry", "after_diploma", "Direct Industry Entry / Private Sector", "-", "Diploma or ITI or degree",
  ["Company tests and interviews", "Campus placements"], ["Technician", "Junior Developer", "Site Supervisor", "QA Engineer"], [],
  "INR 2.4-6 LPA entry", ["all"], "Build projects and certifications to move ahead faster. Combine with part-time degree via DSE if desired.")

n("ad_apprentice", "after_diploma", "Apprenticeship (NAPS / NATS)", "1-3 years", "Diploma, ITI or vocational certificate",
  ["Company selection via NATS/NAPS portals"], ["Graduate/Technician Apprentice"], ["ad_industry"],
  "Stipend INR 8,000-15,000 per month (varies)", ["diploma", "iti", "vocational"],
  "Paid on-the-job training with government stipend support.", links=["https://nats.education.gov.in", "https://www.apprenticeshipindia.gov.in"])


def build() -> dict:
    ids = {x["id"] for x in NODES}
    for node in NODES:
        for t in node["next_nodes"]:
            assert t in ids, f"{node['id']} -> unknown {t}"
    return {
        "schema_version": SCHEMA_VERSION,
        "last_updated": TODAY,
        "disclaimer": "Indicative data. Always verify eligibility, dates and fees on the official portal.",
        "stages": {
            "after_10th": {"label": "After 10th", "root": "a10_start"},
            "after_12th": {"label": "After 12th", "root": "a12_start"},
            "after_diploma": {"label": "After Diploma (DSE & Jobs)", "root": "ad_start"},
        },
        "nodes": NODES,
    }


def main(force: bool = False) -> Path:
    if OUT.exists() and not force:
        print(f"[skip] {OUT.name} exists (use --force to regenerate)")
        return OUT
    OUT.write_text(json.dumps(build(), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[ok] wrote {OUT} ({len(NODES)} nodes)")
    return OUT


if __name__ == "__main__":
    main("--force" in sys.argv)
