"""
Voice Manager - Text-to-Speech Audio Generation System

This module handles the conversion of text reports into audio files using
various Text-to-Speech (TTS) services. It supports generating audio reports
for different types of content and distribution channels.

Features:
- Multiple TTS engine support (Edge TTS, OpenAI TTS, Azure)
- Voice selection for different report types
- Audio processing (background music, normalization)
- Alert audio generation
- Audio file management and cleanup
"""

import os
import logging
import json
import time
import tempfile
import glob
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

# Import text-to-speech libraries
try:
    import edge_tts
except ImportError:
    edge_tts = None

try:
    import openai
except ImportError:
    openai = None

try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None

# Set up logging
logger = logging.getLogger(__name__)

class VoiceManager:
    """Voice Manager for generating audio reports from text content"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Voice Manager
        
        Args:
            config: Platform configuration dictionary
        """
        self.config = config
        self.ai_config = config.get("ai", {})
        self.tts_config = config.get("tts", {})
        
        # TTS provider configuration
        self.provider = self.tts_config.get("provider", "edge_tts")  # Default to Edge TTS
        self.openai_api_key = self.ai_config.get("api_key", "")
        
        # Voice settings
        self.default_voice = self.tts_config.get("default_voice", "en-US-AriaNeural")
        self.voices = {
            "daily": self.tts_config.get("daily_voice", "en-US-GuyNeural"),
            "weekly": self.tts_config.get("weekly_voice", "en-US-AriaNeural"),
            "performance": self.tts_config.get("performance_voice", "en-US-GuyNeural"),
            "alert": self.tts_config.get("alert_voice", "en-US-DavisNeural")
        }
        
        # Audio storage paths
        self.audio_path = "data/audio"
        self.tts_path = os.path.join(self.audio_path, "tts")
        self.music_path = os.path.join(self.audio_path, "music")
        os.makedirs(self.tts_path, exist_ok=True)
        os.makedirs(self.music_path, exist_ok=True)
        
        # Check for background music files
        self._check_background_music()
        
        logger.info("Voice Manager initialized")
        
    def generate_audio_report(self, text: str, report_type: str, voice: Optional[str] = None) -> str:
        """
        Generate an audio report from text
        
        Args:
            text: Text content to convert to speech
            report_type: Type of report (daily, weekly, performance, alert)
            voice: Optional voice to use (overrides default for report type)
            
        Returns:
            Path to the generated audio file
        """
        try:
            # Determine voice to use
            voice_id = voice or self.voices.get(report_type, self.default_voice)
            
            # Prepare text for TTS (clean up markdown, etc.)
            prepared_text = self._prepare_text_for_tts(text)
            
            # Generate audio
            audio_path = self._generate_audio(prepared_text, voice_id, report_type)
            
            # Add background music if appropriate
            if report_type in ["daily", "weekly", "performance"]:
                final_audio = self._add_background_music(audio_path, report_type)
            else:
                final_audio = audio_path
                
            logger.info(f"Generated audio report: {final_audio}")
            return final_audio
            
        except Exception as e:
            logger.error(f"Failed to generate audio report: {str(e)}")
            return ""
            
    def _prepare_text_for_tts(self, text: str) -> str:
        """
        Prepare text for TTS by cleaning up markdown and formatting
        
        Args:
            text: Raw text content (potentially markdown)
            
        Returns:
            Cleaned text ready for TTS
        """
        try:
            # Remove markdown headers
            lines = text.split("\n")
            cleaned_lines = []
            
            for line in lines:
                # Remove markdown headers (# Header)
                if line.strip().startswith("#"):
                    header_text = line.strip().lstrip("#").strip()
                    cleaned_lines.append(header_text + ".")
                    continue
                    
                # Remove markdown bold (**text**)
                line = line.replace("**", "")
                
                # Remove markdown italic (*text*)
                line = line.replace("*", "")
                
                # Remove markdown links [text](url)
                while "[" in line and "](" in line and ")" in line:
                    start = line.find("[")
                    middle = line.find("](", start)
                    end = line.find(")", middle)
                    if start != -1 and middle != -1 and end != -1:
                        link_text = line[start+1:middle]
                        line = line[:start] + link_text + line[end+1:]
                    else:
                        break
                        
                # Add the cleaned line
                cleaned_lines.append(line)
                
            # Join the cleaned lines
            cleaned_text = "\n".join(cleaned_lines)
            
            # Replace common symbols that might affect TTS
            replacements = {
                "-": " ",
                "_": " ",
                "•": "",
                "✅": "",
                "⚠️": "",
                "➡️": "",
                "\n\n": ". ",
                "...": ",",
                "--": ","
            }
            
            for old, new in replacements.items():
                cleaned_text = cleaned_text.replace(old, new)
                
            return cleaned_text
            
        except Exception as e:
            logger.error(f"Failed to prepare text for TTS: {str(e)}")
            return text  # Return original text as fallback
            
    def _generate_audio(self, text: str, voice_id: str, report_type: str) -> str:
        """
        Generate audio using the configured TTS provider
        
        Args:
            text: Prepared text for TTS
            voice_id: Voice ID to use
            report_type: Type of report
            
        Returns:
            Path to the generated audio file
        """
        try:
            # Create a unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{report_type}_report_{timestamp}.mp3"
            output_path = os.path.join(self.tts_path, filename)
            
            # Use the appropriate TTS provider
            if self.provider == "edge_tts":
                return self._generate_with_edge_tts(text, voice_id, output_path)
            elif self.provider == "openai":
                return self._generate_with_openai_tts(text, voice_id, output_path)
            else:
                logger.warning(f"Unsupported TTS provider: {self.provider}, falling back to Edge TTS")
                return self._generate_with_edge_tts(text, voice_id, output_path)
                
        except Exception as e:
            logger.error(f"Failed to generate audio: {str(e)}")
            return ""
            
    def _generate_with_edge_tts(self, text: str, voice_id: str, output_path: str) -> str:
        """
        Generate audio using Edge TTS
        
        Args:
            text: Prepared text for TTS
            voice_id: Voice ID to use
            output_path: Path to save the output audio
            
        Returns:
            Path to the generated audio file
        """
        try:
            if edge_tts is None:
                logger.error("Edge TTS is not installed. Please install with: pip install edge-tts")
                return ""
                
            # In a real implementation, this would use the edge-tts library
            # For now, just log that we would generate audio
            logger.info(f"Would generate audio using Edge TTS with voice {voice_id}")
            
            # Create an empty file as a placeholder
            with open(output_path, "w") as f:
                f.write("")
                
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to generate audio with Edge TTS: {str(e)}")
            return ""
            
    def _generate_with_openai_tts(self, text: str, voice_id: str, output_path: str) -> str:
        """
        Generate audio using OpenAI TTS
        
        Args:
            text: Prepared text for TTS
            voice_id: Voice ID to use
            output_path: Path to save the output audio
            
        Returns:
            Path to the generated audio file
        """
        try:
            if openai is None:
                logger.error("OpenAI is not installed. Please install with: pip install openai")
                return ""
                
            # Map voice_id to OpenAI voice
            # OpenAI has a limited set of voices: alloy, echo, fable, onyx, nova, shimmer
            openai_voices = {
                "en-US-AriaNeural": "nova",
                "en-US-GuyNeural": "onyx",
                "en-US-DavisNeural": "echo",
                "default": "nova"
            }
            
            openai_voice = openai_voices.get(voice_id, openai_voices["default"])
            
            # In a real implementation, this would call the OpenAI API
            # For now, just log that we would generate audio
            logger.info(f"Would generate audio using OpenAI TTS with voice {openai_voice}")
            
            # Create an empty file as a placeholder
            with open(output_path, "w") as f:
                f.write("")
                
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to generate audio with OpenAI TTS: {str(e)}")
            return ""
            
    def _add_background_music(self, audio_path: str, report_type: str) -> str:
        """
        Add background music to the TTS audio
        
        Args:
            audio_path: Path to the TTS audio file
            report_type: Type of report
            
        Returns:
            Path to the final audio file with background music
        """
        try:
            if AudioSegment is None:
                logger.warning("pydub is not installed. Cannot add background music. Using raw TTS audio.")
                return audio_path
                
            # Get appropriate background music
            music_file = self._get_background_music(report_type)
            
            if not music_file or not os.path.exists(music_file):
                logger.warning("No background music found. Using raw TTS audio.")
                return audio_path
                
            # In a real implementation, this would use pydub to combine audio
            # For now, just log that we would add background music
            logger.info(f"Would add background music {music_file} to {audio_path}")
            
            # Generate output filename
            output_filename = os.path.basename(audio_path).replace(".mp3", "_with_music.mp3")
            output_path = os.path.join(self.audio_path, output_filename)
            
            # Placeholder: Just copy the file
            shutil.copy(audio_path, output_path)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to add background music: {str(e)}")
            return audio_path  # Return original audio as fallback
            
    def _get_background_music(self, report_type: str) -> str:
        """
        Get appropriate background music for the report type
        
        Args:
            report_type: Type of report
            
        Returns:
            Path to the background music file
        """
        try:
            # Map report types to music types
            music_types = {
                "daily": "upbeat",
                "weekly": "inspirational",
                "performance": "corporate",
                "alert": "urgent"
            }
            
            music_type = music_types.get(report_type, "ambient")
            
            # Look for music files of the appropriate type
            pattern = os.path.join(self.music_path, f"{music_type}_*.mp3")
            music_files = glob.glob(pattern)
            
            if not music_files:
                # Try any music file
                pattern = os.path.join(self.music_path, "*.mp3")
                music_files = glob.glob(pattern)
                
            if music_files:
                # Pick a random music file
                import random
                return random.choice(music_files)
                
            return ""
            
        except Exception as e:
            logger.error(f"Failed to get background music: {str(e)}")
            return ""
            
    def _check_background_music(self):
        """Check for background music files and create placeholders if needed"""
        try:
            # Check if there are any music files
            if not glob.glob(os.path.join(self.music_path, "*.mp3")):
                # Create placeholder music files
                music_types = ["ambient", "upbeat", "inspirational", "corporate", "urgent"]
                
                for music_type in music_types:
                    placeholder_path = os.path.join(self.music_path, f"{music_type}_placeholder.mp3")
                    with open(placeholder_path, "w") as f:
                        f.write("")
                        
                logger.info("Created placeholder background music files")
                
        except Exception as e:
            logger.error(f"Failed to check background music: {str(e)}")
            
    def generate_alert_audio(self, alert: Dict[str, Any]) -> str:
        """
        Generate audio for a market alert
        
        Args:
            alert: Alert data dictionary
            
        Returns:
            Path to the generated audio file
        """
        try:
            # Extract alert information
            event = alert.get("event", {})
            symbol = event.get("symbol", "unknown")
            event_type = event.get("event_type", "unknown")
            description = event.get("description", "")
            
            # Create alert text
            alert_text = f"Alert! {symbol} {event_type}. {description}"
            
            # Generate audio with alert voice
            voice_id = self.voices.get("alert", self.default_voice)
            
            # Generate a unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"alert_{symbol}_{timestamp}.mp3"
            output_path = os.path.join(self.tts_path, filename)
            
            # Generate the audio
            if self.provider == "edge_tts":
                return self._generate_with_edge_tts(alert_text, voice_id, output_path)
            elif self.provider == "openai":
                return self._generate_with_openai_tts(alert_text, voice_id, output_path)
            else:
                return self._generate_with_edge_tts(alert_text, voice_id, output_path)
                
        except Exception as e:
            logger.error(f"Failed to generate alert audio: {str(e)}")
            return ""
            
    def convert_report_to_audio(self, report_path: str, report_type: str) -> str:
        """
        Convert a text report file to audio
        
        Args:
            report_path: Path to the report file
            report_type: Type of report
            
        Returns:
            Path to the generated audio file
        """
        try:
            # Check if the report file exists
            if not os.path.exists(report_path):
                logger.error(f"Report file does not exist: {report_path}")
                return ""
                
            # Read the report file
            with open(report_path, "r") as f:
                report_text = f.read()
                
            # Generate audio
            return self.generate_audio_report(report_text, report_type)
            
        except Exception as e:
            logger.error(f"Failed to convert report to audio: {str(e)}")
            return ""
            
    def list_available_voices(self) -> List[Dict[str, Any]]:
        """
        List available TTS voices
        
        Returns:
            List of voice information dictionaries
        """
        try:
            # This would call the appropriate TTS provider to get available voices
            # For now, return a placeholder list
            return [
                {"id": "en-US-AriaNeural", "name": "Aria", "gender": "Female", "locale": "en-US"},
                {"id": "en-US-GuyNeural", "name": "Guy", "gender": "Male", "locale": "en-US"},
                {"id": "en-US-DavisNeural", "name": "Davis", "gender": "Male", "locale": "en-US"},
                {"id": "en-GB-LibbyNeural", "name": "Libby", "gender": "Female", "locale": "en-GB"},
                {"id": "en-GB-RyanNeural", "name": "Ryan", "gender": "Male", "locale": "en-GB"}
            ]
            
        except Exception as e:
            logger.error(f"Failed to list available voices: {str(e)}")
            return []
            
    def send_audio_report(self, chat_id: str, title: str, audio_path: str):
        """Send audio report to user"""
        try:
            with open(audio_path, "rb") as audio_file:
                self.updater.bot.send_audio(
                    chat_id=chat_id,
                    audio=audio_file,
                    title=title,
                    caption=f"🔊 {title}"
                )
            return True
        except Exception as e:
            logger.error(f"Failed to send audio report: {str(e)}")
            return False
            
    def run(self):
        """
        Run the Voice Manager
        
        This method keeps the voice manager running and processes audio conversion tasks.
        """
        logger.info("Voice Manager started")
        
        try:
            # In a real implementation, this would monitor a queue for audio conversion tasks
            # For now, just keep the thread alive and periodically clean up old files
            
            # Create placeholder background music files if they don't exist
            self._check_background_music()
            
            # Main loop
            while True:
                try:
                    # Clean up old audio files every day
                    self.cleanup_old_audio(days=7)
                    
                    # Sleep to avoid high CPU usage
                    time.sleep(3600)  # Sleep for an hour
                    
                except Exception as e:
                    logger.error(f"Error in Voice Manager run loop: {str(e)}")
                    time.sleep(60)  # Sleep for a minute before retrying
                    
        except KeyboardInterrupt:
            logger.info("Voice Manager stopped by user")
        except Exception as e:
            logger.error(f"Voice Manager stopped due to error: {str(e)}")
    
    def cleanup_old_audio(self, days: int = 7):
        """
        Clean up old audio files
        
        Args:
            days: Number of days to keep files for
        """
        try:
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Find all audio files older than the cutoff date
            for file_path in glob.glob(os.path.join(self.tts_path, "*.mp3")):
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                if file_time < cutoff_date:
                    try:
                        os.remove(file_path)
                        logger.info(f"Removed old audio file: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to remove old audio file {file_path}: {str(e)}")
                        
        except Exception as e:
            logger.error(f"Failed to clean up old audio files: {str(e)}") 