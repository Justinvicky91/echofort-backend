"""
Whisper API Service for Call Recording Analysis
Analyzes call recordings to detect scams, person's situation, and mentality
"""

import os
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from openai import OpenAI, AsyncOpenAI
import httpx

class WhisperAnalyzer:
    """
    Analyzes call recordings using OpenAI Whisper API
    Detects scams, caller intent, victim state, and psychological indicators
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.scam_analysis_prompt = """
You are an expert scam detection AI analyzing phone call transcriptions from India.
Analyze the conversation for scam indicators, psychological manipulation, and victim vulnerability.

Provide detailed analysis in JSON format with the following structure:
{
    "is_scam": boolean,
    "scam_type": "digital_arrest" | "investment" | "loan_harassment" | "prize_lottery" | "tech_support" | "romance" | "job_offer" | "bank_fraud" | "none",
    "threat_level": 0-10 (integer),
    "confidence": 0-100 (percentage),
    
    "situation_analysis": {
        "caller_intent": "string describing what caller wants",
        "victim_state": "confused" | "scared" | "convinced" | "suspicious" | "calm" | "agitated",
        "urgency": "low" | "medium" | "high" | "critical",
        "pressure_tactics": ["list of manipulation tactics used"],
        "red_flags": ["list of scam indicators found"]
    },
    
    "mentality_analysis": {
        "caller_psychology": "manipulative" | "aggressive" | "friendly" | "professional" | "threatening",
        "victim_vulnerability": 0-10 (integer),
        "emotional_state": "calm" | "anxious" | "fearful" | "angry" | "confused" | "trusting",
        "decision_making": "rational" | "impaired" | "under_pressure" | "coerced",
        "psychological_indicators": ["list of psychological patterns observed"]
    },
    
    "evidence_markers": [
        {
            "timestamp": "MM:SS",
            "event": "description of significant moment",
            "severity": "low" | "medium" | "high" | "critical",
            "quote": "exact quote from conversation"
        }
    ],
    
    "recommendations": [
        "list of specific actions to take"
    ],
    
    "summary": "brief summary of the call and analysis"
}

