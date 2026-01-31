#!/usr/bin/env python3
"""
Chat Parser for Document Parser
Extracts content from chat exports (WhatsApp, Telegram, Discord, etc.)
"""

import asyncio
import re
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import xmltodict
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)

class ChatParser:
    """Parses chat export files"""
    
    def __init__(self):
        self.supported_formats = ['chat_export', 'whatsapp', 'telegram', 'discord', 'txt']
    
    async def parse(self, content: str, chat_type: str = 'auto', options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Parse chat export content"""
        
        if options is None:
            options = {}
        
        logger.info("Starting chat parsing", 
                   chat_type=chat_type,
                   content_length=len(content),
                   options=options)
        
        try:
            # Auto-detect chat type if not specified
            if chat_type == 'auto':
                chat_type = self._detect_chat_type(content)
            
            # Parse based on chat type
            if chat_type == 'whatsapp':
                return await self._parse_whatsapp_export(content, options)
            elif chat_type == 'telegram':
                return await self._parse_telegram_export(content, options)
            elif chat_type == 'discord':
                return await self._parse_discord_export(content, options)
            elif chat_type == 'generic':
                return await self._parse_generic_chat(content, options)
            else:
                # Fall back to generic parsing
                return await self._parse_generic_chat(content, options)
                
        except Exception as e:
            logger.error("Chat parsing failed", chat_type=chat_type, error=str(e))
            return {
                "title": f"Chat Export Parsing Failed ({chat_type})",
                "content": f"Error parsing {chat_type} chat: {str(e)}",
                "metadata": {"error": str(e), "chat_type": chat_type},
                "structure": {},
                "stats": {"error": True}
            }
    
    def _detect_chat_type(self, content: str) -> str:
        """Auto-detect chat export type"""
        
        content_lower = content.lower()
        
        # WhatsApp patterns
        whatsapp_patterns = [
            r'\d{1,2}/\d{1,2}/\d{2,4}, \d{1,2}:\d{2}',  # Date format
            r'- [^:]+:',  # Message format
            'whatsapp',
            'this message was deleted'
        ]
        
        # Telegram patterns
        telegram_patterns = [
            '"type": "message"',
            '"from"',
            '"date"',
            'telegram'
        ]
        
        # Discord patterns
        discord_patterns = [
            '"id":',
            '"timestamp":',
            '"content":',
            '"author":',
            'discord'
        ]
        
        # Check patterns
        if any(re.search(pattern, content, re.IGNORECASE) for pattern in whatsapp_patterns):
            return 'whatsapp'
        elif any(pattern in content_lower for pattern in telegram_patterns):
            return 'telegram'
        elif any(pattern in content_lower for pattern in discord_patterns):
            return 'discord'
        else:
            return 'generic'
    
    async def _parse_whatsapp_export(self, content: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Parse WhatsApp chat export"""
        
        try:
            messages = []
            participants = set()
            
            # WhatsApp message pattern
            message_pattern = r'(\d{1,2}/\d{1,2}/\d{2,4}), (\d{1,2}:\d{2}) - ([^:]+): (.+)'
            
            lines = content.split('\n')
            current_message = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                match = re.match(message_pattern, line)
                if match:
                    # Save previous message if exists
                    if current_message:
                        messages.append(current_message)
                    
                    date_str, time_str, sender, message_text = match.groups()
                    participants.add(sender)
                    
                    # Parse datetime
                    try:
                        datetime_str = f"{date_str}, {time_str}"
                        # Try different date formats
                        for fmt in ['%m/%d/%y, %H:%M', '%d/%m/%y, %H:%M', '%m/%d/%Y, %H:%M', '%d/%m/%Y, %H:%M']:
                            try:
                                parsed_datetime = datetime.strptime(datetime_str, fmt)
                                break
                            except ValueError:
                                continue
                        else:
                            parsed_datetime = None
                    except Exception:
                        parsed_datetime = None
                    
                    current_message = {
                        "timestamp": parsed_datetime.isoformat() if parsed_datetime else datetime_str,
                        "sender": sender,
                        "content": message_text,
                        "type": "text"
                    }
                else:
                    # Continuation of previous message
                    if current_message:
                        current_message["content"] += "\n" + line
            
            # Add last message
            if current_message:
                messages.append(current_message)
            
            # Generate content summary
            content_parts = []
            for msg in messages:
                content_parts.append(f"{msg['sender']}: {msg['content']}")
            
            full_content = '\n\n'.join(content_parts)
            
            # Analyze conversation
            stats = self._analyze_conversation(messages)
            
            result = {
                "title": "WhatsApp Chat Export",
                "content": full_content,
                "metadata": {
                    "chat_type": "whatsapp",
                    "parser": "whatsapp_regex",
                    "participants": list(participants),
                    "participant_count": len(participants),
                    "date_range": self._get_date_range(messages)
                },
                "structure": {
                    "messages": messages if options.get("include_messages", False) else [],
                    "participants": list(participants),
                    "message_types": self._get_message_types(messages)
                },
                "stats": {
                    **stats,
                    "word_count": len(full_content.split()),
                    "character_count": len(full_content)
                }
            }
            
            logger.info("WhatsApp chat parsing completed",
                       message_count=len(messages),
                       participant_count=len(participants))
            
            return result
            
        except Exception as e:
            logger.error("WhatsApp chat parsing failed", error=str(e))
            raise
    
    async def _parse_telegram_export(self, content: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Telegram chat export (JSON format)"""
        
        try:
            # Try to parse as JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # Fall back to generic parsing
                return await self._parse_generic_chat(content, options)
            
            messages = []
            participants = set()
            
            # Extract messages from Telegram JSON structure
            chat_messages = data.get('messages', [])
            
            for msg in chat_messages:
                if msg.get('type') == 'message':
                    sender = msg.get('from', 'Unknown')
                    participants.add(sender)
                    
                    # Extract text content
                    text_content = ""
                    if isinstance(msg.get('text'), str):
                        text_content = msg['text']
                    elif isinstance(msg.get('text'), list):
                        # Handle rich text format
                        text_parts = []
                        for part in msg['text']:
                            if isinstance(part, str):
                                text_parts.append(part)
                            elif isinstance(part, dict) and 'text' in part:
                                text_parts.append(part['text'])
                        text_content = ''.join(text_parts)
                    
                    message_obj = {
                        "timestamp": msg.get('date', ''),
                        "sender": sender,
                        "content": text_content,
                        "type": "text",
                        "id": msg.get('id')
                    }
                    
                    # Handle media messages
                    if 'photo' in msg:
                        message_obj["type"] = "photo"
                        message_obj["media_info"] = {"type": "photo"}
                    elif 'file' in msg:
                        message_obj["type"] = "file"
                        message_obj["media_info"] = msg.get('file', {})
                    
                    messages.append(message_obj)
            
            # Generate content summary
            content_parts = []
            for msg in messages:
                if msg['type'] == 'text':
                    content_parts.append(f"{msg['sender']}: {msg['content']}")
                else:
                    content_parts.append(f"{msg['sender']}: [{msg['type'].upper()}]")
            
            full_content = '\n\n'.join(content_parts)
            
            # Analyze conversation
            stats = self._analyze_conversation(messages)
            
            # Extract chat metadata
            chat_info = data.get('about', 'Telegram Chat')
            chat_name = data.get('name', 'Unknown Chat')
            
            result = {
                "title": f"Telegram Chat: {chat_name}",
                "content": full_content,
                "metadata": {
                    "chat_type": "telegram",
                    "parser": "telegram_json",
                    "chat_name": chat_name,
                    "chat_info": chat_info,
                    "participants": list(participants),
                    "participant_count": len(participants),
                    "date_range": self._get_date_range(messages)
                },
                "structure": {
                    "messages": messages if options.get("include_messages", False) else [],
                    "participants": list(participants),
                    "message_types": self._get_message_types(messages)
                },
                "stats": {
                    **stats,
                    "word_count": len(full_content.split()),
                    "character_count": len(full_content)
                }
            }
            
            logger.info("Telegram chat parsing completed",
                       message_count=len(messages),
                       participant_count=len(participants))
            
            return result
            
        except Exception as e:
            logger.error("Telegram chat parsing failed", error=str(e))
            raise
    
    async def _parse_discord_export(self, content: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Discord chat export (JSON format)"""
        
        try:
            # Try to parse as JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                return await self._parse_generic_chat(content, options)
            
            messages = []
            participants = set()
            
            # Handle different Discord export formats
            if isinstance(data, list):
                # Array of messages
                message_list = data
            elif isinstance(data, dict) and 'messages' in data:
                # Object with messages array
                message_list = data['messages']
            else:
                # Single message object
                message_list = [data]
            
            for msg in message_list:
                author = msg.get('author', {})
                sender = author.get('username', author.get('name', 'Unknown'))
                participants.add(sender)
                
                message_obj = {
                    "timestamp": msg.get('timestamp', ''),
                    "sender": sender,
                    "content": msg.get('content', ''),
                    "type": "text",
                    "id": msg.get('id')
                }
                
                # Handle attachments
                if msg.get('attachments'):
                    message_obj["type"] = "attachment"
                    message_obj["attachments"] = msg['attachments']
                
                # Handle embeds
                if msg.get('embeds'):
                    message_obj["embeds"] = msg['embeds']
                
                messages.append(message_obj)
            
            # Generate content summary
            content_parts = []
            for msg in messages:
                if msg['content']:
                    content_parts.append(f"{msg['sender']}: {msg['content']}")
                elif msg['type'] == 'attachment':
                    content_parts.append(f"{msg['sender']}: [ATTACHMENT]")
            
            full_content = '\n\n'.join(content_parts)
            
            # Analyze conversation
            stats = self._analyze_conversation(messages)
            
            result = {
                "title": "Discord Chat Export",
                "content": full_content,
                "metadata": {
                    "chat_type": "discord",
                    "parser": "discord_json",
                    "participants": list(participants),
                    "participant_count": len(participants),
                    "date_range": self._get_date_range(messages)
                },
                "structure": {
                    "messages": messages if options.get("include_messages", False) else [],
                    "participants": list(participants),
                    "message_types": self._get_message_types(messages)
                },
                "stats": {
                    **stats,
                    "word_count": len(full_content.split()),
                    "character_count": len(full_content)
                }
            }
            
            logger.info("Discord chat parsing completed",
                       message_count=len(messages),
                       participant_count=len(participants))
            
            return result
            
        except Exception as e:
            logger.error("Discord chat parsing failed", error=str(e))
            raise
    
    async def _parse_generic_chat(self, content: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Parse generic chat format"""
        
        try:
            lines = content.split('\n')
            messages = []
            participants = set()
            
            # Try to extract messages using common patterns
            patterns = [
                r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) ([^:]+): (.+)',  # Standard timestamp
                r'(\d{2}:\d{2}) ([^:]+): (.+)',  # Time only
                r'([^:]+): (.+)',  # Name only
            ]
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                matched = False
                for pattern in patterns:
                    match = re.match(pattern, line)
                    if match:
                        groups = match.groups()
                        
                        if len(groups) == 3:
                            timestamp, sender, content_text = groups
                        elif len(groups) == 2:
                            sender, content_text = groups
                            timestamp = ""
                        else:
                            continue
                        
                        participants.add(sender)
                        messages.append({
                            "timestamp": timestamp,
                            "sender": sender,
                            "content": content_text,
                            "type": "text"
                        })
                        matched = True
                        break
                
                if not matched and messages:
                    # Append to last message as continuation
                    messages[-1]["content"] += "\n" + line
            
            # Generate content summary
            content_parts = []
            for msg in messages:
                content_parts.append(f"{msg['sender']}: {msg['content']}")
            
            full_content = '\n\n'.join(content_parts)
            
            # Analyze conversation
            stats = self._analyze_conversation(messages)
            
            result = {
                "title": "Generic Chat Export",
                "content": full_content,
                "metadata": {
                    "chat_type": "generic",
                    "parser": "generic_regex",
                    "participants": list(participants),
                    "participant_count": len(participants),
                    "date_range": self._get_date_range(messages)
                },
                "structure": {
                    "messages": messages if options.get("include_messages", False) else [],
                    "participants": list(participants),
                    "message_types": self._get_message_types(messages)
                },
                "stats": {
                    **stats,
                    "word_count": len(full_content.split()),
                    "character_count": len(full_content)
                }
            }
            
            logger.info("Generic chat parsing completed",
                       message_count=len(messages),
                       participant_count=len(participants))
            
            return result
            
        except Exception as e:
            logger.error("Generic chat parsing failed", error=str(e))
            raise
    
    def _analyze_conversation(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze conversation statistics"""
        
        stats = {
            "message_count": len(messages),
            "participant_stats": {},
            "message_types": {},
            "hourly_distribution": {},
            "daily_distribution": {}
        }
        
        # Analyze by participant
        for msg in messages:
            sender = msg.get('sender', 'Unknown')
            msg_type = msg.get('type', 'text')
            
            if sender not in stats["participant_stats"]:
                stats["participant_stats"][sender] = {
                    "message_count": 0,
                    "word_count": 0,
                    "character_count": 0
                }
            
            stats["participant_stats"][sender]["message_count"] += 1
            
            if msg_type == 'text':
                content = msg.get('content', '')
                stats["participant_stats"][sender]["word_count"] += len(content.split())
                stats["participant_stats"][sender]["character_count"] += len(content)
            
            # Count message types
            stats["message_types"][msg_type] = stats["message_types"].get(msg_type, 0) + 1
        
        return stats
    
    def _get_date_range(self, messages: List[Dict[str, Any]]) -> Dict[str, str]:
        """Get date range of conversation"""
        
        timestamps = [msg.get('timestamp', '') for msg in messages if msg.get('timestamp')]
        
        if not timestamps:
            return {"start": "", "end": ""}
        
        # Filter out empty timestamps and sort
        valid_timestamps = [ts for ts in timestamps if ts]
        if not valid_timestamps:
            return {"start": "", "end": ""}
        
        valid_timestamps.sort()
        
        return {
            "start": valid_timestamps[0],
            "end": valid_timestamps[-1]
        }
    
    def _get_message_types(self, messages: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get count of different message types"""
        
        types = {}
        for msg in messages:
            msg_type = msg.get('type', 'text')
            types[msg_type] = types.get(msg_type, 0) + 1
        
        return types
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported formats"""
        return self.supported_formats 