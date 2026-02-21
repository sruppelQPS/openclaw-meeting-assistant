#!/usr/bin/env python3
"""
Odoo integration
- Match speakers to Odoo contacts
- Create tasks from action items (after review!)
"""

import os
import json
import xmlrpc.client
from typing import Dict, List, Optional
from pathlib import Path
from fuzzywuzzy import process

class OdooConnector:
    """Connect to Odoo and manage tasks"""
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Load Odoo config from existing openclaw setup
        config_path = os.path.expanduser(config.get('config_path'))
        contacts_path = os.path.expanduser(config.get('contacts_path'))
        
        with open(config_path, 'r') as f:
            odoo_config = json.load(f)
        
        self.url = odoo_config['url']
        self.db = odoo_config['db']
        self.username = odoo_config['username']
        self.api_key = odoo_config['api_key']
        
        # Load contacts for fuzzy matching
        with open(contacts_path, 'r') as f:
            self.contacts = json.load(f)
        
        # Connect to Odoo
        self.common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
        self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
        self.uid = self.common.authenticate(self.db, self.username, self.api_key, {})
        
        print(f"✅ Odoo verbunden: {self.url}")
        print(f"   Kontakte geladen: {len(self.contacts)}")
    
    def match_speaker(self, speaker_name: str, threshold: int = 80) -> Optional[Dict]:
        """
        Match speaker name to Odoo contact using fuzzy matching
        
        Args:
            speaker_name: Name from transcript (e.g., "Max", "Anna Meyer")
            threshold: Minimum similarity score (0-100)
        
        Returns:
            Dict with matched contact or None
        """
        # Try exact match first
        if speaker_name in self.contacts:
            return self.contacts[speaker_name]
        
        # Fuzzy match
        match = process.extractOne(speaker_name, self.contacts.keys(), score_cutoff=threshold)
        
        if match:
            matched_name = match[0]
            score = match[1]
            contact = self.contacts[matched_name]
            
            print(f"🔍 Matched '{speaker_name}' → '{matched_name}' (Score: {score})")
            
            return {
                **contact,
                'matched_name': matched_name,
                'confidence': score
            }
        
        print(f"⚠️  Kein Match für '{speaker_name}'")
        return None
    
    def match_participants(self, names: List[str]) -> List[Dict]:
        """Match list of participant names to Odoo contacts"""
        results = []
        
        for name in names:
            match = self.match_speaker(name)
            if match:
                results.append({
                    'original_name': name,
                    'matched_name': match.get('matched_name', name),
                    'email': match.get('email'),
                    'odoo_id': match.get('odoo_id'),
                    'confidence': match.get('confidence', 100)
                })
            else:
                results.append({
                    'original_name': name,
                    'matched_name': None,
                    'email': None,
                    'odoo_id': None,
                    'confidence': 0
                })
        
        return results
    
    def create_task(self, action_item: Dict, project_id: Optional[int] = None) -> int:
        """
        Create Odoo task from action item
        
        NOTE: Should only be called AFTER human review/approval!
        
        Args:
            action_item: Dict with description, assignee, deadline, priority
            project_id: Optional Odoo project ID
        
        Returns:
            Created task ID
        """
        # Match assignee
        assignee_match = self.match_speaker(action_item['assignee'])
        
        if not assignee_match:
            raise ValueError(f"Cannot create task: Assignee '{action_item['assignee']}' not found in Odoo")
        
        # Map priority
        priority_map = {
            'hoch': '3',
            'mittel': '1',
            'niedrig': '0'
        }
        priority = priority_map.get(action_item.get('priority', 'mittel'), '1')
        
        # Parse deadline
        deadline = action_item.get('deadline')
        if deadline and deadline != 'nicht definiert':
            # Convert "28.02.2026" to "2026-02-28"
            try:
                parts = deadline.split('.')
                if len(parts) == 3:
                    deadline = f"{parts[2]}-{parts[1]}-{parts[0]}"
            except:
                deadline = None
        else:
            deadline = None
        
        # Create task
        task_data = {
            'name': action_item['description'],
            'user_ids': [(4, assignee_match['odoo_id'])],  # Assign to user
            'priority': priority,
            'description': action_item.get('context', ''),
        }
        
        if deadline:
            task_data['date_deadline'] = deadline
        
        if project_id:
            task_data['project_id'] = project_id
        
        task_id = self.models.execute_kw(
            self.db, self.uid, self.api_key,
            'project.task', 'create',
            [task_data]
        )
        
        print(f"✅ Odoo Task erstellt: ID {task_id}")
        print(f"   Aufgabe: {action_item['description']}")
        print(f"   Zugewiesen: {action_item['assignee']} (Odoo ID: {assignee_match['odoo_id']})")
        
        return task_id


def test_odoo():
    """Test function"""
    config = {
        'config_path': '~/.openclaw/workspace/skills/odoo-connector/config.json',
        'contacts_path': '~/.openclaw/workspace/odoo-contacts.json'
    }
    
    connector = OdooConnector(config)
    
    # Test speaker matching
    test_names = ['Max', 'Anna', 'Nikita', 'Babak', 'Julia', 'Unknown Person']
    
    print("\n🔍 Testing speaker matching:")
    for name in test_names:
        result = connector.match_speaker(name)
        if result:
            print(f"   {name} → {result.get('matched_name')} ({result.get('email')})")
        else:
            print(f"   {name} → No match")


if __name__ == "__main__":
    test_odoo()
