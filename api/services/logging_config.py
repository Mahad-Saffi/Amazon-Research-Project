"""
Logging Configuration for Research Pipeline

Creates a separate log file for each run with timestamp.
"""
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional


class RunLogger:
    """Manages logging for individual pipeline runs"""
    
    def __init__(self, request_id: str):
        self.request_id = request_id
        self.log_file = None
        self.file_handler = None
        self.logger = None
        
    def setup(self) -> logging.Logger:
        """Setup logging for this run"""
        # Create logs directory
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = logs_dir / f"run_{timestamp}_{self.request_id}.log"
        
        # Create logger
        self.logger = logging.getLogger(f"run_{self.request_id}")
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # Create file handler
        self.file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        self.file_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.file_handler.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(self.file_handler)
        
        # Also log to console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        self.logger.info(f"=== Run started: {self.request_id} ===")
        self.logger.info(f"Log file: {self.log_file}")
        
        return self.logger
    
    def cleanup(self):
        """Cleanup logging handlers"""
        if self.logger:
            self.logger.info(f"=== Run completed: {self.request_id} ===")
            
            if self.file_handler:
                self.file_handler.close()
                self.logger.removeHandler(self.file_handler)
            
            # Remove console handler
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)
    
    def get_log_file_path(self) -> Optional[str]:
        """Get the path to the log file"""
        return str(self.log_file) if self.log_file else None


def setup_run_logger(request_id: str) -> RunLogger:
    """
    Setup a logger for a specific run
    
    Args:
        request_id: Unique identifier for this run
        
    Returns:
        RunLogger instance
    """
    run_logger = RunLogger(request_id)
    run_logger.setup()
    return run_logger
