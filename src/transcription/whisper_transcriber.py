#!/usr/bin/env python3
"""
Whisper-based transcription module
Supports: OpenAI Whisper API, local whisper.cpp
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, List
from openai import OpenAI

class WhisperTranscriber:
    """Transcribe audio using OpenAI Whisper API or local whisper.cpp"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.provider = config.get('provider', 'openai-whisper')
        self.model = config.get('model', 'whisper-1')
        self.language = config.get('language', 'de')
        
        if self.provider == 'openai-whisper':
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    def transcribe(self, audio_path: str) -> Dict:
        """
        Transcribe audio file
        
        Args:
            audio_path: Path to audio file (mp3, wav, m4a, etc.)
        
        Returns:
            Dict with:
                - text: Full transcription
                - language: Detected language
                - duration: Audio duration in seconds
                - segments: List of segments with timestamps (if available)
        """
        print(f"🎙️  Transkribiere: {audio_path}")
        print(f"   Provider: {self.provider}")
        
        if self.provider == 'openai-whisper':
            return self._transcribe_openai(audio_path)
        elif self.provider == 'whisper-cpp':
            return self._transcribe_local(audio_path)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def _transcribe_openai(self, audio_path: str) -> Dict:
        """Transcribe using OpenAI Whisper API"""
        
        with open(audio_path, "rb") as audio_file:
            # Basic transcription
            transcript = self.client.audio.transcriptions.create(
                model=self.model,
                file=audio_file,
                language=self.language,
                response_format="verbose_json"  # Get timestamps
            )
        
        # Extract segments if available
        segments = []
        if hasattr(transcript, 'segments') and transcript.segments:
            segments = [
                {
                    'start': seg.get('start', 0),
                    'end': seg.get('end', 0),
                    'text': seg.get('text', '').strip()
                }
                for seg in transcript.segments
            ]
        
        result = {
            'text': transcript.text.strip(),
            'language': transcript.language if hasattr(transcript, 'language') else self.language,
            'duration': transcript.duration if hasattr(transcript, 'duration') else 0,
            'segments': segments,
            'provider': 'openai-whisper',
            'model': self.model
        }
        
        print(f"✅ Transkription fertig ({result['duration']:.1f}s)")
        print(f"   Länge: {len(result['text'])} Zeichen")
        print(f"   Sprache: {result['language']}")
        
        return result
    
    def _transcribe_local(self, audio_path: str) -> Dict:
        """Transcribe using local whisper.cpp"""
        # TODO: Implement whisper.cpp integration
        # For now, fallback to OpenAI API
        print("⚠️  Lokales Whisper noch nicht implementiert, nutze OpenAI API")
        return self._transcribe_openai(audio_path)
    
    def estimate_cost(self, audio_duration_seconds: float) -> float:
        """
        Estimate transcription cost
        
        OpenAI Whisper: $0.006 per minute
        Local whisper: $0
        """
        if self.provider == 'openai-whisper':
            minutes = audio_duration_seconds / 60
            return minutes * 0.006
        else:
            return 0.0
    
    def save_transcript(self, transcript: Dict, output_path: str):
        """Save transcript to JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(transcript, f, indent=2, ensure_ascii=False)
        print(f"💾 Transkript gespeichert: {output_path}")


def test_transcription():
    """Test function"""
    config = {
        'provider': 'openai-whisper',
        'model': 'whisper-1',
        'language': 'de'
    }
    
    transcriber = WhisperTranscriber(config)
    
    # Example: Estimate cost for 1h meeting
    cost = transcriber.estimate_cost(3600)
    print(f"Geschätzte Kosten für 1h Meeting: ${cost:.2f}")


if __name__ == "__main__":
    test_transcription()
