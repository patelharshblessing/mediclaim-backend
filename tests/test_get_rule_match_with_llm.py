# code to test the LLM-based rule matching
if __name__ == "__main__":
    import asyncio

    # Example item description and sub_limits
    item_description = "Room Charges"
    sub_limits = {
        "Room Charges": {
            "type": "percentage_of_sum_insured",
            "value": 1,
            "max_cap_per_day": 7500,
            "description": "Room Rent is capped at 1% of Sum Insured, up to a maximum of Rs. 7,500 per day.",
        },
        # 2. ICU Charges
        "ICU Charges": {
            "type": "fixed",
            "value": 15000,
            "description": "Intensive Care Unit charges are capped at a maximum of Rs. 15,000 per day.",
        },
        # 3. Doctor's Consultation Fees
        "Doctor Consultation": {
            "type": "fixed",
            "value": 2000,
            "per": "day",
            "description": "Fees for doctor visits/consultations are capped at Rs. 2,000 per day.",
        },
        # 4. Surgeon Fees
        "Surgeon Fees": {
            "type": "percentage_of_surgery_cost",
            "value": 25,
            "description": "The lead surgeon's fee is capped at 25% of the total surgery cost.",
        },
        # 5. Anesthetist Fees
        "Anesthetist Fees": {
            "type": "percentage_of_surgeon_fee",
            "value": 30,
            "description": "The anesthetist's fee is capped at 30% of the admissible surgeon's fee.",
        },
        # 6. Nursing Charges
        "Nursing Charges": {
            "type": "fixed",
            "value": 1000,
            "per": "day",
            "description": "Special nursing charges, if not part of room rent, are capped at Rs. 1,000 per day.",
        },
        # 7. Pharmacy & Medicines
        "Pharmacy": {
            "type": "percentage_of_sum_insured",
            "value": 5,
            "per": "claim",
            "description": "Total pharmacy and medicine costs are capped at 5% of the Sum Insured for this claim.",
        },
        # 8. Diagnostic Tests (Lab & Imaging)
        "Diagnostics": {
            "type": "percentage_of_sum_insured",
            "value": 7,
            "per": "claim",
            "description": "Total diagnostic costs (lab tests, X-rays, scans) are capped at 7% of the Sum Insured for this claim.",
        },
        # 9. Ambulance Charges
        "Ambulance": {
            "type": "fixed",
            "value": 3000,
            "per": "hospitalization",
            "description": "Ambulance charges are covered up to a fixed amount of Rs. 3,000 per hospitalization.",
        },
        # 10. Pre-Hospitalization Expenses
        "Pre-Hospitalization": {
            "type": "fixed",
            "value": 15000,
            "per": "hospitalization",
            "days_covered": 30,
            "description": "Medical expenses incurred up to 30 days before hospitalization are capped at Rs. 15,000.",
        },
        # 11. Post-Hospitalization Expenses
        "Post-Hospitalization": {
            "type": "fixed",
            "value": 25000,
            "per": "hospitalization",
            "days_covered": 60,
            "description": "Medical expenses incurred up to 60 days after discharge are capped at Rs. 25,000.",
        },
        # 12. Domiciliary Hospitalization (Treatment at home)
        "Domiciliary Hospitalization": {
            "type": "percentage_of_sum_insured",
            "value": 10,
            "per": "claim",
            "description": "Treatment taken at home is covered up to 10% of the Sum Insured.",
        },
        # 13. AYUSH Treatment
        "AYUSH Treatment": {
            "type": "fixed",
            "value": 20000,
            "per": "claim",
            "description": "In-patient treatment under Ayurveda, Yoga, Unani, Siddha, and Homeopathy is capped at Rs. 20,000.",
        },
        # 14. Maternity Benefit (Package Rate)
        "Maternity": {
            "type": "fixed_package",
            "normal_delivery": 35000,
            "c_section_delivery": 50000,
            "description": "A fixed package amount is paid for maternity expenses, inclusive of all related charges.",
        },
        # 15. Cataract Surgery
        "Cataract Surgery": {
            "type": "fixed",
            "value": 40000,
            "per": "eye",
            "description": "Cataract surgery is capped at a fixed amount of Rs. 40,000 per eye, per policy year.",
        },
    }

    # Run the LLM-based rule matching
    async def main():
        rule_name = await get_rule_match_with_llm(item_description, sub_limits)
        print(f"Matched Rule: {rule_name}")

    asyncio.run(main())
