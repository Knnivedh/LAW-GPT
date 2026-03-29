"""
DOMAIN SPECIALIST PROFILES — 10x Legal Precision Engine
=========================================================
Maps each legal category to a comprehensive domain profile that drives:
  - Planner: domain-locked planning directives
  - Retriever: domain-boosted queries + boost filtering (80/20)
  - Synthesizer: domain-specialist persona injection
  - Verifier: domain-specific quality checks

Design choices:
  - DEFAULT: auto-detect domain from query text (no user action needed)
  - MANUAL OVERRIDE: if the user selects a category, it overrides auto-detection
  - Offense categories (Murder, Rape, Fraud, Terrorism, Corruption) are mapped
    to Criminal Law as parent domain but carry offense-specific guidance
  - Boost approach: domain docs get 80% weight, cross-domain 20% (never hard-block)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import re
import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA CLASS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DomainProfile:
    """Complete specialist profile for a legal domain."""

    # Identity
    domain_id: str                    # Internal key (e.g. "criminal_law")
    display_name: str                 # UI label (e.g. "Criminal Law")
    parent_domain: Optional[str]      # For offenses → parent domain (e.g. "criminal_law")

    # Expert persona — injected into synthesizer system prompt
    expert_persona: str

    # Core statutes — the acts/sections an expert in this domain MUST know
    core_statutes: List[str]

    # Key precedents — landmark cases that define this domain
    key_precedents: List[str]

    # Query boost keywords — injected into retrieval queries for domain-focus
    query_boost_keywords: List[str]

    # Filter keywords — used for retrieval result scoring/boosting
    filter_keywords: List[str]

    # Verification checklist — what a good answer MUST contain
    verification_checklist: List[str]

    # Domain-specific synthesis instructions (appended to system prompt)
    synthesis_instructions: str = ""

    # Auto-detect trigger keywords — if these appear in query, auto-assign this domain
    auto_detect_keywords: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
#  DOMAIN PROFILES — All 14 categories from CategoryFilter.jsx
# ═══════════════════════════════════════════════════════════════════════════════

DOMAIN_PROFILES: Dict[str, DomainProfile] = {}


def _register(profile: DomainProfile) -> None:
    """Register a profile by its domain_id and display_name."""
    DOMAIN_PROFILES[profile.domain_id] = profile
    DOMAIN_PROFILES[profile.display_name.lower()] = profile


# ─────────────────────────────────────────────────────────────────────────────
#  1. CRIMINAL LAW
# ─────────────────────────────────────────────────────────────────────────────
_register(DomainProfile(
    domain_id="criminal_law",
    display_name="Criminal Law",
    parent_domain=None,
    expert_persona=(
        "a Senior Criminal Law Advocate with 25+ years of practice before the Supreme Court "
        "and High Courts of India, specialising in IPC/BNS offenses, CrPC/BNSS procedure, "
        "bail jurisprudence, criminal trials, and appellate practice"
    ),
    core_statutes=[
        "Indian Penal Code, 1860 (IPC) / Bharatiya Nyaya Sanhita, 2023 (BNS)",
        "Code of Criminal Procedure, 1973 (CrPC) / Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)",
        "Indian Evidence Act, 1872 / Bharatiya Sakshya Adhiniyam, 2023 (BSA)",
        "Prevention of Corruption Act, 1988",
        "Narcotic Drugs and Psychotropic Substances Act, 1985 (NDPS)",
        "Arms Act, 1959",
        "SC/ST (Prevention of Atrocities) Act, 1989",
        "POCSO Act, 2012",
    ],
    key_precedents=[
        "Arnesh Kumar v. State of Bihar (2014) — Guidelines on arrest under Section 498A",
        "Lalita Kumari v. Govt. of UP (2014) — Mandatory FIR registration",
        "Siddharth v. State of UP (2021) — Anticipatory bail principles",
        "Dataram Singh v. State of UP (2018) — Bail is the rule, jail is exception",
        "Maneka Gandhi v. Union of India (1978) — Right to life includes fair procedure",
        "K.S. Puttaswamy v. Union of India (2017) — Privacy as fundamental right",
        "Kedar Nath Singh v. State of Bihar (1962) — Sedition interpretation",
    ],
    query_boost_keywords=[
        "IPC", "BNS", "CrPC", "BNSS", "criminal offense", "punishment",
        "bail", "FIR", "arrest", "charge sheet", "trial", "cognizable",
        "bailable", "non-bailable", "mens rea", "actus reus",
    ],
    filter_keywords=[
        "ipc", "bns", "crpc", "bnss", "criminal", "offense", "offence",
        "punishment", "bail", "fir", "arrest", "charge", "trial",
        "penal", "crime", "accused", "prosecution", "conviction",
        "acquittal", "sentence", "imprisonment", "cognizable",
    ],
    verification_checklist=[
        "Does the answer cite specific IPC/BNS section numbers?",
        "Does the answer classify the offense (cognizable/non-cognizable, bailable/non-bailable)?",
        "Does the answer mention applicable punishment range?",
        "Does the answer reference at least 1 landmark criminal case?",
        "Is the answer focused on criminal law, not civil remedies?",
    ],
    synthesis_instructions=(
        "MANDATORY for Criminal Law responses:\n"
        "1. ALWAYS state the exact IPC/BNS section number and its ingredients (actus reus + mens rea)\n"
        "2. Classify offense: Cognizable/Non-Cognizable, Bailable/Non-Bailable\n"
        "3. State punishment range (minimum and maximum)\n"
        "4. Reference the new BNS equivalent if citing old IPC sections\n"
        "5. Discuss procedural aspects under CrPC/BNSS (FIR, investigation, trial)\n"
    ),
    auto_detect_keywords=[
        "criminal", "crime", "offense", "offence", "ipc", "bns", "crpc", "bnss",
        "fir", "bail", "arrest", "charge", "prosecution", "accused", "conviction",
        "penal", "punishment", "imprisonment", "cognizable", "bailable",
        "police", "investigation", "trial court",
    ],
))

# ─────────────────────────────────────────────────────────────────────────────
#  2. PROPERTY LAW
# ─────────────────────────────────────────────────────────────────────────────
_register(DomainProfile(
    domain_id="property_law",
    display_name="Property Law",
    parent_domain=None,
    expert_persona=(
        "a Senior Property Law Advocate specialising in real estate law, land acquisition, "
        "transfer of property, registration, RERA compliance, succession of immovable property, "
        "and tenancy disputes across India"
    ),
    core_statutes=[
        "Transfer of Property Act, 1882 (TPA)",
        "Registration Act, 1908",
        "Indian Stamp Act, 1899",
        "Real Estate (Regulation and Development) Act, 2016 (RERA)",
        "Specific Relief Act, 1963",
        "Land Acquisition Act, 2013 (RFCTLARR)",
        "Indian Easements Act, 1882",
        "Benami Transactions (Prohibition) Act, 1988",
        "Hindu Succession Act, 1956 (for property succession)",
    ],
    key_precedents=[
        "Suraj Lamp & Industries v. State of Haryana (2012) — Ban on GPA/SA/Will sales",
        "Indore Development Authority v. Shailendra (2018) — Land acquisition compensation",
        "S.P. Chengalvaraya Naidu v. Jagannath (1994) — Fraud vitiates all transactions",
        "Kaliammal v. Saroja (2020) — Partition of property rights",
        "Vidya Devi v. State of HP (2020) — Adverse possession essentials",
    ],
    query_boost_keywords=[
        "property", "land", "real estate", "RERA", "transfer", "registration",
        "sale deed", "mutation", "possession", "easement", "tenancy", "lease",
        "succession", "partition", "ancestral property", "joint family",
    ],
    filter_keywords=[
        "property", "land", "real estate", "rera", "transfer", "registration",
        "deed", "mutation", "possession", "easement", "tenant", "lease",
        "succession", "partition", "ancestral", "immovable", "conveyance",
        "stamp duty", "encumbrance", "title", "ownership",
    ],
    verification_checklist=[
        "Does the answer cite TPA, Registration Act, or RERA provisions?",
        "Does the answer distinguish between movable and immovable property?",
        "Does the answer address registration/stamp duty requirements?",
        "Does the answer reference relevant property law precedents?",
    ],
    synthesis_instructions=(
        "MANDATORY for Property Law responses:\n"
        "1. Cite specific sections of TPA, Registration Act, or RERA\n"
        "2. Distinguish between sale, mortgage, lease, gift, and exchange\n"
        "3. Address registration and stamp duty requirements\n"
        "4. Discuss title verification and encumbrance certificate if relevant\n"
        "5. Note state-specific variations in land laws if applicable\n"
    ),
    auto_detect_keywords=[
        "property", "land", "real estate", "rera", "plot", "flat", "apartment",
        "sale deed", "registration", "mutation", "possession", "tenant",
        "lease", "rent", "builder", "developer", "stamp duty", "encumbrance",
        "title deed", "conveyance", "ancestral property", "partition",
        "immovable", "construction", "housing",
    ],
))

# ─────────────────────────────────────────────────────────────────────────────
#  3. FAMILY LAW
# ─────────────────────────────────────────────────────────────────────────────
_register(DomainProfile(
    domain_id="family_law",
    display_name="Family Law",
    parent_domain=None,
    expert_persona=(
        "a Senior Family Law Advocate specialising in matrimonial disputes, divorce, "
        "child custody, maintenance, succession, adoption, and domestic violence across "
        "Hindu, Muslim, Christian, and Special Marriage Act jurisdictions"
    ),
    core_statutes=[
        "Hindu Marriage Act, 1955 (HMA)",
        "Hindu Succession Act, 1956 (HSA)",
        "Special Marriage Act, 1954",
        "Hindu Minority and Guardianship Act, 1956",
        "Hindu Adoptions and Maintenance Act, 1956",
        "Protection of Women from Domestic Violence Act, 2005 (PWDVA)",
        "Dowry Prohibition Act, 1961",
        "Muslim Personal Law (Shariat)",
        "Indian Divorce Act, 1869 (Christians)",
        "Guardians and Wards Act, 1890",
        "Family Courts Act, 1984",
    ],
    key_precedents=[
        "Shayara Bano v. Union of India (2017) — Triple talaq unconstitutional",
        "V. Bhagat v. D. Bhagat (1994) — Mental cruelty in divorce",
        "Rajnesh v. Neha (2020) — Maintenance quantification guidelines",
        "Vineeta Sharma v. Rakesh Sharma (2020) — Coparcenary rights of daughters",
        "Indra Sarma v. V.K.V. Sarma (2013) — Live-in relationship and DV Act",
    ],
    query_boost_keywords=[
        "marriage", "divorce", "custody", "maintenance", "alimony", "dowry",
        "domestic violence", "succession", "adoption", "guardianship",
        "matrimonial", "husband", "wife", "family court",
    ],
    filter_keywords=[
        "marriage", "divorce", "custody", "maintenance", "alimony", "dowry",
        "domestic violence", "succession", "adoption", "guardianship",
        "matrimonial", "husband", "wife", "family", "child", "minor",
        "hindu", "muslim", "christian", "parsi", "wedding", "conjugal",
    ],
    verification_checklist=[
        "Does the answer cite the correct personal law (Hindu/Muslim/Christian/Special)?",
        "Does the answer reference Family Courts Act jurisdiction?",
        "Does the answer distinguish between divorce grounds under different acts?",
        "Does the answer address maintenance/alimony computation if relevant?",
    ],
    synthesis_instructions=(
        "MANDATORY for Family Law responses:\n"
        "1. Identify the applicable personal law (Hindu/Muslim/Christian/Special Marriage Act)\n"
        "2. Cite specific sections of the governing act\n"
        "3. Address jurisdiction (Family Court / District Court)\n"
        "4. Discuss grounds for relief specific to the personal law\n"
        "5. Address maintenance, custody, and property rights as applicable\n"
    ),
    auto_detect_keywords=[
        "marriage", "divorce", "custody", "maintenance", "alimony", "dowry",
        "domestic violence", "succession", "adoption", "guardianship",
        "matrimonial", "husband", "wife", "family court", "cruelty",
        "desertion", "restitution", "conjugal", "wedding", "stridhan",
        "coparcenary", "daughter's share", "498a",
    ],
))

# ─────────────────────────────────────────────────────────────────────────────
#  4. CONSUMER LAW
# ─────────────────────────────────────────────────────────────────────────────
_register(DomainProfile(
    domain_id="consumer_law",
    display_name="Consumer Law",
    parent_domain=None,
    expert_persona=(
        "a Senior Consumer Law Advocate specialising in Consumer Protection Act 2019, "
        "product liability, service deficiency, unfair trade practices, e-commerce disputes, "
        "and consumer commission practice"
    ),
    core_statutes=[
        "Consumer Protection Act, 2019 (CPA 2019)",
        "Consumer Protection (E-Commerce) Rules, 2020",
        "Legal Metrology Act, 2009",
        "Food Safety and Standards Act, 2006 (FSSAI)",
        "Bureau of Indian Standards Act, 2016",
    ],
    key_precedents=[
        "Indian Medical Association v. VP Shantha (1995) — Medical services are 'services' under CPA",
        "Lucknow Development Authority v. MK Gupta (1994) — Housing as service",
        "Nizam Institute v. Prasad Rao (2009) — Medical negligence standards",
        "Ambrish Kumar Shukla v. Ferrero Rocher (2015) — Misleading advertisements",
    ],
    query_boost_keywords=[
        "consumer", "deficiency", "defect", "refund", "replacement", "complaint",
        "consumer commission", "product liability", "unfair trade practice",
        "misleading advertisement", "warranty", "guarantee",
    ],
    filter_keywords=[
        "consumer", "deficiency", "defect", "refund", "replacement", "complaint",
        "product", "service", "warranty", "guarantee", "commission",
        "e-commerce", "online purchase", "delivery", "seller", "manufacturer",
    ],
    verification_checklist=[
        "Does the answer cite CPA 2019 sections (not old 1986 Act)?",
        "Does the answer identify the correct forum (District/State/National Commission)?",
        "Does the answer address pecuniary jurisdiction limits?",
        "Does the answer distinguish between defect and deficiency?",
    ],
    synthesis_instructions=(
        "MANDATORY for Consumer Law responses:\n"
        "1. Cite CPA 2019 sections (NOT the old 1986 Act)\n"
        "2. Identify correct forum based on value of goods/services\n"
        "3. Distinguish between 'defect in goods' and 'deficiency in service'\n"
        "4. Address product liability provisions if relevant\n"
        "5. Note time limitation for filing complaint (2 years from cause of action)\n"
    ),
    auto_detect_keywords=[
        "consumer", "refund", "defective", "deficiency", "product", "warranty",
        "consumer commission", "complaint", "seller", "e-commerce", "online",
        "delivery", "replacement", "misleading", "advertisement", "service",
        "purchase", "manufacturer", "guarantee",
    ],
))

# ─────────────────────────────────────────────────────────────────────────────
#  5. CORPORATE LAW
# ─────────────────────────────────────────────────────────────────────────────
_register(DomainProfile(
    domain_id="corporate_law",
    display_name="Corporate Law",
    parent_domain=None,
    expert_persona=(
        "a Senior Corporate Law Counsel specialising in Companies Act 2013, SEBI regulations, "
        "mergers & acquisitions, corporate governance, insolvency & bankruptcy, "
        "and NCLT/NCLAT practice"
    ),
    core_statutes=[
        "Companies Act, 2013",
        "Insolvency and Bankruptcy Code, 2016 (IBC)",
        "SEBI Act, 1992 and SEBI Regulations",
        "Competition Act, 2002",
        "Limited Liability Partnership Act, 2008 (LLP Act)",
        "Indian Partnership Act, 1932",
        "Foreign Exchange Management Act, 1999 (FEMA)",
    ],
    key_precedents=[
        "Tata Consultancy Services v. Cyrus Investments (2021) — Board removal powers",
        "Essar Steel v. Satish Kumar Gupta (2019) — CIRP resolution plan approval",
        "Swiss Ribbons v. Union of India (2019) — IBC constitutionality upheld",
        "Sahara v. SEBI (2012) — SEBI regulatory jurisdiction",
        "CCI v. SAIL (2010) — Competition Act interpretation",
    ],
    query_boost_keywords=[
        "company", "director", "shareholder", "NCLT", "IBC", "insolvency",
        "SEBI", "merger", "acquisition", "corporate governance", "compliance",
        "board", "resolution", "winding up", "liquidation",
    ],
    filter_keywords=[
        "company", "companies act", "director", "shareholder", "nclt", "nclat",
        "ibc", "insolvency", "bankruptcy", "sebi", "merger", "acquisition",
        "corporate", "governance", "compliance", "board", "resolution",
        "llp", "partnership", "fema", "competition",
    ],
    verification_checklist=[
        "Does the answer cite Companies Act, 2013 sections?",
        "Does the answer reference NCLT/NCLAT jurisdiction if relevant?",
        "Does the answer address compliance obligations?",
        "Does the answer distinguish between public and private companies?",
    ],
    synthesis_instructions=(
        "MANDATORY for Corporate Law responses:\n"
        "1. Cite specific Companies Act 2013 sections\n"
        "2. Address NCLT/NCLAT jurisdiction and procedures\n"
        "3. Distinguish between public and private company obligations\n"
        "4. Reference SEBI regulations for listed company matters\n"
        "5. Address IBC provisions for insolvency matters\n"
    ),
    auto_detect_keywords=[
        "company", "director", "shareholder", "nclt", "nclat", "ibc",
        "insolvency", "sebi", "merger", "acquisition", "corporate",
        "governance", "compliance", "board", "resolution", "winding up",
        "liquidation", "llp", "partnership", "debenture", "share",
    ],
))

# ─────────────────────────────────────────────────────────────────────────────
#  6. BANKING & FINANCE
# ─────────────────────────────────────────────────────────────────────────────
_register(DomainProfile(
    domain_id="banking_finance",
    display_name="Banking & Finance",
    parent_domain=None,
    expert_persona=(
        "a Senior Banking & Finance Law Advocate specialising in RBI regulations, "
        "SARFAESI, DRT matters, NPA recovery, cheque bounce (NI Act), "
        "and financial services regulation"
    ),
    core_statutes=[
        "Negotiable Instruments Act, 1881 (Section 138 — Cheque Bounce)",
        "SARFAESI Act, 2002",
        "Recovery of Debts and Bankruptcy Act, 1993 (DRT Act)",
        "Banking Regulation Act, 1949",
        "Reserve Bank of India Act, 1934",
        "Payment and Settlement Systems Act, 2007",
        "Factoring Regulation Act, 2011",
    ],
    key_precedents=[
        "Mardia Chemicals v. Union of India (2004) — SARFAESI constitutionality",
        "ICICI Bank v. Prakash Kaur (2007) — Secured creditor rights",
        "Dashrath Rupsingh Rathod v. State of Maharashtra (2014) — Section 138 jurisdiction",
        "Meters and Instruments v. Kanchan Mehta (2018) — Section 138 compounding",
    ],
    query_boost_keywords=[
        "bank", "banking", "loan", "NPA", "SARFAESI", "cheque bounce",
        "Section 138", "DRT", "RBI", "mortgage", "guarantee", "EMI",
        "interest rate", "credit", "recovery",
    ],
    filter_keywords=[
        "bank", "banking", "loan", "npa", "sarfaesi", "cheque", "bounce",
        "section 138", "drt", "rbi", "mortgage", "guarantee", "emi",
        "interest", "credit", "recovery", "deposit", "nbfc", "fintech",
    ],
    verification_checklist=[
        "Does the answer cite NI Act Section 138 for cheque bounce cases?",
        "Does the answer reference SARFAESI provisions for recovery matters?",
        "Does the answer address RBI circulars/guidelines if relevant?",
        "Does the answer identify the correct forum (DRT/Consumer Forum/Civil Court)?",
    ],
    synthesis_instructions=(
        "MANDATORY for Banking & Finance responses:\n"
        "1. Cite specific NI Act, SARFAESI, or Banking Regulation Act sections\n"
        "2. Reference relevant RBI circulars and guidelines\n"
        "3. Identify correct forum (DRT/Consumer Commission/Civil Court)\n"
        "4. Address time limitations and procedural requirements\n"
        "5. Distinguish between secured and unsecured creditor rights\n"
    ),
    auto_detect_keywords=[
        "bank", "loan", "npa", "sarfaesi", "cheque", "bounce", "section 138",
        "drt", "rbi", "mortgage", "emi", "interest", "credit", "nbfc",
        "fintech", "deposit", "recovery", "default", "guarantor",
    ],
))

# ─────────────────────────────────────────────────────────────────────────────
#  7. CYBER LAW
# ─────────────────────────────────────────────────────────────────────────────
_register(DomainProfile(
    domain_id="cyber_law",
    display_name="Cyber Law",
    parent_domain=None,
    expert_persona=(
        "a Senior Cyber Law and Information Technology Law Advocate specialising in "
        "IT Act 2000, data protection (DPDPA 2023), cybercrime, digital evidence, "
        "intermediary liability, and online privacy disputes"
    ),
    core_statutes=[
        "Information Technology Act, 2000 (IT Act)",
        "IT (Intermediary Guidelines) Rules, 2021",
        "IT (SPDI) Rules, 2011",
        "Digital Personal Data Protection Act, 2023 (DPDPA)",
        "Indian Penal Code Sections on cyber-offences (IPC 463, 465, 468, 471)",
    ],
    key_precedents=[
        "Shreya Singhal v. Union of India (2015) — Section 66A struck down, free speech",
        "K.S. Puttaswamy v. Union of India (2017) — Privacy as fundamental right",
        "Anuradha Bhasin v. Union of India (2020) — Internet shutdown proportionality",
        "Google India v. Visaka Industries (2019) — Intermediary liability",
    ],
    query_boost_keywords=[
        "cyber", "IT Act", "data protection", "DPDPA", "hacking", "phishing",
        "data breach", "privacy", "online fraud", "intermediary", "social media",
        "digital evidence", "Section 43", "Section 43A", "Section 66",
    ],
    filter_keywords=[
        "cyber", "it act", "data protection", "dpdpa", "hacking", "phishing",
        "data breach", "privacy", "online", "digital", "internet", "computer",
        "intermediary", "social media", "website", "email", "password",
    ],
    verification_checklist=[
        "Does the answer cite IT Act sections correctly?",
        "Does the answer distinguish between IT Act offenses and IPC cyber-offenses?",
        "Does the answer reference DPDPA 2023 for data protection matters?",
        "Does the answer address intermediary liability guidelines?",
    ],
    synthesis_instructions=(
        "MANDATORY for Cyber Law responses:\n"
        "1. Cite specific IT Act section numbers\n"
        "2. Distinguish between IT Act civil remedies (Section 43/43A) and criminal provisions\n"
        "3. Reference DPDPA 2023 for data protection matters\n"
        "4. Discuss digital evidence admissibility (Section 65B Indian Evidence Act)\n"
        "5. Address intermediary liability under IT Rules 2021\n"
    ),
    auto_detect_keywords=[
        "cyber", "hacking", "phishing", "data breach", "privacy", "online fraud",
        "it act", "dpdpa", "data protection", "digital", "internet", "computer",
        "social media", "website", "email", "password", "malware", "ransomware",
    ],
))

# ─────────────────────────────────────────────────────────────────────────────
#  8. EMPLOYMENT LAW
# ─────────────────────────────────────────────────────────────────────────────
_register(DomainProfile(
    domain_id="employment_law",
    display_name="Employment Law",
    parent_domain=None,
    expert_persona=(
        "a Senior Labour & Employment Law Advocate specialising in industrial disputes, "
        "workplace rights, termination, wages, social security, and the new Labour Codes"
    ),
    core_statutes=[
        "Industrial Disputes Act, 1947",
        "Code on Wages, 2019",
        "Industrial Relations Code, 2020",
        "Social Security Code, 2020",
        "Occupational Safety, Health and Working Conditions Code, 2020",
        "Shops and Establishments Acts (State-specific)",
        "Payment of Gratuity Act, 1972",
        "Employees' Provident Fund Act, 1952 (EPF)",
        "POSH Act, 2013 (Sexual Harassment of Women at Workplace)",
    ],
    key_precedents=[
        "Workmen of Dimakuchi Tea Estate v. Management (1958) — Retrenchment principles",
        "Delhi Transport Corporation v. DTC Mazdoor Congress (1991) — Right to livelihood",
        "Vishaka v. State of Rajasthan (1997) — Sexual harassment guidelines",
        "SAIL v. National Union Waterfront Workers (2001) — Regularisation of contract workers",
    ],
    query_boost_keywords=[
        "employment", "labour", "labor", "termination", "wages", "salary",
        "PF", "gratuity", "industrial dispute", "workman", "employer",
        "retrenchment", "layoff", "sexual harassment", "POSH",
    ],
    filter_keywords=[
        "employment", "labour", "labor", "termination", "wages", "salary",
        "pf", "provident fund", "gratuity", "industrial dispute", "workman",
        "employer", "employee", "retrenchment", "layoff", "posh",
        "sexual harassment", "workplace", "notice period", "bonus",
    ],
    verification_checklist=[
        "Does the answer cite the correct labour code or act?",
        "Does the answer address industrial dispute resolution mechanisms?",
        "Does the answer distinguish between workmen and non-workmen?",
        "Does the answer reference forum (Labour Court/Industrial Tribunal)?",
    ],
    synthesis_instructions=(
        "MANDATORY for Employment Law responses:\n"
        "1. Cite the applicable labour code or pre-existing act\n"
        "2. Distinguish between workmen (ID Act) and employees (other acts)\n"
        "3. Address applicable forum (Labour Court/Industrial Tribunal/Civil Court)\n"
        "4. Discuss statutory protections against unfair dismissal\n"
        "5. Note state-specific variations in shops & establishments acts\n"
    ),
    auto_detect_keywords=[
        "employment", "job", "fired", "terminated", "wages", "salary", "labour",
        "labor", "pf", "provident fund", "gratuity", "employer", "employee",
        "retrenchment", "layoff", "sexual harassment", "posh", "workplace",
        "notice period", "bonus", "resignation", "industrial",
    ],
))

# ─────────────────────────────────────────────────────────────────────────────
#  9. INTELLECTUAL PROPERTY
# ─────────────────────────────────────────────────────────────────────────────
_register(DomainProfile(
    domain_id="intellectual_property",
    display_name="Intellectual Property",
    parent_domain=None,
    expert_persona=(
        "a Senior Intellectual Property Law Advocate specialising in patents, trademarks, "
        "copyrights, trade secrets, designs, and IP enforcement in India"
    ),
    core_statutes=[
        "Patents Act, 1970",
        "Trade Marks Act, 1999",
        "Copyright Act, 1957",
        "Designs Act, 2000",
        "Geographical Indications of Goods Act, 1999",
        "Plant Variety Protection Act, 2001",
        "Semiconductor Integrated Circuits Layout-Design Act, 2000",
    ],
    key_precedents=[
        "Novartis v. Union of India (2013) — Section 3(d) patentability (evergreening)",
        "Yahoo v. Akash Arora (1999) — Domain name as trademark",
        "Bayer v. Union of India (2014) — Compulsory licensing",
        "Eastern Book Company v. Navin J. Desai (2008) — Copyright in compilations",
    ],
    query_boost_keywords=[
        "patent", "trademark", "copyright", "IP", "intellectual property",
        "infringement", "registration", "design", "trade secret", "licensing",
    ],
    filter_keywords=[
        "patent", "trademark", "copyright", "ip", "intellectual property",
        "infringement", "registration", "design", "trade secret", "licensing",
        "brand", "logo", "invention", "plagiarism", "royalty",
    ],
    verification_checklist=[
        "Does the answer cite the correct IP statute?",
        "Does the answer address registration procedures?",
        "Does the answer discuss infringement remedies?",
        "Does the answer reference IPAB/Commercial Court jurisdiction?",
    ],
    synthesis_instructions=(
        "MANDATORY for IP Law responses:\n"
        "1. Identify the type of IP right (patent/trademark/copyright/design)\n"
        "2. Cite the specific statute and relevant sections\n"
        "3. Address registration requirements and timeline\n"
        "4. Discuss infringement tests and available remedies\n"
        "5. Reference international treaties (TRIPS, Paris Convention) if relevant\n"
    ),
    auto_detect_keywords=[
        "patent", "trademark", "copyright", "ip", "intellectual property",
        "infringement", "brand", "logo", "invention", "design", "trade secret",
        "licensing", "plagiarism", "royalty", "piracy",
    ],
))

# ─────────────────────────────────────────────────────────────────────────────
#  10-14. OFFENSE-SPECIFIC PROFILES (mapped to Criminal Law as parent)
# ─────────────────────────────────────────────────────────────────────────────

# 10. MURDER
_register(DomainProfile(
    domain_id="murder",
    display_name="Murder",
    parent_domain="criminal_law",
    expert_persona=(
        "a Senior Criminal Law Advocate with deep specialisation in homicide cases — "
        "murder (IPC 302/BNS 103), culpable homicide (IPC 304/BNS 105), "
        "attempt to murder (IPC 307/BNS 109), and death sentence jurisprudence"
    ),
    core_statutes=[
        "IPC Section 299 (Culpable Homicide) / BNS Section 100",
        "IPC Section 300 (Murder definition) / BNS Section 101",
        "IPC Section 302 (Punishment for Murder) / BNS Section 103",
        "IPC Section 304 (Culpable Homicide not amounting to Murder) / BNS Section 105",
        "IPC Section 304A (Death by Negligence) / BNS Section 106",
        "IPC Section 307 (Attempt to Murder) / BNS Section 109",
        "IPC Section 34 (Common Intention) / BNS Section 3(5)",
        "IPC Section 120B (Criminal Conspiracy) / BNS Section 61",
    ],
    key_precedents=[
        "Bachan Singh v. State of Punjab (1980) — Rarest of rare doctrine for death penalty",
        "Machhi Singh v. State of Punjab (1983) — Categories for death sentence",
        "State of Rajasthan v. Kheraj Ram (2003) — Distinction: murder vs culpable homicide",
        "Virsa Singh v. State of Punjab (1958) — Intention in murder (4 elements test)",
    ],
    query_boost_keywords=[
        "murder", "homicide", "killing", "death", "IPC 302", "BNS 103",
        "culpable homicide", "attempt to murder", "self-defense", "death penalty",
    ],
    filter_keywords=[
        "murder", "homicide", "killing", "death", "302", "300", "307",
        "culpable", "death penalty", "life imprisonment", "self-defense",
    ],
    verification_checklist=[
        "Does the answer cite IPC 300/302 or BNS equivalents?",
        "Does the answer distinguish murder from culpable homicide?",
        "Does the answer discuss intention vs knowledge?",
        "Does the answer address exceptions to murder (IPC 300 exceptions)?",
    ],
    synthesis_instructions=(
        "MANDATORY for Murder case responses:\n"
        "1. Apply Virsa Singh 4-element test for intention\n"
        "2. Distinguish murder (Section 300) from culpable homicide (Section 299)\n"
        "3. Analyse which Exception to Section 300 may apply (sudden provocation, self-defense, etc.)\n"
        "4. Discuss Bachan Singh 'rarest of rare' test if death penalty is relevant\n"
        "5. Reference BNS equivalents alongside IPC sections\n"
    ),
    auto_detect_keywords=[
        "murder", "killing", "homicide", "302", "death", "killed", "stabbed",
        "shot", "death penalty", "life imprisonment", "culpable homicide",
    ],
))

# 11. RAPE
_register(DomainProfile(
    domain_id="rape",
    display_name="Rape",
    parent_domain="criminal_law",
    expert_persona=(
        "a Senior Criminal Law Advocate specialising in sexual offenses — "
        "rape (IPC 375-376/BNS 63-65), POCSO, victim rights, "
        "evidence standards, and witness protection"
    ),
    core_statutes=[
        "IPC Section 375 (Definition of Rape) / BNS Section 63",
        "IPC Section 376 (Punishment for Rape) / BNS Section 65",
        "IPC Section 376A-376E (Aggravated forms) / BNS 66-70",
        "POCSO Act, 2012 (Protection of Children from Sexual Offences)",
        "CrPC Section 164 (Recording of victim statement) / BNSS Section 183",
        "Indian Evidence Act Section 114A (Presumption in certain cases of rape)",
    ],
    key_precedents=[
        "Mukesh v. State (Nirbhaya Case, 2017) — Death for brutal gang rape",
        "Tukaram v. State of Maharashtra (Mathura Case, 1979) — Led to rape law reform",
        "State of Punjab v. Gurmit Singh (1996) — Victim testimony is sufficient",
        "Priya Patel v. State of MP (2006) — Consent must be free and voluntary",
    ],
    query_boost_keywords=[
        "rape", "sexual assault", "sexual offense", "consent", "IPC 376",
        "POCSO", "victim rights", "molestation", "outraging modesty",
    ],
    filter_keywords=[
        "rape", "sexual", "assault", "consent", "376", "375", "pocso",
        "victim", "molestation", "modesty", "penetration",
    ],
    verification_checklist=[
        "Does the answer cite IPC 375/376 or BNS equivalents?",
        "Does the answer address consent as central element?",
        "Does the answer discuss victim protection provisions?",
        "Does the answer reference POCSO if minor is involved?",
    ],
    synthesis_instructions=(
        "MANDATORY for Sexual Offense responses:\n"
        "1. Cite IPC 375/376 (definition + punishment) with BNS equivalents\n"
        "2. Discuss consent as the central element\n"
        "3. Address victim protection: Section 164 statement, in-camera trial\n"
        "4. Reference POCSO Act if the victim is a minor\n"
        "5. Discuss evidence standards and presumption under Section 114A\n"
    ),
    auto_detect_keywords=[
        "rape", "sexual assault", "sexual offense", "molestation", "376",
        "pocso", "consent", "victim", "modesty",
    ],
))

# 12. FRAUD
_register(DomainProfile(
    domain_id="fraud",
    display_name="Fraud",
    parent_domain="criminal_law",
    expert_persona=(
        "a Senior Criminal Law Advocate specialising in economic offenses — "
        "cheating (IPC 420/BNS 318), criminal breach of trust, forgery, "
        "and white-collar crime prosecution"
    ),
    core_statutes=[
        "IPC Section 415-420 (Cheating) / BNS Section 318",
        "IPC Section 405-409 (Criminal Breach of Trust) / BNS Section 316",
        "IPC Section 463-471 (Forgery) / BNS Section 336-340",
        "IPC Section 120B (Criminal Conspiracy) / BNS Section 61",
        "Prevention of Money Laundering Act, 2002 (PMLA)",
        "Negotiable Instruments Act, Section 138 (Cheque Bounce)",
    ],
    key_precedents=[
        "Hridaya Ranjan Prasad v. State of Bihar (2000) — Cheating vs civil dispute",
        "Iridium India Telecom v. Motorola (2011) — Cheating complaint maintainability",
        "Vijay Madanlal Choudhary v. Union of India (2022) — PMLA constitutionality",
        "Indian Oil Corporation v. NEPC India (2006) — Criminal breach of trust elements",
    ],
    query_boost_keywords=[
        "fraud", "cheating", "IPC 420", "forgery", "breach of trust",
        "money laundering", "PMLA", "scam", "deception", "misappropriation",
    ],
    filter_keywords=[
        "fraud", "cheating", "420", "forgery", "breach of trust",
        "money laundering", "pmla", "scam", "deception", "misappropriation",
        "embezzlement", "swindling", "dishonest",
    ],
    verification_checklist=[
        "Does the answer cite IPC 415-420 or BNS equivalents?",
        "Does the answer distinguish criminal fraud from civil dispute?",
        "Does the answer address mens rea (dishonest intention)?",
        "Does the answer reference PMLA for money laundering?",
    ],
    synthesis_instructions=(
        "MANDATORY for Fraud/Cheating responses:\n"
        "1. Cite IPC 415 (definition) and 420 (punishment) with BNS equivalents\n"
        "2. Apply Hridaya Ranjan test: distinguish criminal cheating from civil breach\n"
        "3. Discuss dishonest intention as essential ingredient\n"
        "4. Address forgery charges if documentary fraud is involved\n"
        "5. Reference PMLA provisions for money laundering angle\n"
    ),
    auto_detect_keywords=[
        "fraud", "cheating", "420", "forgery", "scam", "deception",
        "misappropriation", "embezzlement", "swindling", "ponzi",
        "money laundering", "breach of trust",
    ],
))

# 13. TERRORISM
_register(DomainProfile(
    domain_id="terrorism",
    display_name="Terrorism",
    parent_domain="criminal_law",
    expert_persona=(
        "a Senior National Security & Criminal Law Advocate specialising in "
        "terrorism prosecution under UAPA, NIA Act, anti-terror jurisprudence, "
        "and fundamental rights in security contexts"
    ),
    core_statutes=[
        "Unlawful Activities (Prevention) Act, 1967 (UAPA) — Sections 15-23",
        "National Investigation Agency Act, 2008 (NIA Act)",
        "National Security Act, 1980 (NSA)",
        "COFEPOSA Act, 1974",
        "Arms Act, 1959 (for weapons charges)",
        "Explosive Substances Act, 1908",
    ],
    key_precedents=[
        "Arup Bhuyan v. State of Assam (2011) — Mere membership not enough for UAPA",
        "Watali v. NIA (2019) — Bail restrictions under UAPA",
        "Kartar Singh v. State of Punjab (1994) — TADA constitutionality (relevant for UAPA)",
        "Union of India v. K.A. Najeeb (2021) — Right to bail even under special laws",
    ],
    query_boost_keywords=[
        "terrorism", "UAPA", "NIA", "national security", "unlawful activities",
        "designated terrorist", "terror financing", "sedition",
    ],
    filter_keywords=[
        "terrorism", "uapa", "nia", "national security", "terror", "militant",
        "extremist", "unlawful activities", "designated", "explosive", "sedition",
    ],
    verification_checklist=[
        "Does the answer cite UAPA sections correctly?",
        "Does the answer address NIA jurisdiction?",
        "Does the answer discuss bail restrictions under UAPA?",
        "Does the answer balance security concerns with fundamental rights?",
    ],
    synthesis_instructions=(
        "MANDATORY for Terrorism/UAPA responses:\n"
        "1. Cite specific UAPA sections (15-23 for offenses)\n"
        "2. Address NIA jurisdiction and special court procedure\n"
        "3. Discuss strict bail provisions under Section 43D(5) UAPA\n"
        "4. Balance national security with fundamental rights analysis\n"
        "5. Reference Watali principles for bail in terror cases\n"
    ),
    auto_detect_keywords=[
        "terrorism", "terror", "uapa", "nia", "national security", "militant",
        "extremist", "bomb", "explosion", "jihad", "radicalization",
    ],
))

# 14. CORRUPTION
_register(DomainProfile(
    domain_id="corruption",
    display_name="Corruption",
    parent_domain="criminal_law",
    expert_persona=(
        "a Senior Criminal Law Advocate specialising in anti-corruption prosecution — "
        "Prevention of Corruption Act 1988, Lokpal & Lokayuktas Act, "
        "disproportionate assets cases, and trap/bribery cases"
    ),
    core_statutes=[
        "Prevention of Corruption Act, 1988 (PCA) — as amended in 2018",
        "Lokpal and Lokayuktas Act, 2013",
        "IPC Sections 161-165A (Public Servant offenses) / BNS equivalents",
        "Benami Transactions (Prohibition) Act, 1988",
        "Right to Information Act, 2005 (for transparency)",
    ],
    key_precedents=[
        "P.V. Narasimha Rao v. State (1998) — Parliament privilege and PCA",
        "State of MP v. Ram Singh (2000) — Trap case procedure",
        "Neeraj Dutta v. State (2023) — Demand and acceptance both needed for PCA",
        "Subramanian Swamy v. Manmohan Singh (2012) — Sanction for prosecution",
    ],
    query_boost_keywords=[
        "corruption", "bribery", "PCA", "prevention of corruption",
        "public servant", "disproportionate assets", "Lokpal", "trap case",
    ],
    filter_keywords=[
        "corruption", "bribery", "pca", "prevention of corruption",
        "public servant", "disproportionate", "lokpal", "lokayukta",
        "bribe", "kickback", "graft", "trap", "cbi",
    ],
    verification_checklist=[
        "Does the answer cite PCA 1988 (as amended 2018)?",
        "Does the answer address demand + acceptance test?",
        "Does the answer discuss sanction for prosecution?",
        "Does the answer reference Lokpal jurisdiction if relevant?",
    ],
    synthesis_instructions=(
        "MANDATORY for Corruption case responses:\n"
        "1. Cite PCA 1988 sections (as amended by 2018 amendment)\n"
        "2. Apply the Neeraj Dutta test: demand AND acceptance required\n"
        "3. Discuss prior sanction requirement for prosecution of public servants\n"
        "4. Address trap case procedure and evidence standards\n"
        "5. Reference Lokpal/Lokayukta jurisdiction for high-level officials\n"
    ),
    auto_detect_keywords=[
        "corruption", "bribery", "bribe", "public servant", "government officer",
        "disproportionate assets", "lokpal", "cbi", "acb", "rti",
        "kickback", "graft", "pca",
    ],
))


# ═══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def get_domain_profile(category: str) -> Optional[DomainProfile]:
    """
    Look up domain profile by category name (case-insensitive).
    Returns None if category is 'general', 'all', or unrecognised.
    """
    if not category or category.lower() in ("general", "all", ""):
        return None
    return DOMAIN_PROFILES.get(category.lower())


def auto_detect_domain(query: str) -> Optional[DomainProfile]:
    """
    Auto-detect the most relevant domain from the query text.
    Uses keyword matching with scoring.  Returns the best-matching profile
    or None if no strong match (score < 2).

    This is the DEFAULT behavior when the user hasn't picked a category.
    """
    query_lower = query.lower()
    best_profile: Optional[DomainProfile] = None
    best_score = 0

    # Only scan unique profiles (skip duplicate display_name → domain_id mappings)
    seen_ids = set()
    for profile in DOMAIN_PROFILES.values():
        if profile.domain_id in seen_ids:
            continue
        seen_ids.add(profile.domain_id)

        score = sum(1 for kw in profile.auto_detect_keywords if kw in query_lower)

        # For offense-specific profiles, only prefer them over parent if they
        # score significantly higher (≥ 2 offense-specific keyword hits)
        if profile.parent_domain and score >= 2 and score > best_score:
            best_profile = profile
            best_score = score
        elif not profile.parent_domain and score > best_score:
            best_profile = profile
            best_score = score

    # Require minimum score of 2 to avoid false positives
    if best_score >= 2:
        logger.info(f"[DOMAIN-AUTO] Detected domain '{best_profile.display_name}' "
                     f"(score={best_score}) from query")
        return best_profile

    return None


def resolve_domain(category: str, query: str) -> Optional[DomainProfile]:
    """
    Main resolver: manual override takes priority, otherwise auto-detect.

    Usage:
        profile = resolve_domain(request.category, user_query)
        # profile is None only if no domain could be determined
    """
    # 1. Manual user selection always wins
    if category and category.lower() not in ("general", "all", ""):
        manual = get_domain_profile(category)
        if manual:
            logger.info(f"[DOMAIN] Manual override active: {manual.display_name}")
            return manual

    # 2. Auto-detect from query text
    return auto_detect_domain(query)


def get_domain_boost_keywords(profile: Optional[DomainProfile], limit: int = 5) -> List[str]:
    """Get top N boost keywords for query rewriting. Returns empty if no profile."""
    if not profile:
        return []
    return profile.query_boost_keywords[:limit]


def get_planner_directive(profile: DomainProfile) -> str:
    """Generate the domain-lock directive for the planner system prompt."""
    return (
        f"\n\nDOMAIN LOCK ACTIVE: The query has been classified under '{profile.display_name}'.\n"
        f"You MUST:\n"
        f"1. Set detected_domains to include '{profile.domain_id}'\n"
        f"2. Rewrite the query to prioritise {profile.display_name} terminology\n"
        f"3. Generate sub_queries focused on {profile.display_name} statutes and precedents\n"
        f"4. NEVER classify this as 'general' — it is a {profile.display_name} query\n"
        f"\nCore statutes: {', '.join(profile.core_statutes[:6])}\n"
        f"Key precedents: {', '.join(p.split(' — ')[0] for p in profile.key_precedents[:4])}\n"
    )


def get_synthesiser_system_prompt(profile: DomainProfile, lang_hint: str = "") -> str:
    """Generate the domain-specialist system prompt for the synthesiser."""
    return (
        f"You are {profile.expert_persona}.\n\n"
        f"You are a DOMAIN SPECIALIST. Your analysis must be grounded in "
        f"{profile.display_name} law specifically.\n\n"
        f"MANDATORY REFERENCES for {profile.display_name}:\n"
        f"Core Statutes:\n" +
        "\n".join(f"  • {s}" for s in profile.core_statutes) +
        f"\n\nKey Precedents:\n" +
        "\n".join(f"  • {p}" for p in profile.key_precedents) +
        f"\n\n{profile.synthesis_instructions}\n"
        f"RULES:\n"
        f"- Your answer MUST cite at least 2 statutes from the core statutes list above\n"
        f"- Your answer MUST reference at least 1 landmark case from the precedents above\n"
        f"- Do NOT drift into unrelated legal areas unless directly connected to {profile.display_name}\n"
        f"- Maintain laser focus on {profile.display_name}\n"
        f"- If the retrieved context lacks domain-specific data, use your training knowledge on "
        f"these statutes and cases, but never invent section numbers\n"
        f"- NEVER use conversational filler like 'Based on the provided context'\n"
        f"- End with ⚠️ Disclaimer\n"
        f"{lang_hint}"
    )


def get_verifier_domain_check(profile: DomainProfile) -> str:
    """Generate domain-specific verification criteria."""
    checklist = "\n".join(f"  - {item}" for item in profile.verification_checklist)
    return (
        f"\n\nDOMAIN-SPECIFIC VERIFICATION for {profile.display_name}:\n"
        f"{checklist}\n"
        f"  - Is the answer focused on {profile.display_name} or does it drift to unrelated areas?\n"
        f"  - Lower confidence by 0.15 if the answer doesn't cite any domain-specific statutes\n"
        f"  - Lower confidence by 0.10 if the answer doesn't reference domain-relevant cases\n"
    )


def get_expanded_filter_keywords(profile: Optional[DomainProfile]) -> List[str]:
    """Get comprehensive filter keywords for retrieval boosting."""
    if not profile:
        return []

    keywords = list(profile.filter_keywords)

    # If this is an offense profile, also include parent keywords
    if profile.parent_domain:
        parent = DOMAIN_PROFILES.get(profile.parent_domain)
        if parent:
            keywords.extend(parent.filter_keywords)

    return list(set(keywords))  # deduplicate
