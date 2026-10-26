"""
Generate messy test datasets and their corresponding ground-truth clean versions.
Injected problems:
- Missing values (numeric & categorical)
- Duplicate rows
- Invalid values (e.g., negative or extreme age)
- Inconsistent categorical values (e.g., gender casing/abbreviations)
- Numeric values stored as strings with symbols ('$1,200', 'N/A')
- Mixed date formats
- Unit inconsistencies (e.g., weight in kg vs lbs)
- Extreme outliers (e.g., salary = 10,000,000)
"""

from pathlib import Path
import pandas as pd
import numpy as np

SAMPLE_DIR = Path(__file__).resolve().parent
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)


def generate_customers():
    # Ground Truth Clean
    clean_data = [
        {"customer_id": 101, "name": "Alice Smith", "age": 28, "gender": "Female", "signup_date": "2023-01-15", "annual_spend": 1250.50, "loyalty_score": 85},
        {"customer_id": 102, "name": "Bob Johnson", "age": 42, "gender": "Male", "signup_date": "2022-06-20", "annual_spend": 3400.00, "loyalty_score": 92},
        {"customer_id": 103, "name": "Charlie Brown", "age": 35, "gender": "Male", "signup_date": "2023-03-12", "annual_spend": 560.20, "loyalty_score": 60},
        {"customer_id": 104, "name": "Diana Prince", "age": 31, "gender": "Female", "signup_date": "2021-11-05", "annual_spend": 4500.00, "loyalty_score": 98},
        {"customer_id": 105, "name": "Evan Wright", "age": 50, "gender": "Male", "signup_date": "2023-08-01", "annual_spend": 2100.75, "loyalty_score": 74},
        {"customer_id": 106, "name": "Fiona Gallagher", "age": 24, "gender": "Female", "signup_date": "2023-09-14", "annual_spend": 890.00, "loyalty_score": 65},
        {"customer_id": 107, "name": "George Clark", "age": 39, "gender": "Male", "signup_date": "2022-12-10", "annual_spend": 1780.00, "loyalty_score": 80},
        {"customer_id": 108, "name": "Hannah Abbott", "age": 29, "gender": "Female", "signup_date": "2024-02-18", "annual_spend": 3200.50, "loyalty_score": 88},
        {"customer_id": 109, "name": "Ian Malcolm", "age": 46, "gender": "Male", "signup_date": "2020-04-22", "annual_spend": 5100.00, "loyalty_score": 95},
        {"customer_id": 110, "name": "Julia Roberts", "age": 33, "gender": "Female", "signup_date": "2023-05-30", "annual_spend": 1950.25, "loyalty_score": 79},
    ]
    df_clean = pd.DataFrame(clean_data)
    df_clean.to_csv(SAMPLE_DIR / "customers_clean.csv", index=False)

    # Messy version with injected anomalies
    messy_data = [
        {"customer_id": 101, "name": "Alice Smith ", "age": 28, "gender": "Female", "signup_date": "2023-01-15", "annual_spend": "$1,250.50", "loyalty_score": 85},
        {"customer_id": 102, "name": "Bob Johnson", "age": -5, "gender": "M", "signup_date": "06/20/2022", "annual_spend": "3400.00", "loyalty_score": 92}, # invalid age, date format, gender code
        {"customer_id": 103, "name": "Charlie Brown", "age": 35, "gender": "male", "signup_date": "2023-03-12", "annual_spend": "560.20", "loyalty_score": None}, # missing loyalty_score
        {"customer_id": 104, "name": "Diana Prince", "age": 150, "gender": "F", "signup_date": "Nov 5, 2021", "annual_spend": "$4,500.00", "loyalty_score": 98}, # invalid age 150, date format
        {"customer_id": 105, "name": "Evan Wright", "age": 50, "gender": "Male", "signup_date": "2023-08-01", "annual_spend": "2100.75", "loyalty_score": 74},
        {"customer_id": 105, "name": "Evan Wright", "age": 50, "gender": "Male", "signup_date": "2023-08-01", "annual_spend": "2100.75", "loyalty_score": 74}, # exact duplicate row
        {"customer_id": 106, "name": "  fiona gallagher", "age": None, "gender": "female", "signup_date": "2023-09-14", "annual_spend": "890.00", "loyalty_score": 65}, # missing age, dirty text
        {"customer_id": 107, "name": "George Clark", "age": 39, "gender": "MALE ", "signup_date": "2022-12-10", "annual_spend": "1780.00", "loyalty_score": 80},
        {"customer_id": 108, "name": "Hannah Abbott", "age": 29, "gender": "Female", "signup_date": "2024-02-18", "annual_spend": "N/A", "loyalty_score": 88}, # N/A in spend
        {"customer_id": 109, "name": "Ian Malcolm", "age": 46, "gender": "m", "signup_date": "2020-04-22", "annual_spend": "$5,100", "loyalty_score": 95},
        {"customer_id": 110, "name": "Julia Roberts", "age": 33, "gender": None, "signup_date": "2023-05-30", "annual_spend": "1950.25", "loyalty_score": 79}, # missing gender
    ]
    df_messy = pd.DataFrame(messy_data)
    df_messy.to_csv(SAMPLE_DIR / "customers_messy.csv", index=False)


