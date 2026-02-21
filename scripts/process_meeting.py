#!/usr/bin/env python3
"""
Main script to process a meeting audio file
Usage: python process_meeting.py meeting.mp3 --title "Budget Q2" --attendees "Max,Anna,Julia"
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from transcription.whisper_transcriber import WhisperTranscriber
from analysis.claude_analyzer import ClaudeAnalyzer
from protocol.generator import ProtocolGenerator
from integrations.odoo_connector import OdooConnector

def load_config():
    """Load config.json"""
    config_path = Path(__file__).parent.parent / "config.json"
    
    if not config_path.exists():
        print("⚠️  config.json nicht gefunden, nutze Beispiel-Config")
        config_path = Path(__file__).parent.parent / "config.json.example"
    
    with open(config_path, 'r') as f:
        return json.load(f)

def process_meeting(audio_path: str, args):
    """Process a meeting audio file end-to-end"""
    
    print("="*60)
    print("🎙️  OpenClaw Meeting Assistant")
    print("="*60)
    
    # Load config
    config = load_config()
    
    # Initialize components
    print("\n📦 Initialisiere Komponenten...")
    transcriber = WhisperTranscriber(config['transcription'])
    analyzer = ClaudeAnalyzer(config['analysis'])
    generator = ProtocolGenerator(config['protocol'])
    
    # Optional: Odoo
    odoo = None
    if config.get('odoo', {}).get('enabled', False):
        try:
            odoo = OdooConnector(config['odoo'])
        except Exception as e:
            print(f"⚠️  Odoo nicht verfügbar: {e}")
    
    # Step 1: Transcription
    print("\n" + "="*60)
    print("SCHRITT 1: TRANSKRIPTION")
    print("="*60)
    
    transcript = transcriber.transcribe(audio_path)
    
    # Estimate cost
    transcription_cost = transcriber.estimate_cost(transcript['duration'])
    print(f"💰 Geschätzte Transkriptions-Kosten: ${transcription_cost:.2f}")
    
    # Save transcript
    output_dir = Path(audio_path).parent / f"{Path(audio_path).stem}_output"
    output_dir.mkdir(exist_ok=True)
    
    transcriber.save_transcript(transcript, str(output_dir / "transcript.json"))
    
    # Step 2: Analysis
    print("\n" + "="*60)
    print("SCHRITT 2: KI-ANALYSE")
    print("="*60)
    
    # Prepare context
    context = {
        'title': args.title or 'Meeting',
        'date': datetime.now().strftime('%d.%m.%Y')
    }
    
    if args.attendees:
        context['attendees'] = [name.strip() for name in args.attendees.split(',')]
    
    analysis = analyzer.analyze(transcript['text'], context)
    
    # Estimate cost
    analysis_cost = analyzer.estimate_cost(
        len(transcript['text']), 
        len(json.dumps(analysis))
    )
    print(f"💰 Geschätzte Analyse-Kosten: ${analysis_cost:.2f}")
    
    # Save analysis
    analyzer.save_analysis(analysis, str(output_dir / "analysis.json"))
    
    # Step 3: Speaker Matching (Odoo)
    participants = []
    if odoo and context.get('attendees'):
        print("\n" + "="*60)
        print("SCHRITT 3: SPEAKER MATCHING (ODOO)")
        print("="*60)
        
        matched = odoo.match_participants(context['attendees'])
        
        for m in matched:
            participants.append({
                'name': m['matched_name'] or m['original_name'],
                'email': m['email'],
                'odoo_id': m['odoo_id'],
                'present': True,
                'confidence': m['confidence']
            })
    
    # Step 4: Protocol Generation
    print("\n" + "="*60)
    print("SCHRITT 4: PROTOKOLL-ERSTELLUNG")
    print("="*60)
    
    metadata = {
        **context,
        'participants': participants,
        'location': 'Online',
        'start_time': '',
        'end_time': ''
    }
    
    protocol = generator.generate(transcript, analysis, metadata)
    
    # Save protocol
    protocol_path = output_dir / "protocol.md"
    generator.save_markdown(protocol, str(protocol_path))
    
    # Summary
    print("\n" + "="*60)
    print("✅ FERTIG!")
    print("="*60)
    
    print(f"\n📊 Zusammenfassung:")
    print(f"   Dauer: {transcript['duration']:.1f}s ({transcript['duration']/60:.1f} Min)")
    print(f"   Transkript: {len(transcript['text'])} Zeichen")
    print(f"   Action Items: {len(analysis.get('action_items', []))}")
    print(f"   Entscheidungen: {len(analysis.get('decisions', []))}")
    print(f"   Offene Fragen: {len(analysis.get('open_questions', []))}")
    
    total_cost = transcription_cost + analysis_cost
    print(f"\n💰 Gesamtkosten: ${total_cost:.2f}")
    
    print(f"\n📁 Output:")
    print(f"   {output_dir / 'transcript.json'}")
    print(f"   {output_dir / 'analysis.json'}")
    print(f"   {output_dir / 'protocol.md'}")
    
    print(f"\n📋 Nächster Schritt:")
    print(f"   Review-Flow (wird mit Opus 4.6 implementiert)")
    print(f"   Dann: Export nach Odoo/E-Mail/Memory")
    
    return {
        'transcript': transcript,
        'analysis': analysis,
        'protocol': protocol,
        'output_dir': output_dir,
        'cost': total_cost
    }

def main():
    parser = argparse.ArgumentParser(description='Process meeting audio file')
    parser.add_argument('audio_path', help='Path to audio file (mp3, wav, m4a, etc.)')
    parser.add_argument('--title', help='Meeting title')
    parser.add_argument('--attendees', help='Comma-separated list of attendees')
    parser.add_argument('--type', help='Meeting type (team, customer, status)', default='team')
    
    args = parser.parse_args()
    
    # Check if audio file exists
    if not Path(args.audio_path).exists():
        print(f"❌ Audio-Datei nicht gefunden: {args.audio_path}")
        sys.exit(1)
    
    # Process
    try:
        result = process_meeting(args.audio_path, args)
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
