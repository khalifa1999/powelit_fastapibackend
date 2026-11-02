from typing import Optional, Dict, Any
from pydantic import BaseModel
from enum import Enum

class ErrorCode(str, Enum):
    """Error codes for different types of errors"""
    # File upload errors
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    EMPTY_FILE = "EMPTY_FILE"
    FILE_READ_ERROR = "FILE_READ_ERROR"
    
    # Analysis errors  
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    INVALID_BLUEPRINT = "INVALID_BLUEPRINT"
    LEGEND_NOT_FOUND = "LEGEND_NOT_FOUND"
    NO_BLUEPRINT_DETECTED = "NO_BLUEPRINT_DETECTED"
    
    # Service errors
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    REQUEST_TIMEOUT = "REQUEST_TIMEOUT"
    AI_SERVICE_ERROR = "AI_SERVICE_ERROR"
    
    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    
    # Generic errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"


class ErrorResponse(BaseModel):
    """Standardized error response format"""
    error_code: ErrorCode
    user_message: str
    suggestion: str
    technical_details: Optional[str] = None
    retryable: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_code": self.error_code.value,
            "user_message": self.user_message,
            "suggestion": self.suggestion,
            "technical_details": self.technical_details,
            "retryable": self.retryable
        }


# Error message mappings
ERROR_MESSAGES = {
    ErrorCode.INVALID_FILE_TYPE: {
        "user_message": "The file type you uploaded is not supported.",
        "suggestion": "Please upload a PDF, PNG, or JPG file. Make sure the file extension matches the actual file type.",
        "retryable": True
    },
    ErrorCode.FILE_TOO_LARGE: {
        "user_message": "The file you uploaded is too large.",
        "suggestion": "Please upload a file smaller than 15MB. You can try compressing the image or splitting large PDFs into smaller sections.",
        "retryable": True
    },
    ErrorCode.EMPTY_FILE: {
        "user_message": "The file you uploaded appears to be empty or corrupted.",
        "suggestion": "Please check that the file is not empty and can be opened normally. Try re-saving the file or using a different copy.",
        "retryable": True
    },
    ErrorCode.FILE_READ_ERROR: {
        "user_message": "We couldn't read your file properly.",
        "suggestion": "The file may be corrupted or in an unsupported format. Try opening it in another application first, then re-upload.",
        "retryable": True
    },
    ErrorCode.ANALYSIS_FAILED: {
        "user_message": "We couldn't analyze your blueprint successfully.",
        "suggestion": "This could be due to poor image quality, unclear symbols, or an unsupported blueprint format. Try uploading a clearer image or a different file.",
        "retryable": True
    },
    ErrorCode.INVALID_BLUEPRINT: {
        "user_message": "The file doesn't appear to be a valid electrical blueprint.",
        "suggestion": "Please make sure you're uploading an actual electrical drawing or floor plan. The image should clearly show electrical symbols and layouts.",
        "retryable": True
    },
    ErrorCode.NO_BLUEPRINT_DETECTED: {
        "user_message": "We couldn't detect any blueprint files in your upload.",
        "suggestion": "Please upload files with names containing 'plan', 'layout', 'drawing', 'blueprint', 'floor', or 'elevation' so we can identify them correctly.",
        "retryable": True
    },
    ErrorCode.RATE_LIMIT_EXCEEDED: {
        "user_message": "You've sent too many requests recently.",
        "suggestion": "Please wait a moment and try again. Our system has rate limits to ensure fair usage for all users.",
        "retryable": True
    },
    ErrorCode.SERVICE_UNAVAILABLE: {
        "user_message": "Our analysis service is temporarily unavailable.",
        "suggestion": "The service is experiencing high demand. Please try again in a few moments.",
        "retryable": True
    },
    ErrorCode.REQUEST_TIMEOUT: {
        "user_message": "The analysis is taking longer than expected.",
        "suggestion": "This usually happens with large or complex blueprints. Try uploading a smaller file or reduce the image resolution.",
        "retryable": True
    },
    ErrorCode.AI_SERVICE_ERROR: {
        "user_message": "Our AI analysis engine encountered an issue.",
        "suggestion": "This is usually temporary. Please try again in a few moments. If the problem persists, try with a different file.",
        "retryable": True
    },
    ErrorCode.VALIDATION_ERROR: {
        "user_message": "Some information you provided is invalid.",
        "suggestion": "Please check all required fields and make sure they are filled correctly.",
        "retryable": True
    },
    ErrorCode.MISSING_REQUIRED_FIELD: {
        "user_message": "Required information is missing.",
        "suggestion": "Please make sure you've filled in all required fields before submitting.",
        "retryable": True
    },
    ErrorCode.INTERNAL_ERROR: {
        "user_message": "Something went wrong on our end.",
        "suggestion": "This is a temporary issue. Please try again in a few moments. If the problem continues, please contact support.",
        "retryable": True
    },
    ErrorCode.NETWORK_ERROR: {
        "user_message": "A network error occurred while processing your request.",
        "suggestion": "Please check your internet connection and try again.",
        "retryable": True
    }
}


def create_error_response(
    error_code: ErrorCode,
    technical_details: Optional[str] = None,
    custom_message: Optional[str] = None,
    custom_suggestion: Optional[str] = None
) -> ErrorResponse:
    """Create a standardized error response"""
    error_info = ERROR_MESSAGES.get(error_code, ERROR_MESSAGES[ErrorCode.INTERNAL_ERROR])
    
    return ErrorResponse(
        error_code=error_code,
        user_message=custom_message or error_info["user_message"],
        suggestion=custom_suggestion or error_info["suggestion"],
        technical_details=technical_details,
        retryable=error_info["retryable"]
    )