def generate_employees():
    clean_data = [
        {"emp_id": "E01", "department": "Engineering", "role": "Senior Engineer", "years_experience": 8, "salary": 115000, "status": "Active"},
        {"emp_id": "E02", "department": "Marketing", "role": "Marketing Specialist", "years_experience": 4, "salary": 68000, "status": "Active"},
        {"emp_id": "E03", "department": "Engineering", "role": "Software Engineer", "years_experience": 3, "salary": 92000, "status": "Active"},
        {"emp_id": "E04", "department": "Sales", "role": "Account Executive", "years_experience": 5, "salary": 75000, "status": "Active"},
        {"emp_id": "E05", "department": "Finance", "role": "Financial Analyst", "years_experience": 6, "salary": 85000, "status": "On Leave"},
        {"emp_id": "E06", "department": "Engineering", "role": "Staff Engineer", "years_experience": 12, "salary": 160000, "status": "Active"},
        {"emp_id": "E07", "department": "Sales", "role": "Sales Associate", "years_experience": 1, "salary": 52000, "status": "Active"},
        {"emp_id": "E08", "department": "Human Resources", "role": "HR Generalist", "years_experience": 5, "salary": 64000, "status": "Active"},
    ]
    df_clean = pd.DataFrame(clean_data)
    df_clean.to_csv(SAMPLE_DIR / "employees_clean.csv", index=False)

    messy_data = [
        {"emp_id": "E01", "department": "engineering", "role": "Senior Engineer", "years_experience": 8, "salary": 115000, "status": "Active"},
        {"emp_id": "E02", "department": "Marketing ", "role": "marketing specialist", "years_experience": 4, "salary": "68000", "status": "Active"},
        {"emp_id": "E03", "department": "Engineering", "role": "Software Engineer", "years_experience": -2, "salary": 92000, "status": "Active"}, # negative experience
        {"emp_id": "E04", "department": "Sales", "role": "Account Executive", "years_experience": 5, "salary": 10000000, "status": "Active"}, # huge outlier 10 million
        {"emp_id": "E05", "department": "Finance", "role": "Financial Analyst", "years_experience": None, "salary": 85000, "status": "On Leave"}, # missing experience
        {"emp_id": "E06", "department": "ENGINEERING", "role": "Staff Engineer", "years_experience": 12, "salary": 160000, "status": "active"},
        {"emp_id": "E07", "department": "Sales", "role": "Sales Associate", "years_experience": 1, "salary": 52000, "status": "Active"},
        {"emp_id": "E07", "department": "Sales", "role": "Sales Associate", "years_experience": 1, "salary": 52000, "status": "Active"}, # duplicate
        {"emp_id": "E08", "department": "HR", "role": "HR Generalist", "years_experience": 5, "salary": "64,000", "status": "Active"}, # comma in salary, inconsistent HR
    ]
    df_messy = pd.DataFrame(messy_data)
    df_messy.to_csv(SAMPLE_DIR / "employees_messy.csv", index=False)


def generate_products():
    clean_data = [
        {"sku": "PRD-01", "name": "Wireless Mouse", "category": "Electronics", "price": 29.99, "weight_kg": 0.15, "in_stock": True},
        {"sku": "PRD-02", "name": "Ergonomic Keyboard", "category": "Electronics", "price": 89.50, "weight_kg": 0.85, "in_stock": True},
        {"sku": "PRD-03", "name": "Office Desk Lamp", "category": "Home & Office", "price": 45.00, "weight_kg": 1.20, "in_stock": False},
        {"sku": "PRD-04", "name": "USB-C Charging Cable", "category": "Electronics", "price": 14.99, "weight_kg": 0.08, "in_stock": True},
        {"sku": "PRD-05", "name": "Stainless Water Bottle", "category": "Kitchen", "price": 22.00, "weight_kg": 0.40, "in_stock": True},
        {"sku": "PRD-06", "name": "Noise Cancelling Headphones", "category": "Electronics", "price": 199.99, "weight_kg": 0.32, "in_stock": True},
    ]
    df_clean = pd.DataFrame(clean_data)
    df_clean.to_csv(SAMPLE_DIR / "products_clean.csv", index=False)

    messy_data = [
        {"sku": "PRD-01", "name": "Wireless Mouse ", "category": "electronics", "price": "$29.99", "weight_kg": "0.15 kg", "in_stock": "TRUE"},
        {"sku": "PRD-02", "name": "Ergonomic Keyboard", "category": "Electronics", "price": "89.50", "weight_kg": 0.85, "in_stock": "yes"},
        {"sku": "PRD-03", "name": "Office Desk Lamp", "category": "Home & Office", "price": None, "weight_kg": "1.2", "in_stock": "False"}, # missing price
        {"sku": "PRD-04", "name": "USB-C Charging Cable", "category": "ELECTRONICS", "price": "14.99 USD", "weight_kg": "0.08", "in_stock": "True"},
        {"sku": "PRD-05", "name": "Stainless Water Bottle", "category": "Kitchen", "price": "22.00", "weight_kg": "0.88 lbs", "in_stock": "True"}, # lbs unit inconsistency
        {"sku": "PRD-06", "name": "Noise Cancelling Headphones", "category": "Electronics", "price": -199.99, "weight_kg": 0.32, "in_stock": "True"}, # negative price
        {"sku": "PRD-01", "name": "Wireless Mouse ", "category": "electronics", "price": "$29.99", "weight_kg": "0.15 kg", "in_stock": "TRUE"}, # duplicate
    ]
    df_messy = pd.DataFrame(messy_data)
    df_messy.to_csv(SAMPLE_DIR / "products_messy.csv", index=False)


if __name__ == "__main__":
    generate_customers()
    generate_employees()
    generate_products()
    print("Generated 3 messy and clean test datasets in sample_data/")
