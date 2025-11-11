import sqlite3
from sqlalchemy import create_engine
import pandas as pd

DB_PATH = 'data/options.db'
engine = create_engine(f'sqlite:///{DB_PATH}')

def save_to_db(df, table_name):
    """
    Saves a DataFrame to a table in the SQLite database.
    Replaces the table if it already exists.
    """
    if df.empty:
        print(f"Skipping save for {table_name}: DataFrame is empty.")
        return
        
    try:
        df.to_sql(table_name, con=engine, if_exists='replace', index=False)
        print(f"Successfully saved {len(df)} rows to '{table_name}' in {DB_PATH}")
    except Exception as e:
        print(f"Error saving to database: {e}")

def load_from_db(query):
    """Loads data from the database using a SQL query."""
    try:
        with engine.connect() as conn:
            return pd.read_sql(query, con=conn)
    except Exception as e:
        print(f"Error loading from database: {e}")
        return pd.DataFrame()