Focus on:
- Common Indian scam patterns (digital arrest, fake police, investment schemes)
- Hindi/English code-switching patterns
- Urgency and pressure tactics
- Requests for money, OTP, bank details, personal information
- Impersonation of authorities (police, bank, government)
- Emotional manipulation and fear tactics
"""
    
    async def transcribe_audio(
        self, 
        audio_url: str, 
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Transcribe audio file using Whisper API
        
        Args:
            audio_url: URL or file path to audio file
            language: Language code (en, hi, ta, te, etc.)
        
        Returns:
            {
                "text": str,
                "language": str,
                "duration": float,
                "segments": List[Dict]
            }
        """
        try:
            # Download audio file if URL
            if audio_url.startswith("http"):
                async with httpx.AsyncClient() as client:
                    response = await client.get(audio_url)
                    audio_data = response.content
                    
                    # Save temporarily
                    temp_file = f"/tmp/call_{datetime.now().timestamp()}.mp3"
                    with open(temp_file, "wb") as f:
                        f.write(audio_data)
                    audio_file = temp_file
            else:
                audio_file = audio_url
            
            # Transcribe with Whisper
            with open(audio_file, "rb") as f:
                transcription = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    language=language,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"]
                )
            
            # Clean up temp file
            if audio_url.startswith("http"):
                os.remove(temp_file)
            
            return {
                "text": transcription.text,
                "language": language,
                "duration": transcription.duration if hasattr(transcription, 'duration') else 0,
                "segments": transcription.segments if hasattr(transcription, 'segments') else []
            }
            
        except Exception as e:
            raise Exception(f"Transcription failed: {str(e)}")
    
    async def analyze_scam(
        self, 
        transcription: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze transcription for scam indicators
        
        Args:
            transcription: Full text of the call
            metadata: Optional metadata (caller_id, duration, etc.)
        
        Returns:
            Detailed scam analysis with situation and mentality assessment
        """
        try:
            # Build analysis prompt
            user_prompt = f"Call Transcription:\n\n{transcription}"
            
            if metadata:
                user_prompt += f"\n\nMetadata:\n{json.dumps(metadata, indent=2)}"
            
            # Analyze with GPT-4
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": self.scam_analysis_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            # Parse response
            analysis = json.loads(response.choices[0].message.content)
            
            # Add metadata
            analysis["analyzed_at"] = datetime.now().isoformat()
            analysis["model"] = "gpt-4o"
            
            return analysis
            
        except Exception as e:
            raise Exception(f"Scam analysis failed: {str(e)}")
    
    async def analyze_call_recording(
        self,
        audio_url: str,
        language: str = "en",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Complete analysis pipeline: transcribe + analyze
        
        Args:
            audio_url: URL or file path to call recording
            language: Language code
            metadata: Optional call metadata
        
        Returns:
            Complete analysis with transcription and scam detection
        """
        try:
            # Step 1: Transcribe
            transcription_result = await self.transcribe_audio(audio_url, language)
            
            # Step 2: Analyze
            analysis = await self.analyze_scam(
                transcription_result["text"],
                metadata
            )
            
            # Combine results
            return {
                "transcription": transcription_result,
                "analysis": analysis,
                "processed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "status": "failed",
                "processed_at": datetime.now().isoformat()
            }
    
    async def batch_analyze(
        self,
        audio_urls: List[str],
        language: str = "en"
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple call recordings in parallel
        
        Args:
            audio_urls: List of audio file URLs
            language: Language code
        
        Returns:
            List of analysis results
        """
        tasks = [
            self.analyze_call_recording(url, language)
            for url in audio_urls
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [
            result if not isinstance(result, Exception) else {"error": str(result)}
            for result in results
        ]
    
    def generate_alert_message(self, analysis: Dict[str, Any]) -> str:
        """
        Generate user-friendly alert message from analysis
        
        Args:
            analysis: Analysis result
        
        Returns:
            Alert message string
        """
        if not analysis.get("is_scam"):
            return "✅ No scam detected. Call appears safe."
        
        threat_level = analysis.get("threat_level", 0)
        scam_type = analysis.get("scam_type", "unknown")
        
        # Emoji based on threat level
        if threat_level >= 8:
            emoji = "🚨"
            urgency = "CRITICAL"
        elif threat_level >= 6:
            emoji = "⚠️"
            urgency = "HIGH"
        elif threat_level >= 4:
            emoji = "⚡"
            urgency = "MEDIUM"
        else:
            emoji = "ℹ️"
            urgency = "LOW"
        
        message = f"{emoji} {urgency} THREAT DETECTED\n\n"
        message += f"Scam Type: {scam_type.replace('_', ' ').title()}\n"
        message += f"Threat Level: {threat_level}/10\n"
        message += f"Confidence: {analysis.get('confidence', 0)}%\n\n"
        
        # Add recommendations
        recommendations = analysis.get("recommendations", [])
        if recommendations:
            message += "Recommended Actions:\n"
            for i, rec in enumerate(recommendations[:3], 1):
                message += f"{i}. {rec}\n"
        
        return message
    
    def generate_evidence_report(self, analysis: Dict[str, Any]) -> str:
        """
        Generate detailed evidence report for legal purposes
        
        Args:
            analysis: Analysis result
        
        Returns:
            Formatted evidence report
        """
        report = "SCAM CALL EVIDENCE REPORT\n"
        report += "=" * 50 + "\n\n"
        
        report += f"Analysis Date: {analysis.get('analyzed_at', 'N/A')}\n"
        report += f"Scam Type: {analysis.get('scam_type', 'N/A')}\n"
        report += f"Threat Level: {analysis.get('threat_level', 0)}/10\n"
        report += f"Confidence: {analysis.get('confidence', 0)}%\n\n"
        
        # Situation Analysis
        situation = analysis.get("situation_analysis", {})
        report += "SITUATION ANALYSIS\n"
        report += "-" * 50 + "\n"
        report += f"Caller Intent: {situation.get('caller_intent', 'N/A')}\n"
        report += f"Victim State: {situation.get('victim_state', 'N/A')}\n"
        report += f"Urgency: {situation.get('urgency', 'N/A')}\n\n"
        
        # Red Flags
        red_flags = situation.get("red_flags", [])
        if red_flags:
            report += "Red Flags Detected:\n"
            for flag in red_flags:
                report += f"  • {flag}\n"
            report += "\n"
        
        # Evidence Markers
        markers = analysis.get("evidence_markers", [])
        if markers:
            report += "EVIDENCE TIMELINE\n"
            report += "-" * 50 + "\n"
            for marker in markers:
                report += f"[{marker.get('timestamp', 'N/A')}] "
                report += f"{marker.get('severity', 'N/A').upper()}: "
                report += f"{marker.get('event', 'N/A')}\n"
                if marker.get('quote'):
                    report += f"  Quote: \"{marker.get('quote')}\"\n"
                report += "\n"
        
        # Summary
        report += "SUMMARY\n"
        report += "-" * 50 + "\n"
        report += analysis.get("summary", "No summary available") + "\n\n"
        
        # Recommendations
        recommendations = analysis.get("recommendations", [])
        if recommendations:
            report += "RECOMMENDED ACTIONS\n"
            report += "-" * 50 + "\n"
            for i, rec in enumerate(recommendations, 1):
                report += f"{i}. {rec}\n"
        
        report += "\n" + "=" * 50 + "\n"
        report += "This report is generated by AI and should be reviewed by authorities.\n"
        
        return report


# Singleton instance
_analyzer = None

def get_whisper_analyzer() -> WhisperAnalyzer:
    """Get singleton instance of WhisperAnalyzer"""
    global _analyzer
    if _analyzer is None:
        _analyzer = WhisperAnalyzer()
    return _analyzer

