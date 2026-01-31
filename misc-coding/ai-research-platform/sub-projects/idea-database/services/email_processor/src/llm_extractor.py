import httpx
import logging
import asyncpg

# FIXED: Use correct AI processor service name and port
AI_PROCESSOR_URL = "http://idea_db_ai_processor:8000/process/email"

logger = logging.getLogger("llm_extractor")

async def call_llm_extractor(email_data: dict) -> dict:
    """
    Call the AI Processor LLM extraction endpoint with parsed email data.
    Returns a dict with 'entities', 'categories', 'sentiment', etc.
    """
    try:
        # Map email_parser format to AI Processor expected format
        # Convert attachment objects to just filenames (strings)
        attachments = email_data.get("attachments", [])
        attachment_filenames = []
        if attachments:
            for att in attachments:
                if isinstance(att, dict):
                    # Extract filename from attachment object
                    filename = att.get("filename") or att.get("original_filename", "")
                    if filename:
                        attachment_filenames.append(filename)
                elif isinstance(att, str):
                    # Already a string filename
                    attachment_filenames.append(att)
        
        ai_processor_payload = {
            "email_id": email_data["email_id"],
            "subject": email_data["subject"], 
            "body": email_data["body"],
            "sender": email_data["sender"],
            "timestamp": email_data["timestamp"],
            "attachments": attachment_filenames
        }
        
        logger.info(f"Calling AI Processor at {AI_PROCESSOR_URL} for email {email_data['email_id']}")
        
        async with httpx.AsyncClient(timeout=60) as client:  # Increased timeout for LLM processing
            response = await client.post(AI_PROCESSOR_URL, json=ai_processor_payload)
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"AI Processor response received for email {email_data['email_id']}: "
                       f"{len(data.get('entities', []))} entities, "
                       f"categories: {data.get('categories', [])}, "
                       f"status: {data.get('processing_status', 'unknown')}")
            
            # Return data in format expected by email_parser
            return {
                "entities": data.get("entities", []),  # AI processor returns 'entities' 
                "categories": data.get("categories", []),
                "sentiment": data.get("sentiment", {}),
                "priority_score": data.get("priority_score", 0.5),
                "processing_status": data.get("processing_status", "completed")
            }
            
    except httpx.TimeoutException as e:
        logger.error(f"AI Processor timeout: {e}")
        return {"error": f"AI Processor timeout: {str(e)}"}
    except httpx.HTTPStatusError as e:
        response_text = e.response.text if hasattr(e.response, 'text') else str(e.response.content)
        logger.error(f"AI Processor HTTP error: {e.response.status_code} - {response_text}")
        return {"error": f"AI Processor HTTP error: {e.response.status_code} - {response_text}"}
    except Exception as e:
        logger.error(f"LLM extraction failed: {e}")
        return {"error": f"LLM extraction failed: {str(e)}"}

async def get_taxonomy_types(postgres_url: str):
    """
    LEGACY FUNCTION - No longer used in modern pipeline
    AI Processor handles taxonomy validation internally
    """
    # This function is kept for backward compatibility but not used
    return set(), set() 