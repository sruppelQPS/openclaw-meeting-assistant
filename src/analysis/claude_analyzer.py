#!/usr/bin/env python3
"""
Claude-based meeting analysis
Extracts: Action Items, Decisions, Open Questions, Summary
"""

import os
import json
from typing import Dict, List
from anthropic import Anthropic

class ClaudeAnalyzer:
    """Analyze meeting transcripts using Claude"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.model = config.get('model', 'claude-sonnet-4-5')
        self.max_tokens = config.get('max_tokens', 4000)
        self.client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    
    def analyze(self, transcript: str, context: Dict = None) -> Dict:
        """
        Analyze meeting transcript
        
        Args:
            transcript: Full meeting transcription
            context: Optional context (meeting title, attendees, agenda)
        
        Returns:
            Dict with:
                - summary: Executive summary
                - action_items: List of action items
                - decisions: List of decisions
                - open_questions: List of open questions
                - key_topics: Main topics discussed
        """
        print("🧠 Analysiere Meeting mit Claude...")
        
        # Build context string
        context_str = ""
        if context:
            if context.get('title'):
                context_str += f"Meeting-Titel: {context['title']}\n"
            if context.get('attendees'):
                context_str += f"Teilnehmer: {', '.join(context['attendees'])}\n"
            if context.get('date'):
                context_str += f"Datum: {context['date']}\n"
        
        # System prompt (QPS-specific)
        system_prompt = """Du bist ein professioneller Meeting-Protokollant für QPS Engineering AG, 
ein Schweizer Engineering-Unternehmen.

Deine Aufgabe:
1. Fasse das Meeting präzise zusammen (2-3 Absätze)
2. Extrahiere Action Items im Format: [WER] muss [WAS] bis [WANN]
3. Identifiziere Entscheidungen: ENTSCHEIDUNG: [Was wurde beschlossen]
4. Erkenne offene Fragen: OFFEN: [Was muss geklärt werden]
5. Extrahiere 3-5 Hauptthemen

Wichtig:
- Protokoll auf Deutsch, auch wenn das Meeting auf Englisch war
- Stil: Sachlich, präzise, keine Füllwörter
- Namen beibehalten wie im Transkript
- Bei Action Items: Wenn kein Datum genannt, als "nicht definiert" markieren
- Passiv vermeiden

Ausgabe als JSON mit diesen Feldern:
{
  "summary": "...",
  "action_items": [
    {
      "description": "Budget-Plan erstellen",
      "assignee": "Anna Meyer",
      "deadline": "28.02.2026" oder "nicht definiert",
      "context": "Originalzitat aus dem Meeting",
      "priority": "hoch" | "mittel" | "niedrig"
    }
  ],
  "decisions": [
    {
      "description": "Q2-Budget wird um 15% erhöht",
      "decided_by": ["Max", "Anna"],
      "context": "Originalzitat"
    }
  ],
  "open_questions": [
    {
      "question": "Wer übernimmt das Review?",
      "raised_by": "Max",
      "assigned_to": null
    }
  ],
  "key_topics": ["Budget Q2", "Neue Projekte", ...]
}
"""
        
        # User prompt
        user_prompt = f"""{context_str}

Transkript:
{transcript}

Analysiere dieses Meeting und gib das Ergebnis als JSON zurück."""
        
        # Call Claude
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        # Extract JSON from response
        response_text = response.content[0].text
        
        # Try to parse JSON (Claude should return valid JSON)
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback: Extract JSON from markdown code block
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
                result = json.loads(json_str)
            else:
                raise ValueError("Claude did not return valid JSON")
        
        # Add metadata
        result['model'] = self.model
        result['tokens_used'] = response.usage.input_tokens + response.usage.output_tokens
        
        print(f"✅ Analyse fertig:")
        print(f"   Action Items: {len(result.get('action_items', []))}")
        print(f"   Entscheidungen: {len(result.get('decisions', []))}")
        print(f"   Offene Fragen: {len(result.get('open_questions', []))}")
        print(f"   Tokens: {result['tokens_used']}")
        
        return result
    
    def estimate_cost(self, input_chars: int, output_chars: int) -> float:
        """
        Estimate analysis cost
        
        Claude Sonnet 4.5:
        - Input: $3/M tokens (~750k chars)
        - Output: $15/M tokens
        
        Rough estimate: 1 char ≈ 0.25 tokens
        """
        input_tokens = input_chars * 0.25
        output_tokens = output_chars * 0.25
        
        input_cost = (input_tokens / 1_000_000) * 3
        output_cost = (output_tokens / 1_000_000) * 15
        
        return input_cost + output_cost
    
    def save_analysis(self, analysis: Dict, output_path: str):
        """Save analysis to JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        print(f"💾 Analyse gespeichert: {output_path}")


def test_analysis():
    """Test function"""
    config = {
        'model': 'claude-sonnet-4-5',
        'max_tokens': 4000
    }
    
    analyzer = ClaudeAnalyzer(config)
    
    # Example transcript
    test_transcript = """
    Max: Guten Tag zusammen. Lass uns mit dem Budget für Q2 starten.
    
    Anna: Ich schlage vor, wir erhöhen das Budget um 15%.
    
    Max: Einverstanden. Anna, kannst du den Budget-Plan bis Ende Monat fertig machen?
    
    Anna: Ja, mache ich bis nächsten Freitag, also 28. Februar.
    
    Max: Super. Gibt es noch offene Punkte?
    
    Peter: Wer übernimmt das Review des Plans?
    
    Max: Gute Frage, klären wir nächste Woche.
    """
    
    context = {
        'title': 'Budget-Meeting Q2',
        'attendees': ['Max', 'Anna', 'Peter'],
        'date': '21.02.2026'
    }
    
    result = analyzer.analyze(test_transcript, context)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    test_analysis()
