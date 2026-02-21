#!/usr/bin/env python3
"""
Protocol generator
Creates meeting protocols in Markdown, PDF, DOCX formats
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from jinja2 import Template

class ProtocolGenerator:
    """Generate meeting protocols from analysis results"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.template_dir = Path(__file__).parent.parent.parent / "templates"
        self.default_template = config.get('default_template', 'qps-standard')
        self.language = config.get('language', 'de')
    
    def generate(self, 
                 transcript: Dict,
                 analysis: Dict,
                 metadata: Dict,
                 template_name: str = None) -> str:
        """
        Generate protocol from transcript and analysis
        
        Args:
            transcript: Transcription results
            analysis: Analysis results from Claude
            metadata: Meeting metadata (title, date, attendees, etc.)
            template_name: Template to use (default: config default)
        
        Returns:
            Markdown protocol text
        """
        print("📋 Erstelle Protokoll...")
        
        if not template_name:
            template_name = self.default_template
        
        # Load template
        template_path = self.template_dir / f"protocol-{template_name}.md"
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template_text = f.read()
        
        template = Template(template_text)
        
        # Prepare data for template
        data = {
            'title': metadata.get('title', 'Meeting-Protokoll'),
            'date': metadata.get('date', datetime.now().strftime('%d.%m.%Y')),
            'start_time': metadata.get('start_time', ''),
            'end_time': metadata.get('end_time', ''),
            'location': metadata.get('location', 'Online'),
            'participants': metadata.get('participants', []),
            'summary': analysis.get('summary', ''),
            'action_items': analysis.get('action_items', []),
            'decisions': analysis.get('decisions', []),
            'open_questions': analysis.get('open_questions', []),
            'topics': self._extract_topics(analysis),
            'next_steps': analysis.get('next_steps', ''),
            'created_at': datetime.now().strftime('%d.%m.%Y %H:%M'),
            'version': '1.0.0',
            'reviewed_by': metadata.get('reviewed_by', '')
        }
        
        # Render protocol
        protocol = template.render(**data)
        
        print(f"✅ Protokoll erstellt ({len(protocol)} Zeichen)")
        
        return protocol
    
    def _extract_topics(self, analysis: Dict) -> List[Dict]:
        """Extract topics with their content from analysis"""
        topics = []
        
        # Use key_topics if available
        key_topics = analysis.get('key_topics', [])
        
        if key_topics:
            for i, topic_title in enumerate(key_topics):
                # Find related decisions
                decisions = [
                    d for d in analysis.get('decisions', [])
                    if any(keyword in d['description'].lower() for keyword in topic_title.lower().split())
                ]
                
                topics.append({
                    'title': topic_title,
                    'content': f"Details zu {topic_title} wurden besprochen.",
                    'decisions': decisions
                })
        
        return topics
    
    def save_markdown(self, protocol: str, output_path: str):
        """Save protocol as Markdown file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(protocol)
        print(f"💾 Markdown gespeichert: {output_path}")
    
    def save_pdf(self, protocol: str, output_path: str):
        """Save protocol as PDF (requires reportlab)"""
        # TODO: Implement PDF generation
        print("⚠️  PDF-Export noch nicht implementiert")
        print(f"   Nutze erstmal: pandoc {output_path.replace('.pdf', '.md')} -o {output_path}")
    
    def save_docx(self, protocol: str, output_path: str):
        """Save protocol as DOCX (requires python-docx)"""
        # TODO: Implement DOCX generation
        print("⚠️  DOCX-Export noch nicht implementiert")
        print(f"   Nutze erstmal: pandoc {output_path.replace('.docx', '.md')} -o {output_path}")


def test_generator():
    """Test function"""
    config = {
        'default_template': 'qps',
        'language': 'de'
    }
    
    generator = ProtocolGenerator(config)
    
    # Example data
    transcript = {
        'text': 'Meeting transcript...',
        'duration': 1800
    }
    
    analysis = {
        'summary': 'Im Meeting wurde das Q2-Budget besprochen und eine Erhöhung um 15% beschlossen.',
        'action_items': [
            {
                'description': 'Budget-Plan Q2 erstellen',
                'assignee': 'Anna Meyer',
                'deadline': '28.02.2026',
                'priority': 'hoch',
                'context': 'Anna, kannst du den Budget-Plan bis Ende Monat fertig machen?'
            }
        ],
        'decisions': [
            {
                'description': 'Q2-Budget wird um 15% erhöht',
                'decided_by': ['Max', 'Anna'],
                'context': 'Ich schlage vor, wir erhöhen das Budget um 15%'
            }
        ],
        'open_questions': [
            {
                'question': 'Wer übernimmt das Review des Budget-Plans?',
                'raised_by': 'Peter',
                'assigned_to': None
            }
        ],
        'key_topics': ['Budget Q2', 'Neue Projekte']
    }
    
    metadata = {
        'title': 'Budget-Meeting Q2',
        'date': '21.02.2026',
        'start_time': '14:00',
        'end_time': '15:00',
        'location': 'Zoom',
        'participants': [
            {'name': 'Max Schmidt', 'role': 'Projektleiter', 'present': True},
            {'name': 'Anna Meyer', 'role': 'Finance', 'present': True},
            {'name': 'Peter Müller', 'role': 'Developer', 'present': True}
        ]
    }
    
    protocol = generator.generate(transcript, analysis, metadata)
    print("\n" + "="*60)
    print(protocol)
    print("="*60)


if __name__ == "__main__":
    test_generator()
