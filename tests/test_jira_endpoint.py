#!/usr/bin/env python3
"""
Test script for the Jira issue endpoint.

Usage: 
  python -m tests.test_jira_endpoint --id PROJECT-123
  python -m tests.test_jira_endpoint --url https://your-domain.atlassian.net/browse/PROJECT-123
"""

import sys
import requests
import json
import argparse

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test the Jira issue endpoint')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--id', help='Jira issue ID (e.g., PROJECT-123)')
    group.add_argument('--url', help='URL to the Jira issue')
    args = parser.parse_args()
    
    # Prepare the request payload
    payload = {}
    if args.id:
        print(f"Fetching information for issue ID: {args.id}")
        payload['issueId'] = args.id
    else:
        print(f"Fetching information for issue URL: {args.url}")
        payload['issueUrl'] = args.url
    
    url = "http://localhost:8000/jira/issue"
    
    try:
        response = requests.post(url, json=payload)
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\nResponse:")
            print(json.dumps(data, indent=2))
            print(f"\nMessage: {data.get('message', '')}")
        else:
            print(f"Error: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the API server. Make sure it's running.")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()