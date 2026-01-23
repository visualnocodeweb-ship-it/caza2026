import os
from airtable import Airtable

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY", "YOUR_AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "YOUR_AIRTABLE_BASE_ID")
AIRTABLE_PRICE_TABLE_NAME = os.getenv("AIRTABLE_PRICE_TABLE_NAME", "Prices") # Assuming a table named 'Prices'

def get_current_price() -> float:
    """
    Fetches the current price from Airtable.
    Assumes a table named 'Prices' with a field 'Price' that holds the value.
    For simplicity, fetches the first record and takes its 'Price' field.
    """
    try:
        airtable = Airtable(AIRTABLE_BASE_ID, AIRTABLE_PRICE_TABLE_NAME, AIRTABLE_API_KEY)
        # Fetch records. You might want to filter this based on a 'Name' or 'Activity' field
        # For now, we'll just take the first record's price.
        records = airtable.get_all(maxRecords=1) 
        if records and 'fields' in records[0] and 'Price' in records[0]['fields']:
            price = float(records[0]['fields']['Price'])
            print(f"Fetched price from Airtable: {price}")
            return price
        else:
            print("No price found in Airtable or 'Price' field missing. Using default.")
            return 100.00 # Fallback to default price
    except Exception as e:
        print(f"Error fetching price from Airtable: {e}. Using default price.")
        return 100.00 # Fallback to default price
