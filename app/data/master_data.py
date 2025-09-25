# app/master_data.py
# This file contains the canonical list of all recognizable medical items, procedures, and charges.
# It serves as the "source of truth" for the normalization engine.

MASTER_ITEM_LIST = [
    # =================================================================================
    # == Room, Boarding, and Nursing Charges
    # =================================================================================
    {"id": "RC01", "name": "General Ward Bed Charges", "category": "Room Charges"},
    {"id": "RC02", "name": "Semi-Private Ward Bed Charges", "category": "Room Charges"},
    # FIX 1: Made names more distinct to avoid confusion between Private and Deluxe rooms.
    {"id": "RC03", "name": "Single Private Room Ward Accommodation", "category": "Room Charges"},
    {"id": "RC04", "name": "Deluxe Room Suite Accommodation Charges", "category": "Room Charges"},
    {"id": "RC05", "name": "Suite Accommodation Charges", "category": "Room Charges"},
    {"id": "RC06", "name": "Intensive Care Unit (ICU) Charges per day", "category": "Room Charges"},
    {"id": "RC07", "name": "Intensive Coronary Care Unit (ICCU) Charges per day", "category": "Room Charges"},
    {"id": "RC08", "name": "Neonatal Intensive Care Unit (NICU) Charges per day", "category": "Room Charges"},
    {"id": "RC09", "name": "Pediatric Intensive Care Unit (PICU) Charges per day", "category": "Room Charges"},
    {"id": "RC10", "name": "Isolation Ward Charges", "category": "Room Charges"},
    {"id": "RC11", "name": "Labor Delivery Recovery (LDR) Room Charges", "category": "Room Charges"},

    # =================================================================================
    # == Professional Fees (Doctors, Surgeons, etc.)
    # =================================================================================
    {"id": "PF01", "name": "Initial Doctor Consultation Fee", "category": "Professional Fees"},
    {"id": "PF02", "name": "Follow-up Doctor Consultation Fee", "category": "Professional Fees"},
    {"id": "PF03", "name": "Emergency Consultation Fee", "category": "Professional Fees"},
    {"id": "PF04", "name": "Specialist Consultation Fee", "category": "Professional Fees"},
    {"id": "PF05", "name": "Surgeon's Fee", "category": "Professional Fees"},
    {"id": "PF06", "name": "Assistant Surgeon's Fee", "category": "Professional Fees"},
    # FIX 2: Added common typo 'Anestesia' to the name to teach the model.
    {"id": "PF07", "name": "Anesthetist Anesthesia Anestesia Fee", "category": "Professional Fees"},
    {"id": "PF08", "name": "Nursing Care Charges per day", "category": "Professional Fees"},
    {"id": "PF09", "name": "Physiotherapy Session Fee", "category": "Professional Fees"},
    {"id": "PF10", "name": "Dietician Consultation Fee", "category": "Professional Fees"},

    # =================================================================================
    # == Procedure & Treatment Charges
    # =================================================================================
    # FIX 3: Added abbreviation 'OT' to the name to teach the model.
    {"id": "PROC01", "name": "OT Operation Theatre Charges", "category": "Procedure Charges"},
    {"id": "PROC01", "name": "Minor Operation Theatre Charges", "category": "Procedure Charges"},
    {"id": "PROC03", "name": "Wound Dressing and Suture Charges", "category": "Procedure Charges"},
    {"id": "PROC04", "name": "Blood Transfusion Charges", "category": "Procedure Charges"},
    {"id": "PROC05", "name": "Chemotherapy Administration Charges", "category": "Procedure Charges"},
    {"id": "PROC06", "name": "Dialysis Session Charges", "category": "Procedure Charges"},
    {"id": "PROC07", "name": "Nebulization Charges", "category": "Procedure Charges"},

    # ... (rest of the file remains the same) ...
    # =================================================================================
    # == Diagnostics - Laboratory Tests
    # =================================================================================
    {"id": "DIAG01", "name": "Complete Blood Count (CBC) Test", "category": "Diagnostics"},
    {"id": "DIAG02", "name": "Liver Function Test (LFT)", "category": "Diagnostics"},
    {"id": "DIAG03", "name": "Kidney Function Test (KFT)", "category": "Diagnostics"},
    {"id": "DIAG04", "name": "Lipid Profile Test", "category": "Diagnostics"},
    {"id": "DIAG05", "name": "Thyroid Profile Test (T3, T4, TSH)", "category": "Diagnostics"},
    {"id": "DIAG06", "name": "Blood Sugar Test (Fasting, Post-Prandial)", "category": "Diagnostics"},
    {"id": "DIAG07", "name": "Urine Routine & Microscopy Test", "category": "Diagnostics"},
    {"id": "DIAG08", "name": "Dengue Serology Test (NS1, IgG, IgM)", "category": "Diagnostics"},
    {"id": "DIAG09", "name": "COVID-19 RT-PCR Test", "category": "Diagnostics"},
    {"id": "DIAG10", "name": "Histopathology / Biopsy Report", "category": "Diagnostics"},
    
    # =================================================================================
    # == Diagnostics - Imaging & Radiology
    # =================================================================================
    {"id": "IMG01", "name": "Chest X-Ray", "category": "Diagnostics"},
    {"id": "IMG02", "name": "Limb or Joint X-Ray", "category": "Diagnostics"},
    {"id": "IMG03", "name": "Abdominal Ultrasound (USG)", "category": "Diagnostics"},
    {"id": "IMG04", "name": "Doppler Study", "category": "Diagnostics"},
    {"id": "IMG05", "name": "Electrocardiogram (ECG)", "category": "Diagnostics"},
    {"id": "IMG06", "name": "2D Echocardiogram (2D Echo)", "category": "Diagnostics"},
    {"id": "IMG07", "name": "CT Scan of the Brain", "category": "Diagnostics"},
    {"id": "IMG08", "name": "CT Scan of the Chest or Abdomen", "category": "Diagnostics"},
    {"id": "IMG09", "name": "MRI Scan of the Brain or Spine", "category": "Diagnostics"},
    {"id": "IMG10", "name": "MRI Scan of a Joint (e.g., Knee)", "category": "Diagnostics"},
    
    # =================================================================================
    # == Pharmacy - Common Medicines
    # =================================================================================
    {"id": "PHARM01", "name": "Paracetamol Tablet", "category": "Pharmacy"},
    {"id": "PHARM02", "name": "Ibuprofen Tablet", "category": "Pharmacy"},
    {"id": "PHARM03", "name": "Amoxicillin Antibiotic", "category": "Pharmacy"},
    {"id": "PHARM04", "name": "Azithromycin Antibiotic", "category": "Pharmacy"},
    {"id": "PHARM05", "name": "Ondansetron Injection (Anti-emetic)", "category": "Pharmacy"},
    {"id": "PHARM06", "name": "Pantoprazole Injection (Antacid)", "category": "Pharmacy"},
    {"id": "PHARM07", "name": "Normal Saline (NS) IV Fluid", "category": "Pharmacy"},
    {"id": "PHARM08", "name": "Dextrose Normal Saline (DNS) IV Fluid", "category": "Pharmacy"},
    {"id": "PHARM09", "name": "Metformin Tablet (Anti-diabetic)", "category": "Pharmacy"},
    {"id": "PHARM10", "name": "Amlodipine Tablet (Anti-hypertensive)", "category": "Pharmacy"},
    
    # =================================================================================
    # == Implants & High-Value Disposables
    # =================================================================================
    {"id": "IMP01", "name": "Drug-Eluting Coronary Stent", "category": "Implants"},
    {"id": "IMP02", "name": "Intraocular Lens (IOL) for Cataract", "category": "Implants"},
    {"id": "IMP03", "name": "Orthopedic Plate and Screws", "category": "Implants"},
    {"id": "IMP04", "name": "Prosthetic Knee Joint", "category": "Implants"},
    {"id": "HVD01", "name": "Surgical Stapler", "category": "Payable Consumable"},
    
    # =================================================================================
    # == Administrative & Other Charges
    # =================================================================================
    # FIX 4: Made name more specific to avoid false positive with 'parking fee'.
    {"id": "ADM01", "name": "Hospital Admission and Registration Charges", "category": "Administrative Charges"},
    {"id": "ADM02", "name": "Medical Records or Folder Fee", "category": "Administrative Charges"},
    {"id": "ADM03", "name": "Discharge Summary Certificate Fee", "category": "Administrative Charges"},
    {"id": "OTH01", "name": "Ambulance Service Charges", "category": "Other Charges"},
    {"id": "OTH02", "name": "Patient Dietary and Food Charges", "category": "Other Charges"},
    {"id": "OTH03", "name": "Visitor Pass Charges", "category": "Other Charges"},
    {"id": "OTH04", "name": "Blood Bank Processing Fee", "category": "Other Charges"},
        # =================================================================================
    # == IRDAI Non-Payable Items (Expanded List)
    # =================================================================================
    {"id": "NP01", "name": "Baby Food and Products", "category": "Non-Payable Item"},
    {"id": "NP02", "name": "Water Bottle or Feeding Bottle", "category": "Non-Payable Item"},
    {"id": "NP03", "name": "Brush for Hair or Teeth", "category": "Non-Payable Item"},
    {"id": "NP04", "name": "Towel, Napkin or Serviette", "category": "Non-Payable Item"},
    {"id": "NP05", "name": "Talcum Powder or Dusting Powder", "category": "Non-Payable Item"},
    {"id": "NP06", "name": "Disposable Shoe Covers", "category": "Non-Payable Item"},
    {"id": "NP07", "name": "Beauty and Barber Services", "category": "Non-Payable Item"},
    {"id": "NP08", "name": "Cotton Buds", "category": "Non-Payable Item"},
    {"id": "NP09", "name": "Disposable Caps", "category": "Non-Payable Item"},
    {"id": "NP10", "name": "Cold Pack or Hot Pack", "category": "Non-Payable Item"},
    {"id": "NP11", "name": "Carry Bags", "category": "Non-Payable Item"},
    {"id": "NP12", "name": "Cradle or Baby Cot Charges", "category": "Non-Payable Item"},
    {"id": "NP13", "name": "Comb", "category": "Non-Payable Item"},
    {"id": "NP14", "name": "Room Fresheners or Deodorizers", "category": "Non-Payable Item"},
    {"id": "NP15", "name": "Eye Pad or Eye Shield", "category": "Non-Payable Item"},
    {"id": "NP16", "name": "Internet and WiFi Charges", "category": "Non-Payable Item"},
    {"id": "NP17", "name": "Food and Beverage charges for others", "category": "Non-Payable Item"},
    {"id": "NP18", "name": "Disposable Foot Covers", "category": "Non-Payable Item"},
    {"id": "NP19", "name": "Patient Gown", "category": "Non-Payable Item"},
    {"id": "NP20", "name": "Laundry or Washing Charges", "category": "Non-Payable Item"},
    {"id": "NP21", "name": "Mineral Water Charges", "category": "Non-Payable Item"},
    {"id": "NP22", "name": "Body Oil or Massage Oil", "category": "Non-Payable Item"},
    {"id": "NP23", "name": "Sanitary Pads or Tampons", "category": "Non-Payable Item"},
    {"id": "NP24", "name": "Slippers or Footwear", "category": "Non-Payable Item"},
    {"id": "NP25", "name": "Telephone Charges", "category": "Non-Payable Item"},
    {"id": "NP26", "name": "Tissue Paper or Wipes", "category": "Non-Payable Item"},
    {"id": "NP27", "name": "Toothpaste", "category": "Non-Payable Item"},
    {"id": "NP28", "name": "Guest Services", "category": "Non-Payable Item"},
    {"id": "NP29", "name": "Bed Pan", "category": "Non-Payable Item"},
    {"id": "NP30", "name": "Under Pads or Bed Protectors", "category": "Non-Payable Item"},
    {"id": "NP31", "name": "Camera Cover for Endoscopy/Laparoscopy", "category": "Non-Payable Item"},
    {"id": "NP32", "name": "Diapers or Nappies", "category": "Non-Payable Item"},
    {"id": "NP33", "name": "DVD or CD for storing medical records", "category": "Non-Payable Item"},
    {"id": "NP34", "name": "Eyelet Collar", "category": "Non-Payable Item"},
    {"id": "NP35", "name": "Disposable Face Mask", "category": "Non-Payable Item"},
    {"id": "NP36", "name": "Gauze or Dressing Pad", "category": "Non-Payable Item"},
    {"id": "NP37", "name": "Hansaplast or Adhesive Bandages", "category": "Non-Payable Item"},
    {"id": "NP38", "name": "Admission Kit", "category": "Non-Payable Item"},
    {"id": "NP39", "name": "Birth Certificate Charges", "category": "Non-Payable Item"},
    {"id": "NP40", "name": "Blood Reservation Charges", "category": "Non-Payable Item"},
    {"id": "NP41", "name": "Certificate or Documentation Charges", "category": "Non-Payable Item"},
    {"id": "NP42", "name": "Courier Charges", "category": "Non-Payable Item"},
    {"id": "NP43", "name": "Conveyance Charges for staff or visitors", "category": "Non-Payable Item"},
    {"id": "NP44", "name": "Diabetic Chart Charges", "category": "Non-Payable Item"},
    {"id": "NP45", "name": "Administrative Expenses", "category": "Non-Payable Item"},
    {"id": "NP46", "name": "Discharge Procedure Charges", "category": "Non-Payable Item"},
    {"id": "NP47", "name": "Daily Chart Charges", "category": "Non-Payable Item"},
    {"id": "NP48", "name": "Visitors Pass Charges", "category": "Non-Payable Item"},
    {"id": "NP49", "name": "File Opening or Registration Charges", "category": "Non-Payable Item"},
    {"id": "NP50", "name": "Incidental or Miscellaneous Charges", "category": "Non-Payable Item"},
    {"id": "NP51", "name": "Patient Identification Band or Name Tag", "category": "Non-Payable Item"},
    {"id": "NP52", "name": "Medicine Box or Container", "category": "Non-Payable Item"},
    {"id": "NP53", "name": "Medico-Legal Case (MLC) Charges", "category": "Non-Payable Item"},
    {"id": "NP54", "name": "Third Party Administrator (TPA) Charges", "category": "Non-Payable Item"},
    {"id": "NP55", "name": "Walking Aids like crutches or walkers", "category": "Non-Payable Item"},
    {"id": "NP56", "name": "Commode Chair", "category": "Non-Payable Item"},
    {"id": "NP57", "name": "Inhalation Spacer", "category": "Non-Payable Item"},
    {"id": "NP58", "name": "Armsling or Pouch Sling", "category": "Non-Payable Item"},
    {"id": "NP59", "name": "Thermometer", "category": "Non-Payable Item"},
    {"id": "NP60", "name": "Cervical Collar", "category": "Non-Payable Item"},
    {"id": "NP61", "name": "Splint", "category": "Non-Payable Item"},
    {"id": "NP62", "name": "Diabetic Foot Wear", "category": "Non-Payable Item"},
    {"id": "NP63", "name": "Knee Braces or Immobilizer", "category": "Non-Payable Item"},
    {"id": "NP64", "name": "Shoulder Immobilizer", "category": "Non-Payable Item"},
    {"id": "NP65", "name": "Ambulance Collar or Equipment", "category": "Non-Payable Item"},
    {"id": "NP66", "name": "Disposable Apron", "category": "Non-Payable Item"},
    {"id": "NP67", "name": "Alcohol Swabs", "category": "Non-Payable Item"},
    {"id": "NP68", "name": "Scrub Solution or Sterillium", "category": "Non-Payable Item"},
    {"id": "NP69", "name": "Examination Gloves", "category": "Non-Payable Item"},
    {"id": "NP70", "name": "Kidney Tray", "category": "Non-Payable Item"},
    {"id": "NP71", "name": "Oxygen Mask", "category": "Non-Payable Item"},
    {"id": "NP72", "name": "Paper Gloves", "category": "Non-Payable Item"},
    {"id": "NP73", "name": "Urine Container or Pot", "category": "Non-Payable Item"},
    {"id": "NP74", "name": "Softovac or Laxatives", "category": "Non-Payable Item"},
    {"id": "NP75", "name": "Accu-Chek or Glucometer Strips", "category": "Non-Payable Item"}
]


