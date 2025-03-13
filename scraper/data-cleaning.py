import pandas as pd
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)

file_path = r"C:\Users\d.tanubudhi\amazon_sales_estimation\scraper\2025Jan1-2025Feb28CustomUnifiedTransaction.csv"
df = pd.read_csv(file_path)

df = df[~df['type'].isin(['Amazon Fees', 'FBA Inventory Fee'])]

df.columns = df.columns.str.replace(' ', '_')

df['data_time'] = pd.to_datetime(df['date/time'], errors='coerce')

numerical_columns = [
    'quantity', 'product_sales', 'product_sales_tax', 'shipping_credits',
    'shipping_credits_tax', 'gift_wrap_credits', 'giftwrap_credits_tax', 'Regulatory_Fee',
    'Tax_On_Regulatory_Fee', 'promotional_rebates', 'promotional_rebates_tax',
    'marketplace_withheld_tax', 'selling_fees', 'fba_fees', 'other_transaction_fees',
    'other', 'total'
]

for col in numerical_columns:
    df[col] = df[col].astype('category')

df['sales'] = (
    df.get('product_sales', 0).astype(float) +
    df.get('product_sales_tax', 0).astype(float) +
    df.get('shipping_credits', 0).astype(float) +
    df.get('shipping_credits_tax', 0).astype(float) +
    df.get('gift_wrap_credits', 0).astype(float) +
    df.get('giftwrap_credits_tax', 0).astype(float) +
    df.get('Regulatory_Fee', 0).astype(float)
).round(2)

df['discounts'] = (
    df.get('promotional_rebates', 0).astype(float) + 
    df.get('promotional_rebates_tax', 0).astype(float)
).round(2)

df['amazon_fee'] = (
    df.get('marketplace_withheld_tax', 0).astype(float) +
    df.get('selling_fees', 0).astype(float)
).round(2)

columns_to_remove = [
    'product_sales', 'product_sales_tax', 'shipping_credits',
    'shipping_credits_tax', 'gift_wrap_credits', 'giftwrap_credits_tax', 'Regulatory_Fee',
    'Tax_On_Regulatory_Fee', 'promotional_rebates', 'promotional_rebates_tax',
    'marketplace_withheld_tax', 'selling_fees'
]

df.drop(columns=columns_to_remove, inplace=True, errors='ignore')

output_file_path = r"C:\Users\d.tanubudhi\amazon_sales_estimation\scraper\cleaned_transaction_data.csv"
df.to_csv(output_file_path, index=False)
print(f"Cleaned data saved to: {output_file_path}")