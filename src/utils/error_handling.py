"""
Enhanced Error Handling for JEDEC Insight
Provides comprehensive error handling for PDF processing, API calls, and system operations.
"""

import logging
import traceback
import functools
import asyncio
from typing import Any, Callable, Optional, Dict, List
from pathlib import Path
import requests
import time
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Error types for categorization."""
    PDF_PROCESSING = "pdf_processing"
    API_TIMEOUT = "api_timeout"
    API_CONNECTION = "api_connection"
    FILE_NOT_FOUND = "file_not_found"
    PERMISSION_ERROR = "permission_error"
    MEMORY_ERROR = "memory_error"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN_ERROR = "unknown_error"


class JEDECError(Exception):
    """Custom exception for JEDEC Insight errors."""
    
    def __init__(self, message: str, error_type: ErrorType = ErrorType.UNKNOWN_ERROR, 
                 details: Optional[Dict] = None, original_exception: Optional[Exception] = None):
        super().__init__(message)
        self.error_type = error_type
        self.details = details or {}
        self.original_exception = original_exception
        self.timestamp = time.time()


def handle_errors(error_type: ErrorType = ErrorType.UNKNOWN_ERROR, 
                 reraise: bool = True, 
                 default_return: Any = None,
                 log_level: int = logging.ERROR):
    """
    Decorator for error handling.
    
    Args:
        error_type: Type of error to categorize
        reraise: Whether to reraise the exception
        default_return: Default return value on error
        log_level: Logging level for the error
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Create JEDEC error
                jedec_error = JEDECError(
                    message=str(e),
                    error_type=error_type,
                    details={
                        "function": func.__name__,
                        "args": str(args)[:200],  # Limit length
                        "kwargs": str(kwargs)[:200]
                    },
                    original_exception=e
                )
                
                # Log the error
                logger.log(log_level, f"Error in {func.__name__}: {jedec_error.message}")
                logger.debug(f"Full traceback: {traceback.format_exc()}")
                
                if reraise:
                    raise jedec_error
                else:
                    return default_return
        
        return wrapper
    return decorator


def handle_async_errors(error_type: ErrorType = ErrorType.UNKNOWN_ERROR,
                      reraise: bool = True,
                      default_return: Any = None,
                      log_level: int = logging.ERROR):
    """
    Decorator for async error handling.
    
    Args:
        error_type: Type of error to categorize
        reraise: Whether to reraise the exception
        default_return: Default return value on error
        log_level: Logging level for the error
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Create JEDEC error
                jedec_error = JEDECError(
                    message=str(e),
                    error_type=error_type,
                    details={
                        "function": func.__name__,
                        "args": str(args)[:200],
                        "kwargs": str(kwargs)[:200]
                    },
                    original_exception=e
                )
                
                # Log the error
                logger.log(log_level, f"Async error in {func.__name__}: {jedec_error.message}")
                logger.debug(f"Full traceback: {traceback.format_exc()}")
                
                if reraise:
                    raise jedec_error
                else:
                    return default_return
        
        return wrapper
    return decorator


class PDFErrorHandler:
    """Specialized error handler for PDF processing."""
    
    @staticmethod
    @handle_errors(error_type=ErrorType.PDF_PROCESSING, reraise=False, default_return=None)
    def safe_pdf_processing(func: Callable, file_path: str, *args, **kwargs):
        """
        Safely execute PDF processing with error handling.
        
        Args:
            func: PDF processing function
            file_path: Path to PDF file
            *args, **kwargs: Additional arguments
            
        Returns:
            Processing result or None on error
        """
        # Check if file exists
        if not Path(file_path).exists():
            raise JEDECError(
                f"PDF file not found: {file_path}",
                error_type=ErrorType.FILE_NOT_FOUND,
                details={"file_path": str(file_path)}
            )
        
        # Check file size
        file_size = Path(file_path).stat().st_size
        max_size = 50 * 1024 * 1024  # 50MB
        if file_size > max_size:
            raise JEDECError(
                f"PDF file too large: {file_size} bytes (max: {max_size})",
                error_type=ErrorType.VALIDATION_ERROR,
                details={"file_size": file_size, "max_size": max_size}
            )
        
        # Execute processing
        return func(file_path, *args, **kwargs)
    
    @staticmethod
    def get_pdf_error_suggestion(error: JEDECError) -> str:
        """
        Get user-friendly suggestion for PDF errors.
        
        Args:
            error: JEDEC error
            
        Returns:
            Suggestion message
        """
        suggestions = {
            ErrorType.FILE_NOT_FOUND: "PDF 파일을 확인하고 다시 업로드해주세요.",
            ErrorType.PERMISSION_ERROR: "파일 권한을 확인하고 다시 시도해주세요.",
            ErrorType.VALIDATION_ERROR: "파일이 손상되었거나 지원되지 않는 형식입니다. 다른 PDF를 시도해주세요.",
            ErrorType.MEMORY_ERROR: "파일이 너무 큽니다. 더 작은 PDF로 나누거나 시스템 메모리를 확인해주세요.",
        }
        
        return suggestions.get(error.error_type, "PDF 처리 중 오류가 발생했습니다. 관리자에게 문의해주세요.")


class APIErrorHandler:
    """Specialized error handler for API calls."""
    
    @staticmethod
    @handle_async_errors(error_type=ErrorType.API_TIMEOUT, reraise=False, default_return=None)
    async def safe_api_call(func: Callable, url: str, timeout: int = 30, max_retries: int = 3, *args, **kwargs):
        """
        Safely execute API call with retry logic.
        
        Args:
            func: API function (requests.get, requests.post, etc.)
            url: API URL
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
            *args, **kwargs: Additional arguments
            
        Returns:
            API response or None on error
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                response = func(url, timeout=timeout, *args, **kwargs)
                response.raise_for_status()
                return response.json() if response.content else None
                
            except requests.exceptions.Timeout as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"API timeout (attempt {attempt + 1}), retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise JEDECError(
                        f"API timeout after {max_retries} retries: {url}",
                        error_type=ErrorType.API_TIMEOUT,
                        details={"url": url, "timeout": timeout, "attempts": max_retries + 1}
                    )
            
            except requests.exceptions.ConnectionError as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(f"API connection error (attempt {attempt + 1}), retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise JEDECError(
                        f"API connection failed after {max_retries} retries: {url}",
                        error_type=ErrorType.API_CONNECTION,
                        details={"url": url, "attempts": max_retries + 1}
                    )
            
            except requests.exceptions.HTTPError as e:
                raise JEDECError(
                    f"API HTTP error: {e.response.status_code} - {e.response.text}",
                    error_type=ErrorType.VALIDATION_ERROR,
                    details={"url": url, "status_code": e.response.status_code}
                )
            
            except Exception as e:
                raise JEDECError(
                    f"Unexpected API error: {str(e)}",
                    error_type=ErrorType.UNKNOWN_ERROR,
                    details={"url": url, "original_error": str(e)}
                )
    
    @staticmethod
    def get_api_error_suggestion(error: JEDECError) -> str:
        """
        Get user-friendly suggestion for API errors.
        
        Args:
            error: JEDEC error
            
        Returns:
            Suggestion message
        """
        suggestions = {
            ErrorType.API_TIMEOUT: "서버 응답이 지연되고 있습니다. 잠시 후 다시 시도해주세요.",
            ErrorType.API_CONNECTION: "서버에 연결할 수 없습니다. 네트워크 연결을 확인해주세요.",
            ErrorType.VALIDATION_ERROR: "요청 형식이 올바르지 않습니다. 입력값을 확인해주세요.",
        }
        
        return suggestions.get(error.error_type, "API 호출 중 오류가 발생했습니다. 관리자에게 문의해주세요.")


