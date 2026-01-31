"""
WebSocket Manager for Real-Time Updates
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Set, Any
from fastapi import WebSocket
import structlog

logger = structlog.get_logger()


class WebSocketManager:
    """
    Manages WebSocket connections for real-time job updates.
    """
    
    def __init__(self):
        # Map of job_id -> set of websockets
        self.job_connections: Dict[str, Set[WebSocket]] = {}
        # Map of websocket -> job_id for cleanup
        self.websocket_jobs: Dict[WebSocket, str] = {}
        # Global connections (not tied to specific jobs)
        self.global_connections: Set[WebSocket] = set()
        self.connection_count = 0
    
    async def connect(self, websocket: WebSocket, job_id: str = None) -> bool:
        """
        Accept a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection
            job_id: Optional job ID to associate with this connection
            
        Returns:
            bool: True if connection accepted, False otherwise
        """
        try:
            await websocket.accept()
            
            if job_id:
                # Job-specific connection
                if job_id not in self.job_connections:
                    self.job_connections[job_id] = set()
                
                self.job_connections[job_id].add(websocket)
                self.websocket_jobs[websocket] = job_id
                
                logger.info(f"WebSocket connected for job {job_id}")
                
                # Send initial connection confirmation
                await websocket.send_json({
                    "type": "connection_established",
                    "job_id": job_id,
                    "timestamp": datetime.now().isoformat(),
                    "message": f"Connected to job {job_id} updates"
                })
                
            else:
                # Global connection
                self.global_connections.add(websocket)
                
                logger.info("Global WebSocket connected")
                
                # Send initial connection confirmation
                await websocket.send_json({
                    "type": "connection_established",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Connected to global updates"
                })
            
            self.connection_count += 1
            return True
            
        except Exception as e:
            logger.error(f"Failed to accept WebSocket connection: {e}")
            return False
    
    def disconnect(self, websocket: WebSocket, job_id: str = None) -> None:
        """
        Disconnect a WebSocket connection.
        
        Args:
            websocket: The WebSocket connection to disconnect
            job_id: Optional job ID if known
        """
        try:
            # Remove from job-specific connections
            if websocket in self.websocket_jobs:
                stored_job_id = self.websocket_jobs[websocket]
                
                if stored_job_id in self.job_connections:
                    self.job_connections[stored_job_id].discard(websocket)
                    
                    # Clean up empty job connection sets
                    if not self.job_connections[stored_job_id]:
                        del self.job_connections[stored_job_id]
                
                del self.websocket_jobs[websocket]
                logger.info(f"WebSocket disconnected from job {stored_job_id}")
            
            # Remove from global connections
            if websocket in self.global_connections:
                self.global_connections.discard(websocket)
                logger.info("Global WebSocket disconnected")
            
            # Also check by job_id if provided
            if job_id and job_id in self.job_connections:
                self.job_connections[job_id].discard(websocket)
                if not self.job_connections[job_id]:
                    del self.job_connections[job_id]
            
            self.connection_count = max(0, self.connection_count - 1)
            
        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {e}")
    
    async def broadcast_to_job(self, job_id: str, message: Dict[str, Any]) -> int:
        """
        Broadcast a message to all connections listening to a specific job.
        
        Args:
            job_id: The job ID to broadcast to
            message: The message to send
            
        Returns:
            int: Number of connections the message was sent to
        """
        if job_id not in self.job_connections:
            return 0
        
        connections = self.job_connections[job_id].copy()  # Copy to avoid modification during iteration
        sent_count = 0
        disconnected_websockets = []
        
        for websocket in connections:
            try:
                await websocket.send_json(message)
                sent_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to send message to WebSocket for job {job_id}: {e}")
                disconnected_websockets.append(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected_websockets:
            self.disconnect(websocket, job_id)
        
        return sent_count
    
    async def broadcast_global(self, message: Dict[str, Any]) -> int:
        """
        Broadcast a message to all global connections.
        
        Args:
            message: The message to send
            
        Returns:
            int: Number of connections the message was sent to
        """
        connections = self.global_connections.copy()  # Copy to avoid modification during iteration
        sent_count = 0
        disconnected_websockets = []
        
        for websocket in connections:
            try:
                await websocket.send_json(message)
                sent_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to send global message to WebSocket: {e}")
                disconnected_websockets.append(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected_websockets:
            self.disconnect(websocket)
        
        return sent_count
    
    async def send_job_notification(
        self, 
        job_id: str, 
        notification_type: str, 
        title: str, 
        message: str,
        data: Dict[str, Any] = None
    ) -> int:
        """
        Send a formatted notification to job connections.
        
        Args:
            job_id: The job ID to send to
            notification_type: Type of notification (info, success, warning, error)
            title: Notification title
            message: Notification message
            data: Optional additional data
            
        Returns:
            int: Number of connections the notification was sent to
        """
        notification = {
            "type": "notification",
            "notification_type": notification_type,
            "job_id": job_id,
            "title": title,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        }
        
        return await self.broadcast_to_job(job_id, notification)
    
    async def send_system_notification(
        self, 
        notification_type: str, 
        title: str, 
        message: str,
        data: Dict[str, Any] = None
    ) -> int:
        """
        Send a system-wide notification to all connections.
        
        Args:
            notification_type: Type of notification (info, success, warning, error)
            title: Notification title
            message: Notification message
            data: Optional additional data
            
        Returns:
            int: Number of connections the notification was sent to
        """
        notification = {
            "type": "system_notification",
            "notification_type": notification_type,
            "title": title,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        }
        
        # Send to both global and all job-specific connections
        global_count = await self.broadcast_global(notification)
        job_count = 0
        
        for job_id in list(self.job_connections.keys()):
            job_count += await self.broadcast_to_job(job_id, notification)
        
        return global_count + job_count
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about current connections.
        
        Returns:
            Dict with connection statistics
        """
        job_connection_count = sum(len(connections) for connections in self.job_connections.values())
        
        return {
            "total_connections": self.connection_count,
            "global_connections": len(self.global_connections),
            "job_connections": job_connection_count,
            "active_jobs": len(self.job_connections),
            "jobs_with_connections": list(self.job_connections.keys())
        }
    
    async def ping_all_connections(self) -> Dict[str, Any]:
        """
        Send a ping message to all connections to check health.
        
        Returns:
            Dict with ping results
        """
        ping_message = {
            "type": "ping",
            "timestamp": datetime.now().isoformat(),
            "message": "Connection health check"
        }
        
        global_pings = await self.broadcast_global(ping_message)
        job_pings = 0
        
        for job_id in list(self.job_connections.keys()):
            job_pings += await self.broadcast_to_job(job_id, ping_message)
        
        return {
            "ping_sent_at": datetime.now().isoformat(),
            "global_pings_sent": global_pings,
            "job_pings_sent": job_pings,
            "total_pings_sent": global_pings + job_pings
        }
    
    async def cleanup_stale_connections(self) -> int:
        """
        Clean up stale WebSocket connections.
        
        Returns:
            int: Number of connections cleaned up
        """
        cleaned_count = 0
        
        # Check global connections
        stale_global = []
        for websocket in self.global_connections.copy():
            try:
                # Try to send a small ping to check if connection is alive
                await websocket.ping()
            except:
                stale_global.append(websocket)
        
        for websocket in stale_global:
            self.disconnect(websocket)
            cleaned_count += 1
        
        # Check job connections
        stale_job_connections = []
        for job_id, connections in self.job_connections.items():
            for websocket in connections.copy():
                try:
                    await websocket.ping()
                except:
                    stale_job_connections.append((websocket, job_id))
        
        for websocket, job_id in stale_job_connections:
            self.disconnect(websocket, job_id)
            cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} stale WebSocket connections")
        
        return cleaned_count
    
    @property
    def active_connections(self) -> int:
        """Get the number of active connections."""
        return self.connection_count 