#!/bin/bash
# Work Tracker Unified CLI
# Usage: ./work.sh <command> [args]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

COMMAND=$1
shift

case $COMMAND in
    # Activity logging
    log)
        python3 auto_logger.py "$@"
        ;;
    script)
        python3 auto_logger.py script "$@"
        ;;
    research)
        python3 auto_logger.py research "$@"
        ;;
    analysis)
        python3 auto_logger.py analysis "$@"
        ;;
    
    # Task queue
    task-add)
        python3 task_queue.py add "$@"
        ;;
    task-start)
        python3 task_queue.py start "$@"
        ;;
    task-complete)
        python3 task_queue.py complete "$@"
        ;;
    task-list)
        python3 task_queue.py list "$@"
        ;;
    task-next)
        python3 task_queue.py next
        ;;
    task-stats)
        python3 task_queue.py stats
        ;;
    
    # Agent monitoring
    agent-scan)
        python3 agent_monitor.py scan
        ;;
    agent-summary)
        python3 agent_monitor.py summary
        ;;
    
    # Combined
    status)
        echo "=== Task Queue ==="
        python3 task_queue.py list
        echo ""
        echo "=== Agent Activity ==="
        python3 agent_monitor.py summary
        ;;
    
    # Help
    help|--help|-h)
        echo "Work Tracker Unified CLI"
        echo ""
        echo "Activity Logging:"
        echo "  ./work.sh log <type> <description>     - Log generic activity"
        echo "  ./work.sh script <name> <desc>         - Log script build"
        echo "  ./work.sh research <topic> <findings>  - Log research"
        echo "  ./work.sh analysis <subject> <result> - Log analysis"
        echo ""
        echo "Task Queue:"
        echo "  ./work.sh task-add <title> <desc> [priority] [tags]"
        echo "  ./work.sh task-start <task_id>"
        echo "  ./work.sh task-complete <task_id>"
        echo "  ./work.sh task-list [status]"
        echo "  ./work.sh task-next"
        echo "  ./work.sh task-stats"
        echo ""
        echo "Agent Monitoring:"
        echo "  ./work.sh agent-scan                 - Scan all agents"
        echo "  ./work.sh agent-summary              - Daily summary"
        echo ""
        echo "Combined:"
        echo "  ./work.sh status                     - Full status report"
        ;;
    
    *)
        echo "Unknown command: $COMMAND"
        echo "Run './work.sh help' for usage"
        exit 1
        ;;
esac
