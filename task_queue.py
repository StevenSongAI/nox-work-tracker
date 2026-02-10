"""
Task Queue System - Queue and manage tasks for Nox
"""
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

QUEUE_PATH = "/Users/stevenai/Desktop/Nox Builds/nox-work-tracker-repo/data/task_queue.json"

@dataclass
class Task:
    id: str
    title: str
    description: str
    priority: str  # urgent, high, normal, low
    status: str  # pending, in_progress, completed, cancelled
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    agent: str = "nox"
    tags: List[str] = None
    estimated_time: Optional[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class TaskQueue:
    """Manage task queue for Nox"""
    
    def __init__(self):
        self.queue_path = QUEUE_PATH
        self.tasks: Dict[str, Task] = {}
        self.load()
    
    def load(self):
        """Load queue from file"""
        if os.path.exists(self.queue_path):
            with open(self.queue_path, 'r') as f:
                data = json.load(f)
                for task_id, task_dict in data.get('tasks', {}).items():
                    self.tasks[task_id] = Task(**task_dict)
    
    def save(self):
        """Save queue to file"""
        os.makedirs(os.path.dirname(self.queue_path), exist_ok=True)
        data = {
            'tasks': {k: asdict(v) for k, v in self.tasks.items()},
            'last_updated': datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
        with open(self.queue_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_task(self, title: str, description: str, priority: str = "normal",
                 tags: List[str] = None, estimated_time: str = None) -> str:
        """Add a new task to the queue"""
        task_id = f"task_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{len(self.tasks)}"
        
        task = Task(
            id=task_id,
            title=title,
            description=description,
            priority=priority,
            status="pending",
            created_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            tags=tags or [],
            estimated_time=estimated_time
        )
        
        self.tasks[task_id] = task
        self.save()
        
        print(f"✅ Task added: {title}")
        print(f"   ID: {task_id}")
        print(f"   Priority: {priority}")
        return task_id
    
    def start_task(self, task_id: str) -> bool:
        """Mark a task as in progress"""
        if task_id not in self.tasks:
            print(f"❌ Task not found: {task_id}")
            return False
        
        # Mark any other in_progress tasks as pending (only one at a time)
        for task in self.tasks.values():
            if task.status == "in_progress":
                task.status = "pending"
                task.started_at = None
        
        task = self.tasks[task_id]
        task.status = "in_progress"
        task.started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self.save()
        
        print(f"🔄 Task started: {task.title}")
        return True
    
    def complete_task(self, task_id: str) -> bool:
        """Mark a task as completed"""
        if task_id not in self.tasks:
            print(f"❌ Task not found: {task_id}")
            return False
        
        task = self.tasks[task_id]
        task.status = "completed"
        task.completed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self.save()
        
        print(f"✅ Task completed: {task.title}")
        return True
    
    def get_pending(self) -> List[Task]:
        """Get all pending tasks sorted by priority"""
        priority_order = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
        pending = [t for t in self.tasks.values() if t.status == "pending"]
        return sorted(pending, key=lambda x: priority_order.get(x.priority, 2))
    
    def get_in_progress(self) -> Optional[Task]:
        """Get currently in-progress task"""
        for task in self.tasks.values():
            if task.status == "in_progress":
                return task
        return None
    
    def get_next_task(self) -> Optional[Task]:
        """Get next highest priority pending task"""
        pending = self.get_pending()
        return pending[0] if pending else None
    
    def list_tasks(self, status: Optional[str] = None) -> List[Task]:
        """List tasks, optionally filtered by status"""
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        # Sort by status (pending first), then priority, then created date
        priority_order = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
        status_order = {"in_progress": 0, "pending": 1, "completed": 2, "cancelled": 3}
        
        return sorted(tasks, key=lambda x: (
            status_order.get(x.status, 1),
            priority_order.get(x.priority, 2),
            x.created_at
        ))
    
    def get_stats(self) -> Dict:
        """Get queue statistics"""
        stats = {"pending": 0, "in_progress": 0, "completed": 0, "cancelled": 0, "total": len(self.tasks)}
        for task in self.tasks.values():
            if task.status in stats:
                stats[task.status] += 1
        return stats
    
    def format_task_list(self, tasks: List[Task]) -> str:
        """Format task list for display"""
        if not tasks:
            return "No tasks found."
        
        lines = []
        lines.append(f"{'ID':<25} {'Status':<12} {'Priority':<8} {'Title':<40}")
        lines.append("-" * 90)
        
        for task in tasks:
            status_emoji = {
                "pending": "⏳",
                "in_progress": "🔄",
                "completed": "✅",
                "cancelled": "❌"
            }.get(task.status, "⏳")
            
            priority_emoji = {
                "urgent": "🔴",
                "high": "🟠",
                "normal": "🟡",
                "low": "🟢"
            }.get(task.priority, "🟡")
            
            short_id = task.id[:20] + "..." if len(task.id) > 20 else task.id
            title = task.title[:37] + "..." if len(task.title) > 37 else task.title
            
            lines.append(f"{short_id:<25} {status_emoji} {task.status:<10} {priority_emoji} {task.priority:<6} {title}")
        
        return "\n".join(lines)


def main():
    """CLI for task queue"""
    import sys
    
    queue = TaskQueue()
    
    if len(sys.argv) < 2:
        print("Usage: python task_queue.py <command> [args]")
        print("\nCommands:")
        print("  add <title> <description> [priority] [tags]")
        print("  start <task_id>")
        print("  complete <task_id>")
        print("  list [status]")
        print("  next")
        print("  stats")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "add":
        if len(sys.argv) < 4:
            print("Usage: add <title> <description> [priority] [tags]")
            sys.exit(1)
        title = sys.argv[2]
        description = sys.argv[3]
        priority = sys.argv[4] if len(sys.argv) > 4 else "normal"
        tags = sys.argv[5].split(",") if len(sys.argv) > 5 else []
        queue.add_task(title, description, priority, tags)
    
    elif command == "start":
        if len(sys.argv) < 3:
            print("Usage: start <task_id>")
            sys.exit(1)
        queue.start_task(sys.argv[2])
    
    elif command == "complete":
        if len(sys.argv) < 3:
            print("Usage: complete <task_id>")
            sys.exit(1)
        queue.complete_task(sys.argv[2])
    
    elif command == "list":
        status = sys.argv[2] if len(sys.argv) > 2 else None
        tasks = queue.list_tasks(status)
        print(queue.format_task_list(tasks))
    
    elif command == "next":
        task = queue.get_next_task()
        if task:
            print(f"Next task: {task.title}")
            print(f"ID: {task.id}")
            print(f"Description: {task.description}")
        else:
            print("No pending tasks!")
    
    elif command == "stats":
        stats = queue.get_stats()
        print(f"Total: {stats['total']}")
        print(f"Pending: {stats['pending']}")
        print(f"In Progress: {stats['in_progress']}")
        print(f"Completed: {stats['completed']}")
    
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
