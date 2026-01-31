"""Background task processing for sentiment analysis."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from ..models.sentiment_models import SentimentResult
from ..processors.sentiment_engine import get_engine
from ..utils.database import db

logger = logging.getLogger(__name__)


class TaskStatus:
    """Task status tracking."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BackgroundTask:
    """Background task for sentiment analysis."""
    
    def __init__(self, task_id: str, task_type: str, payload: dict):
        self.task_id = task_id
        self.task_type = task_type
        self.payload = payload
        self.status = TaskStatus.PENDING
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.result: Optional[dict] = None


class TaskManager:
    """Manages background sentiment analysis tasks."""
    
    def __init__(self):
        self._tasks: Dict[str, BackgroundTask] = {}
        self._queue = asyncio.Queue()
        self._workers_running = False
        self._worker_tasks: List[asyncio.Task] = []
    
    async def start_workers(self, num_workers: int = 2):
        """Start background worker tasks."""
        if self._workers_running:
            return
        
        self._workers_running = True
        for i in range(num_workers):
            worker_task = asyncio.create_task(self._worker(f"worker-{i}"))
            self._worker_tasks.append(worker_task)
        
        logger.info(f"Started {num_workers} sentiment analysis workers")
    
    async def stop_workers(self):
        """Stop background worker tasks."""
        self._workers_running = False
        
        # Cancel all worker tasks
        for task in self._worker_tasks:
            task.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()
        
        logger.info("Stopped sentiment analysis workers")
    
    async def submit_batch_analysis(self, texts: List[str], entities: Optional[List[str]] = None, 
                                  sector: Optional[str] = None) -> str:
        """Submit batch sentiment analysis task."""
        task_id = str(uuid4())
        task = BackgroundTask(
            task_id=task_id,
            task_type="batch_analysis",
            payload={
                "texts": texts,
                "entities": entities,
                "sector": sector
            }
        )
        
        self._tasks[task_id] = task
        await self._queue.put(task)
        
        logger.info(f"Submitted batch analysis task {task_id} with {len(texts)} texts")
        return task_id
    
    async def submit_event_analysis(self, event_id: str, text: str, entities: Optional[List[str]] = None,
                                  sector: Optional[str] = None) -> str:
        """Submit single event sentiment analysis task."""
        task_id = str(uuid4())
        task = BackgroundTask(
            task_id=task_id,
            task_type="event_analysis",
            payload={
                "event_id": event_id,
                "text": text,
                "entities": entities,
                "sector": sector
            }
        )
        
        self._tasks[task_id] = task
        await self._queue.put(task)
        
        logger.info(f"Submitted event analysis task {task_id} for event {event_id}")
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get task status and result."""
        task = self._tasks.get(task_id)
        if not task:
            return None
        
        return {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "status": task.status,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error_message": task.error_message,
            "result": task.result
        }
    
    def get_queue_status(self) -> Dict:
        """Get queue status and metrics."""
        pending_tasks = sum(1 for task in self._tasks.values() if task.status == TaskStatus.PENDING)
        running_tasks = sum(1 for task in self._tasks.values() if task.status == TaskStatus.RUNNING)
        completed_tasks = sum(1 for task in self._tasks.values() if task.status == TaskStatus.COMPLETED)
        failed_tasks = sum(1 for task in self._tasks.values() if task.status == TaskStatus.FAILED)
        
        return {
            "queue_size": self._queue.qsize(),
            "workers_running": self._workers_running,
            "active_workers": len(self._worker_tasks),
            "pending_tasks": pending_tasks,
            "running_tasks": running_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "total_tasks": len(self._tasks)
        }
    
    async def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Clean up old completed/failed tasks."""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        tasks_to_remove = []
        for task_id, task in self._tasks.items():
            if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED] and 
                task.completed_at and task.completed_at < cutoff_time):
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self._tasks[task_id]
        
        if tasks_to_remove:
            logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")
    
    async def _worker(self, worker_name: str):
        """Background worker for processing sentiment analysis tasks."""
        logger.info(f"Started sentiment analysis worker: {worker_name}")
        
        while self._workers_running:
            try:
                # Get task from queue with timeout
                task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                
                # Process the task
                await self._process_task(task, worker_name)
                
            except asyncio.TimeoutError:
                # No tasks in queue, continue
                continue
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
                await asyncio.sleep(1)
        
        logger.info(f"Stopped sentiment analysis worker: {worker_name}")
    
    async def _process_task(self, task: BackgroundTask, worker_name: str):
        """Process a single sentiment analysis task."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        
        try:
            engine = get_engine()
            
            if task.task_type == "batch_analysis":
                # Process batch analysis
                texts = task.payload["texts"]
                entities = task.payload.get("entities")
                sector = task.payload.get("sector")
                
                results = await engine.analyze_batch(texts, entities, sector)
                task.result = {
                    "results": [result.model_dump() for result in results],
                    "processed_count": len(results)
                }
                
            elif task.task_type == "event_analysis":
                # Process single event analysis
                event_id = task.payload["event_id"]
                text = task.payload["text"]
                entities = task.payload.get("entities")
                sector = task.payload.get("sector")
                
                result = await engine.analyze(text, entities, sector)
                
                # Save to database
                sentiment_id = await db.save_sentiment(event_id, result)
                
                task.result = {
                    "sentiment_id": str(sentiment_id),
                    "event_id": event_id,
                    "sentiment": result.model_dump()
                }
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            
            processing_time = (task.completed_at - task.started_at).total_seconds()
            logger.info(f"Worker {worker_name} completed task {task.task_id} in {processing_time:.2f}s")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.utcnow()
            task.error_message = str(e)
            
            logger.error(f"Worker {worker_name} failed task {task.task_id}: {e}")


# Global task manager instance
task_manager = TaskManager() 