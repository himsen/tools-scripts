#!/usr/bin/env python3

import argparse
import json
import os
import requests
import sys

class CloudflareState:
    def __init__(self, api_token, account_id=None, db_name=None, db_table_name=None, db_uuid=None):
        self.api_token = api_token
        self.account_id = account_id or self.get_account_id()
        self.db_name = db_name
        self.db_table_name = db_table_name
        self.db_uuid = db_uuid

    def to_dict(self):
        """Convert the state to a dictionary, including first 5 chars of the API token."""
        return {
            'account_id': self.account_id,
            'api_token': self.api_token[:5] + "*****",  # Show only the first 5 characters
            'db_name': self.db_name,
            'db_table_name': self.db_table_name,
            'db_uuid': self.db_uuid
        }

    def dump(self):
        """Dump the state content with only first 5 chars of the API token."""
        state_dict = self.to_dict()
        # Print or return the state dictionary including the masked API token
        return json.dumps(state_dict, indent=2)

    def get_account_id(self):
        """Fetch Cloudflare Account ID using the API token."""
        url = "https://api.cloudflare.com/client/v4/accounts"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            accounts = response.json().get("result", [])
            if accounts:
                return accounts[0]["id"]
            else:
                print("Error: No Cloudflare accounts found.")
                exit(1)
        else:
            print(f"Failed to fetch Cloudflare account ID: {response.text}")
            exit(1)

def create_d1_database(state, prod=False):
    """Create a new D1 database using Cloudflare's API."""
    if not state.db_name:
        print("Error: Database name is required for creating the D1 database.")
        exit(1)

    url = f"https://api.cloudflare.com/client/v4/accounts/{state.account_id}/d1/database"
    headers = {
        "Authorization": f"Bearer {state.api_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "name": state.db_name,
        "mode": "create",
    }

    response = requests.post(url, json=payload, headers=headers)

    if prod:
        if response.status_code == 200:
            print(f"D1 database '{state.db_name}' created successfully!")
        else:
            print(f"Failed to create D1 database: {response.text}")
            print(state.dump())
    else:
        print(f"[DRY RUN] database create request: {url}")
        print(state.dump())

def create_table_if_not_exists(table_name):
    """Create the table if it doesn't exist."""
    sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        product_name TEXT,
        pet_life_stage TEXT,
        ingredients TEXT,
        primary_protein TEXT,
        sensitive_stomach BOOLEAN,
        manufacturer TEXT,
        price REAL,
        package_size REAL,
        form_factor TEXT,
        reference_url TEXT,
        created_at TEXT,
        product_image_url TEXT
    );
    """
    return sql

def get_database_uuid(state):
    """Retrieve the UUID of a D1 database by name and store it in the state."""
    # Cloudflare API settings
    url = f"https://api.cloudflare.com/client/v4/accounts/{state.account_id}/d1/database"
    headers = {
        "Authorization": f"Bearer {state.api_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "name": state.db_name,
    }
    response = requests.get(url, json=payload, headers=headers)

    if response.status_code == 200:
        # Search for the database with the specified name
        databases = response.json()['result']
        for db in databases:
            if db['name'] == state.db_name:
                # Save the database UUID to state
                state.db_uuid = db['uuid']
                print(f"Database UUID for '{state.db_name}' is {state.db_uuid}")
                return
        print(f"Database '{state.db_name}' not found.")
    else:
        print(f"Failed to retrieve databases: {response.text}")
        print(state.dump())

def upload_data_to_d1(state, data, prod=False):
    """Upload the JSON data to D1 database."""
    url = f"https://api.cloudflare.com/client/v4/accounts/{state.account_id}/d1/database/{state.db_uuid}/query"
    headers = {
        "Authorization": f"Bearer {state.api_token}",
        "Content-Type": "application/json",
    }

    # SQL to create table if not exists
    create_table_sql = create_table_if_not_exists(state.db_table_name)
    payload = {"sql": create_table_sql}

    # Create the table if it doesn't exist
    if prod:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            print(f"Table {state.db_table_name} created or already exists.")
        else:
            print(f"Failed to create table {state.db_table_name}: {response.text}")
            print(state.dump())

    # Insert data into the table
    for product in data:
        sql = f"""
        INSERT INTO {state.db_table_name} (
            product_name, pet_life_stage, ingredients, primary_protein, 
            sensitive_stomach, manufacturer, price, package_size, form_factor, 
            reference_url, created_at, product_image_url
        ) VALUES (
            '{product['product_name']}', '{product['pet_life_stage']}', 
            '{json.dumps(product['ingredients'])}', '{product['primary_protein']}', 
            {str(product['sensitive_stomach']).lower()}, '{product['manufacturer']}', 
            {product['price']}, {product['package_size']}, '{product['form_factor']}', 
            '{product['reference_url']}', '{product['created_at']}', 
            '{product['product_image_url']}'
        );
        """

        payload = {"sql": sql}
        
        if prod:
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                print(f"Uploaded product: {product['product_name']}")
            else:
                print(f"Failed to upload {product['product_name']}: {response.text}")
                print(state.dump())
        else:
            print(f"[DRY RUN] SQL: {sql}")
            print(state.dump())


def load_json(file_path):
    """Load JSON data from a file."""
    with open(file_path, "r") as f:
        return json.load(f)

def show_json(data):
    """Display the parsed JSON content."""
    print(json.dumps(data, indent=2))

def main():
    """Main function to handle argument parsing and execution."""
    parser = argparse.ArgumentParser(description="Cat Food Product Uploader")
    parser.add_argument("--create-db", action="store_true", help="Create the D1 database")
    parser.add_argument("--upload-data", action="store_true", help="Upload data to the D1 database")
    parser.add_argument("--prod", action="store_true", help="Execute actual upload (otherwise dry-run)")
    parser.add_argument("--file", type=str, help="Path to the JSON file", required=True)
    parser.add_argument("--db-name", type=str, help="The D1 database name", required=True)

    # Conditionally add --db-name as a required argument if --create-db is used
    parser.add_argument("--db-table-name", type=str, help="The D1 database table name", required=('--upload-data' in sys.argv))

    args = parser.parse_args()

    # Check for Cloudflare API token in the environment
    CF_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
    if not CF_API_TOKEN:
        print("Error: CLOUDFLARE_API_TOKEN environment variable is not set.")
        exit(1)

    # Create a CloudflareState instance
    state = CloudflareState(api_token=CF_API_TOKEN, db_name=args.db_name, db_table_name=args.db_table_name)

    # Load the JSON data
    data = load_json(args.file)

    if not args.prod:
        show_json(data)

    if args.create_db :
        create_d1_database(state, prod=args.prod)

    get_database_uuid(state)

    if args.upload_data:
        upload_data_to_d1(state, data, prod=args.prod)

if __name__ == "__main__":
    main()