class SystemErrorHandler:
    """System-wide error handler."""
    
    def __init__(self):
        self.error_counts = {}
        self.error_threshold = 10  # Threshold for error alerts
        self.time_window = 300  # 5 minutes
    
    def record_error(self, error: JEDECError):
        """
        Record an error for monitoring.
        
        Args:
            error: JEDEC error to record
        """
        error_key = f"{error.error_type.value}_{error.details.get('function', 'unknown')}"
        current_time = time.time()
        
        if error_key not in self.error_counts:
            self.error_counts[error_key] = []
        
        # Clean old errors outside time window
        self.error_counts[error_key] = [
            timestamp for timestamp in self.error_counts[error_key]
            if current_time - timestamp < self.time_window
        ]
        
        # Add current error
        self.error_counts[error_key].append(current_time)
        
        # Check threshold
        if len(self.error_counts[error_key]) >= self.error_threshold:
            logger.error(f"Error threshold exceeded for {error_key}: {len(self.error_counts[error_key])} errors in {self.time_window}s")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """
        Get error statistics.
        
        Returns:
            Dictionary with error statistics
        """
        current_time = time.time()
        stats = {}
        
        for error_key, timestamps in self.error_counts.items():
            # Clean old errors
            recent_timestamps = [
                timestamp for timestamp in timestamps
                if current_time - timestamp < self.time_window
            ]
            self.error_counts[error_key] = recent_timestamps
            
            stats[error_key] = {
                "count": len(recent_timestamps),
                "error_type": error_key.split("_")[0],
                "function": "_".join(error_key.split("_")[1:])
            }
        
        return stats


# Global error handler instance
system_error_handler = SystemErrorHandler()


def get_system_error_handler() -> SystemErrorHandler:
    """Get global system error handler."""
    return system_error_handler


def create_error_response(error: JEDECError, include_suggestion: bool = True) -> Dict[str, Any]:
    """
    Create standardized error response.
    
    Args:
        error: JEDEC error
        include_suggestion: Whether to include user-friendly suggestion
        
    Returns:
        Error response dictionary
    """
    response = {
        "error": True,
        "error_type": error.error_type.value,
        "message": error.message,
        "timestamp": error.timestamp,
        "details": error.details
    }
    
    if include_suggestion:
        if error.error_type == ErrorType.PDF_PROCESSING:
            response["suggestion"] = PDFErrorHandler.get_pdf_error_suggestion(error)
        elif error.error_type in [ErrorType.API_TIMEOUT, ErrorType.API_CONNECTION, ErrorType.VALIDATION_ERROR]:
            response["suggestion"] = APIErrorHandler.get_api_error_suggestion(error)
        else:
            response["suggestion"] = "문제가 지속되면 관리자에게 문의해주세요."
    
    return response


# Context manager for error handling
class ErrorContext:
    """Context manager for error handling."""
    
    def __init__(self, error_type: ErrorType = ErrorType.UNKNOWN_ERROR, 
                 operation: str = "operation", 
                 reraise: bool = True):
        self.error_type = error_type
        self.operation = operation
        self.reraise = reraise
        self.error = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.error = JEDECError(
                message=str(exc_val),
                error_type=self.error_type,
                details={"operation": self.operation},
                original_exception=exc_val
            )
            
            # Record error
            system_error_handler.record_error(self.error)
            
            if not self.reraise:
                return True  # Suppress exception
        
        return False


# Example usage
if __name__ == "__main__":
    # Test error handling
    try:
        with ErrorContext(ErrorType.PDF_PROCESSING, "test_operation"):
            raise FileNotFoundError("Test PDF not found")
    except JEDECError as e:
        print(f"Caught JEDEC error: {e}")
        print(f"Error response: {create_error_response(e)}")
