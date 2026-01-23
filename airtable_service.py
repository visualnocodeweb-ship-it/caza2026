import os
from airtable import Airtable

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY", "YOUR_AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "app2WxKfUMvO4oj5q") # User's provided Base ID
AIRTABLE_PRICE_TABLE_NAME = os.getenv("AIRTABLE_PRICE_TABLE_NAME", "tbl3tpeIUcsFQV7TT") # User's provided Table ID

def get_current_price() -> float:
    """
    Fetches the current price for "Inscripcion" from Airtable.
    Assumes a table identified by AIRTABLE_PRICE_TABLE_NAME with a column 'Tipo'
    to identify the item (e.g., 'Inscripcion') and a column 'Valores' that holds the price.
    """
    try:
        airtable = Airtable(AIRTABLE_BASE_ID, AIRTABLE_PRICE_TABLE_NAME, AIRTABLE_API_KEY)
        
        # Filter for the record where 'Tipo' is "Inscripcion"
        # The filterByFormula syntax needs to match Airtable's exact field name.
        records = airtable.get_all(formula="{Tipo} = 'Inscripcion'") 

        if records and 'fields' in records[0] and 'Valores' in records[0]['fields']:
            price = float(records[0]['fields']['Valores'])
            print(f"Fetched price from Airtable: {price}")
            return price
        else:
            print("No price found for 'Inscripcion' in Airtable or 'Valores' field missing. Using default.")
            return 10.00 # Fallback to default price for Inscripcion
    except Exception as e:
        print(f"Error fetching price from Airtable: {e}. Using default price.")
        return 10.00 # Fallback to default price