# == Policy Rulebook
# This dictionary simulates a database of insurance policy rules.
# =================================================================================
# app/master_data.py

# =================================================================================
# == MVP Policy Rulebook
# A single, detailed policy with an expanded list of 15 sub-limits.
# =================================================================================
# app/detailed_master_data.py

# This file contains a single, highly detailed policy rulebook with examples
# for Few-Shot Prompting to improve LLM accuracy.

POLICY_RULEBOOK = {
    "MVP1": {
        "policy_name": "MediSure Comprehensive MVP Plan",
        "sum_insured": 1000000,
        "co_payment_percentage": 10,
        "sub_limits": {
            # --- Existing 15 Rules ---
            "Room Charges": {
                "type": "percentage_of_sum_insured", "value": 1, "max_cap_per_day": 7500,
                "description": "Room Rent is capped at 1% of Sum Insured or up to a maximum of Rs. 7,500 per day whichever is minimum",
                "examples": ["Private A/C Room Rent", "General Ward Bed Charges", "Semi-Private Ward Stay", "Room and Board"]
            },
            "ICU Charges": {
                "type": "fixed", "value": 15000, "per": "day",
                "description": "Intensive Care Unit charges are capped at a maximum of Rs. 15,000 per day.",
                "examples": ["Intensive Care Unit Stay", "ICCU Charges", "Charges for NICU"]
            },
            "Doctor Consultation": {
                "type": "fixed", "value": 2000, "per": "day",
                "description": "Fees for doctor visits/consultations are capped at Rs. 2,000 per day.",
                "examples": ["Daily Doctor Visits", "Fee for Consulting Physician", "Dr. Sharma's Visit Fee"]
            },
            "Surgeon Fees": {
                "type": "percentage_of_surgery_cost", "value": 25,
                "description": "The lead surgeon's fee is capped at 25% of the total surgery cost.",
                "examples": ["Lead Surgeon Fee for Appendectomy", "Surgeon's Charges", "Operating Surgeon Fee"]
            },
            "Anesthetist Fees": {
                "type": "percentage_of_surgeon_fee", "value": 30,
                "description": "The anesthetist's fee is capped at 30% of the admissible surgeon's fee.",
                "examples": ["Anesthetist Charges", "Fee for Anesthesia Admin", "Anesthesiologist Fee"]
            },
            "Nursing Charges": {
                "type": "fixed", "value": 1000, "per": "day",
                "description": "Special nursing charges, if not part of room rent, are capped at Rs. 1,000 per day.",
                "examples": ["Special Nursing Care", "Private Nurse Charges", "Nursing Attendant Fee"]
            },
            "Pharmacy": {
                "type": "percentage_of_sum_insured", "value": 5, "per": "claim",
                "description": "Total pharmacy and medicine costs are capped at 5% of the Sum Insured for this claim.",
                "examples": ["Pharmacy and Medicines", "Medical Consumables", "Bill for Pharmacy Items"]
            },
            "Diagnostics": {
                "type": "percentage_of_sum_insured", "value": 7, "per": "claim",
                "description": "Total diagnostic costs (lab tests, X-rays, scans) are capped at 7% of the Sum Insured for this claim.",
                "examples": ["Diagnostic Tests (CT, Blood)", "Lab Investigations", "Charges for X-Ray and USG"]
            },
            "Ambulance": {
                "type": "fixed", "value": 3000, "per": "hospitalization",
                "description": "Ambulance charges are covered up to a fixed amount of Rs. 3,000 per hospitalization.",
                "examples": ["Ambulance Service", "Patient Transport Vehicle", "Emergency Ambulance"]
            },
            "Pre-Hospitalization": {
                "type": "fixed", "value": 15000, "per": "hospitalization", "days_covered": 30,
                "description": "Medical expenses incurred up to 30 days before hospitalization are capped at Rs. 15,000.",
                "examples": ["Pre-Hosp OPD Consultation", "Medicines before admission"]
            },
            "Post-Hospitalization": {
                "type": "fixed", "value": 25000, "per": "hospitalization", "days_covered": 60,
                "description": "Medical expenses incurred up to 60 days after discharge are capped at Rs. 25,000.",
                "examples": ["Follow-up visit after discharge", "Post-op medication"]
            },
            "Domiciliary Hospitalization": {
                "type": "percentage_of_sum_insured", "value": 10, "per": "claim",
                "description": "Treatment taken at home is covered up to 10% of the Sum Insured.",
                "examples": ["Home Care Treatment Charges", "Hospitalization at Home"]
            },
            "AYUSH Treatment": {
                "type": "fixed", "value": 20000, "per": "claim",
                "description": "In-patient treatment under Ayurveda, Yoga, Unani, Siddha, and Homeopathy is capped at Rs. 20,000.",
                "examples": ["Ayurvedic Hospitalization", "Homeopathy In-patient care"]
            },
            "Maternity": {
                "type": "fixed_package", "normal_delivery": 35000, "c_section_delivery": 50000,
                "description": "A fixed package amount is paid for maternity expenses, inclusive of all related charges.",
                "examples": ["Normal Delivery Package", "Caesarean Section Charges", "Maternity Bill"]
            },
            "Cataract Surgery": {
                "type": "fixed", "value": 40000, "per": "eye",
                "description": "Cataract surgery is capped at a fixed amount of Rs. 40,000 per eye, per policy year.",
                "examples": ["Cataract Surgery - Left Eye", "Phacoemulsification with IOL"]
            },

            # --- Newly Added 15 Rules ---
            "Health Checkup": {
                "type": "fixed", "value": 5000, "per": "year",
                "description": "Cost of a preventive health check-up is covered up to Rs. 5,000 per policy year.",
                "examples": ["Annual Health Check", "Preventive Screening", "Master Health Checkup"]
            },
            "Organ Donor Expenses": {
                "type": "percentage_of_sum_insured", "value": 20, "max_cap": 200000, "per": "claim",
                "description": "Expenses for organ harvesting for a transplant are covered up to 20% of SI, max Rs. 2 Lakh.",
                "examples": ["Organ Harvesting Charges", "Donor Surgery Expenses"]
            },
            "Dental Treatment (Accidental)": {
                "type": "fixed", "value": 30000, "per": "claim",
                "description": "Dental treatment required due to an accident is covered up to Rs. 30,000.",
                "examples": ["Accidental Dental Surgery", "Jaw fracture treatment"]
            },
            "Bariatric Surgery": {
                "type": "fixed_package", "value": 250000,
                "description": "A fixed package amount is paid for bariatric surgery if medically necessary.",
                "examples": ["Weight Loss Surgery", "Bariatric Procedure"]
            },
            "Prosthetics (Artificial Limbs)": {
                "type": "percentage_of_sum_insured", "value": 15, "max_cap": 150000, "per": "claim",
                "description": "Cost of artificial limbs is covered up to 15% of SI, max Rs. 1.5 Lakh.",
                "examples": ["Prosthetic Limb Cost", "Artificial Hand/Leg"]
            },
            "Psychiatric Treatment": {
                "type": "fixed", "value": 50000, "per": "year",
                "description": "In-patient hospitalization for psychiatric treatment is capped at Rs. 50,000 per year.",
                "examples": ["Psychiatric Care", "Mental Illness Hospitalization"]
            },
            "Chemotherapy": {
                "type": "percentage_of_sum_insured", "value": 50, "per": "claim",
                "description": "Chemotherapy charges are covered up to 50% of the Sum Insured.",
                "examples": ["Chemotherapy Session", "Cancer Chemo Treatment"]
            },
            "Dialysis": {
                "type": "fixed", "value": 3000, "per": "session",
                "description": "Dialysis is capped at Rs. 3,000 per session.",
                "examples": ["Kidney Dialysis", "Hemodialysis Charges"]
            },
            "Road Traffic Accident (RTA)": {
                "type": "percentage_of_sum_insured", "value": 100,
                "description": "Hospitalization due to a road traffic accident is covered up to the full sum insured.",
                "examples": ["RTA Injury Treatment", "Accident and Emergency Care"]
            },
            "Joint Replacement Surgery": {
                "type": "fixed_package", "value": 200000, "per": "joint",
                "description": "A fixed package for joint replacement surgery (e.g., knee, hip) is paid.",
                "examples": ["Total Knee Replacement", "Hip Replacement Surgery"]
            },
            "Physiotherapy": {
                "type": "fixed", "value": 500, "per": "session", "max_sessions": 15,
                "description": "Post-hospitalization physiotherapy is capped at Rs. 500 per session for a max of 15 sessions.",
                "examples": ["Physiotherapy Session", "Rehabilitation Therapy"]
            },
            "Hearing Aids": {
                "type": "percentage_of_sum_insured", "value": 5, "max_cap": 25000,
                "description": "Cost of hearing aids is covered up to 5% of SI, max Rs. 25,000.",
                "examples": ["Hearing Aid Device Cost", "Audiometry Services"]
            },
            "Day Care Procedures": {
                "type": "percentage_of_sum_insured", "value": 100,
                "description": "Covers specified surgical procedures that do not require 24-hour hospitalization.",
                "examples": ["Day Care Surgery", "Minor Surgical Procedure"]
            },
            "Emergency Evacuation": {
                "type": "fixed", "value": 75000, "per": "claim",
                "description": "Cost of emergency air ambulance or evacuation is covered up to Rs. 75,000.",
                "examples": ["Air Ambulance", "Medical Evacuation"]
            },
            "Second Medical Opinion": {
                "type": "fixed", "value": 5000, "per": "year",
                "description": "Cost of obtaining a second medical opinion from another doctor is covered up to Rs. 5,000.",
                "examples": ["Second Opinion Consultation", "Medical Review"]
            }
        }
    }
}

