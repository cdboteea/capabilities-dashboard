"""Data models for the X Post Content Extraction Service."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime


class ExtractRequest(BaseModel):
    """Request model for post extraction."""
    urls: List[str] = Field(..., description="List of X post URLs to extract content from")
    
    class Config:
        schema_extra = {
            "example": {
                "urls": [
                    "https://x.com/username/status/1234567890",
                    "https://twitter.com/username/status/0987654321"
                ]
            }
        }


class Author(BaseModel):
    """Author information model."""
    username: str = Field(..., description="Username without @ symbol")
    display_name: str = Field(..., description="Display name of the user")
    profile_image_url: Optional[str] = Field(None, description="Profile image URL")
    verified: bool = Field(False, description="Whether the account is verified")


class Engagement(BaseModel):
    """Engagement metrics model."""
    likes: int = Field(0, description="Number of likes")
    retweets: int = Field(0, description="Number of retweets")
    replies: int = Field(0, description="Number of replies")
    quotes: int = Field(0, description="Number of quote tweets")


class UrlInfo(BaseModel):
    """URL information model."""
    display_url: str = Field(..., description="Shortened or display URL")
    expanded_url: str = Field(..., description="Full expanded URL")
    title: Optional[str] = Field(None, description="Page title if available")
    description: Optional[str] = Field(None, description="Page description if available")


class MediaItem(BaseModel):
    """Media item model."""
    type: str = Field(..., description="Media type: image, video, gif")
    url: str = Field(..., description="Direct URL to media")
    preview_url: Optional[str] = Field(None, description="Preview/thumbnail URL")
    alt_text: Optional[str] = Field(None, description="Alt text or description")
    width: Optional[int] = Field(None, description="Media width in pixels")
    height: Optional[int] = Field(None, description="Media height in pixels")


class ReferencedDocument(BaseModel):
    """Referenced document model."""
    url: str = Field(..., description="Document URL")
    type: str = Field(..., description="Document type: PDF, Google Doc, etc.")
    title: Optional[str] = Field(None, description="Document title")
    description: Optional[str] = Field(None, description="Document description")


class PostContent(BaseModel):
    """Extracted post content model."""
    post_url: str = Field(..., description="Original post URL")
    post_id: str = Field(..., description="Unique post ID")
    author: Author = Field(..., description="Author information")
    content: str = Field(..., description="Full post text content")
    timestamp: datetime = Field(..., description="Post creation timestamp")
    engagement: Engagement = Field(..., description="Engagement metrics")
    urls: List[UrlInfo] = Field(default_factory=list, description="URLs mentioned in the post")
    media: List[MediaItem] = Field(default_factory=list, description="Media attachments")
    referenced_documents: List[ReferencedDocument] = Field(default_factory=list, description="Referenced documents")
    hashtags: List[str] = Field(default_factory=list, description="Hashtags in the post")
    mentions: List[str] = Field(default_factory=list, description="User mentions in the post")
    is_reply: bool = Field(False, description="Whether this is a reply to another post")
    reply_to_post_id: Optional[str] = Field(None, description="ID of the post this is replying to")
    is_retweet: bool = Field(False, description="Whether this is a retweet")
    original_post_id: Optional[str] = Field(None, description="ID of the original post if this is a retweet")


class ExtractResponse(BaseModel):
    """Response model for post extraction."""
    success: bool = Field(..., description="Whether the extraction was successful")
    posts: List[PostContent] = Field(default_factory=list, description="Extracted post data")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Errors encountered during extraction")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "posts": [
                    {
                        "post_url": "https://x.com/username/status/1234567890",
                        "post_id": "1234567890",
                        "author": {
                            "username": "username",
                            "display_name": "Display Name",
                            "verified": False
                        },
                        "content": "This is a sample tweet content",
                        "timestamp": "2024-01-01T12:00:00Z",
                        "engagement": {
                            "likes": 10,
                            "retweets": 5,
                            "replies": 2,
                            "quotes": 1
                        },
                        "urls": [],
                        "media": [],
                        "referenced_documents": [],
                        "hashtags": [],
                        "mentions": [],
                        "is_reply": False,
                        "is_retweet": False
                    }
                ],
                "errors": []
            }
        }


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Current timestamp")
    version: str = Field(..., description="Service version")
    uptime: float = Field(..., description="Service uptime in seconds")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(..., description="Error timestamp")

