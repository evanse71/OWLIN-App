"""
Chat Router

FastAPI endpoints for conversational chat assistant with code context.
"""

import logging
import json
import asyncio
import uuid
import time
import queue as thread_queue
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
# Lazy import ChatService to avoid blocking router registration if there are import errors
try:
    from backend.services.chat_service import ChatService
except ImportError as e:
    # Log but don't fail - ChatService will be imported when needed
    import logging
    logging.getLogger("owlin.routes.chat").warning(f"ChatService import deferred: {e}")
    ChatService = None  # Will be imported in _get_chat_service if needed
from backend.services.chat_metrics import get_metrics
from backend.services.exploration_history import (
    get_exploration_sessions,
    get_exploration_session,
    delete_exploration_session,
    get_exploration_stats
)
from backend.config import env_str

logger = logging.getLogger("owlin.routes.chat")
router = APIRouter(prefix="/api/chat", tags=["chat"])

# Initialize chat service (lazy loading)
_chat_service = None  # Type will be ChatService when available


def _get_chat_service():
    """Get or create ChatService instance."""
    global _chat_service
    # Lazy import ChatService if it wasn't imported at module level
    if ChatService is None:
        try:
            from backend.services.chat_service import ChatService as _ChatService
            globals()['ChatService'] = _ChatService
        except ImportError as e:
            logger.error(f"[CHAT_SERVICE] Failed to import ChatService: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    if _chat_service is None:
        try:
            ollama_url = env_str("OLLAMA_URL", "http://localhost:11434")
            # Support comma-separated model list
            models_str = env_str("OLLAMA_MODELS", "")
            models = [m.strip() for m in models_str.split(",") if m.strip()] if models_str else None
            _chat_service = ChatService(ollama_url=ollama_url, models=models)
            logger.info(f"[CHAT_SERVICE] Initialized successfully with URL: {ollama_url}")
        except Exception as e:
            logger.error(f"[CHAT_SERVICE] Failed to initialize: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    return _chat_service


class ChatMessage(BaseModel):
    """Single chat message."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request for chat endpoint."""
    message: str = Field(..., description="User's message")
    conversation_history: Optional[List[ChatMessage]] = Field(
        default=None,
        description="Previous conversation messages for context"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context (current page, error logs, etc.)"
    )
    context_size: Optional[int] = Field(
        default=128000,
        description="Context window size in tokens (10k, 16k, 32k, 64k, 100k, 128k) - default 128k for local processing"
    )
    use_search_mode: bool = Field(
        default=False,
        description="Use Search mode: comprehensive information gathering and discovery"
    )
    use_agent_mode: bool = Field(
        default=False,
        description="Use Agent mode: autonomous problem-solving with task execution"
    )
    force_agent: bool = Field(
        default=False,
        description="Force agent mode on (bypasses heuristics, always uses agent mode)"
    )


class CodeReference(BaseModel):
    """Reference to a code file."""
    file: str = Field(..., description="File path")
    lines: Optional[List[int]] = Field(None, description="Line numbers")
    snippet: str = Field(..., description="Code snippet")


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    response: str = Field(..., description="Assistant's response")
    code_references: List[CodeReference] = Field(
        default_factory=list,
        description="Code file references if any"
    )
    model_used: str = Field(..., description="Model used for response")
    ollama_available: bool = Field(..., description="Whether Ollama was available")
    error: Optional[str] = Field(None, description="Error code if request failed")
    requires_ollama: bool = Field(False, description="Whether Ollama is required for this request")
    retryable: bool = Field(False, description="Whether the request can be retried")
    exploration_mode: bool = Field(False, description="Whether agent exploration was used")
    exploration_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Exploration details (files searched, findings count, etc.)"
    )


# Route handler function - registered explicitly in main.py to fix 405 error
# The route decorator is removed because FastAPI doesn't handle @router.post("") correctly
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat with the code assistant.
    
    The assistant can:
    - Answer questions about your code
    - Read and explain code files
    - Help debug errors
    - Search for code patterns
    
    Uses Ollama (if available) or fallback responses.
    """
    # Generate request ID for tracking
    request_id = str(uuid.uuid4())[:8]
    
    try:
        logger.info(f"[{request_id}] Chat request received: {request.message[:100]}...")
        
        chat_service = _get_chat_service()
        
        # Convert conversation history format if provided
        history = None
        if request.conversation_history:
            history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ]
        
        # Check Ollama availability before processing (re-check in case it started)
        try:
            chat_service.ollama_available = chat_service._check_ollama_available()
        except Exception as e:
            logger.warning(f"Ollama check failed: {e}")
            chat_service.ollama_available = False
        
        if not chat_service.ollama_available:
            # Run quick diagnostic
            diagnostic_msg = f"Attempted connection to {chat_service.ollama_url}"
            logger.warning(f"Ollama is not available - {diagnostic_msg}")
            
            return ChatResponse(
                response=f"Ollama is not available at {chat_service.ollama_url}. Please ensure:\n1. Ollama is installed\n2. Ollama is running (check with 'ollama serve')\n3. Ollama is accessible at port 11434\n\nClick Retry once Ollama is running.",
                code_references=[],
                model_used="none",
                ollama_available=False,
                error="OLLAMA_UNAVAILABLE",
                requires_ollama=True,
                retryable=True
            )
        
        # Process chat (request_id already generated above)
        result = chat_service.chat(
            message=request.message,
            conversation_history=history,
            context=request.context,
            context_size=request.context_size,
            use_search_mode=request.use_search_mode,
            use_agent_mode=request.use_agent_mode,
            force_agent=request.force_agent,
            request_id=request_id
        )
        
        # Convert code references
        code_refs = [
            CodeReference(
                file=ref["file"],
                lines=ref.get("lines"),
                snippet=ref.get("snippet", "")
            )
            for ref in result.get("code_references", [])
        ]
        
        logger.info(f"Chat response generated (model: {result.get('model_used', 'unknown')})")
        
        return ChatResponse(
            response=result["response"],
            code_references=code_refs,
            model_used=result.get("model_used", "fallback"),
            ollama_available=result.get("ollama_available", False),
            error=result.get("error"),
            requires_ollama=result.get("requires_ollama", False),
            retryable=result.get("retryable", False),
            exploration_mode=result.get("exploration_mode", False),
            exploration_metadata=result.get("exploration_metadata")
        )
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        
        # Classify error type
        error_type = "unknown"
        error_message = str(e)
        status_code = 500
        
        error_str_lower = str(e).lower()
        if "timeout" in error_str_lower:
            error_type = "timeout"
            error_message = "Request timed out. The operation took too long to complete."
        elif "ollama" in error_str_lower or "connection" in error_str_lower:
            error_type = "ollama_unavailable"
            error_message = "Ollama service is not available. Please ensure Ollama is running."
            status_code = 503
        elif "validation" in error_str_lower or "invalid" in error_str_lower:
            error_type = "validation_error"
            error_message = f"Invalid request: {str(e)}"
            status_code = 400
        else:
            error_type = "server_error"
            error_message = f"An error occurred: {str(e)}"
        
        logger.error(f"[{request_id}] Chat endpoint error [{error_type}]: {e}\n{error_trace}")
        raise HTTPException(
            status_code=status_code,
            detail={
                "error": error_type,
                "message": error_message,
                "detail": str(e),
                "request_id": request_id
            }
        )


@router.post("/stream")
async def chat_stream(request: ChatRequest, fastapi_request: Request):
    """
    Chat with streaming progress updates via Server-Sent Events (SSE).
    
    Returns SSE stream with:
    - progress: Exploration progress updates
    - response: Final response
    - error: Any errors
    """
    # Generate request ID for tracking
    stream_request_id = str(uuid.uuid4())[:8]
    
    async def event_generator():
        """Generate SSE events for exploration progress."""
        try:
            logger.info(f"[{stream_request_id}] Stream request received: {request.message[:100]}...")
            chat_service = _get_chat_service()
            
            # Convert conversation history format if provided
            history = None
            if request.conversation_history:
                history = [
                    {"role": msg.role, "content": msg.content}
                    for msg in request.conversation_history
                ]
            
            # Check Ollama availability
            try:
                chat_service.ollama_available = chat_service._check_ollama_available()
            except Exception as e:
                logger.warning(f"Ollama check failed: {e}")
                chat_service.ollama_available = False
            
            if not chat_service.ollama_available:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Ollama not available'})}\n\n"
                return
            
            # Create progress callback queue (thread-safe)
            progress_queue = thread_queue.Queue()
            result_container = {"result": None, "error": None, "done": False}
            
            def progress_callback(message: str, current: int, total: int):
                """Progress callback that sends to queue (thread-safe)."""
                try:
                    # Check if message is a structured JSON event
                    if message.startswith('{') and message.endswith('}'):
                        try:
                            import json
                            event_data = json.loads(message)
                            # Forward structured events as-is
                            progress_queue.put_nowait(event_data)
                        except json.JSONDecodeError:
                            # Fallback to regular progress if JSON parse fails
                            progress_queue.put_nowait({
                                "type": "progress",
                                "message": message,
                                "current": current,
                                "total": total,
                                "percentage": int((current / total) * 100) if total > 0 else 0
                            })
                    else:
                        # Regular progress message
                        progress_queue.put_nowait({
                            "type": "progress",
                            "message": message,
                            "current": current,
                            "total": total,
                            "percentage": int((current / total) * 100) if total > 0 else 0
                        })
                except Exception as e:
                    logger.warning(f"Progress callback error: {e}")
            
            # Run exploration in background (sync function in executor)
            def run_exploration_sync():
                try:
                    result = chat_service.chat(
                        message=request.message,
                        conversation_history=history,
                        context=request.context,
                        context_size=request.context_size,
                        use_search_mode=request.use_search_mode,
                        use_agent_mode=request.use_agent_mode,
                        force_agent=request.force_agent,
                        progress_callback=progress_callback,
                        request_id=stream_request_id
                    )
                    result_container["result"] = result
                except Exception as e:
                    logger.error(f"Exploration error: {e}", exc_info=True)
                    result_container["error"] = str(e)
                    # Immediately signal error to queue
                    try:
                        progress_queue.put_nowait({"type": "error", "message": str(e)})
                    except Exception:
                        pass
                finally:
                    result_container["done"] = True
                    # Signal completion
                    try:
                        progress_queue.put_nowait({"type": "done"})
                    except Exception:
                        pass
            
            # Start exploration task in executor (since chat() is sync)
            loop = asyncio.get_event_loop()
            exploration_task = loop.run_in_executor(None, run_exploration_sync)
            
            # Stream progress updates with timeout
            stream_start_time = time.time()
            stream_timeout = 120  # 2 minutes max for stream
            
            while not result_container["done"] or not progress_queue.empty():
                # Check for client disconnection (request cancellation)
                if fastapi_request and hasattr(fastapi_request, 'is_disconnected') and fastapi_request.is_disconnected():
                    logger.info(f"[{stream_request_id}] Client disconnected, cancelling stream")
                    break
                
                # Check overall stream timeout
                if time.time() - stream_start_time > stream_timeout:
                    logger.warning(f"[{stream_request_id}] SSE stream timeout exceeded after {stream_timeout}s")
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Stream timeout exceeded'})}\n\n"
                    break
                
                try:
                    # Use get_nowait for thread-safe queue
                    try:
                        progress_data = progress_queue.get_nowait()
                    except thread_queue.Empty:
                        if result_container["done"]:
                            break
                        await asyncio.sleep(0.1)  # Small delay before retry
                        continue
                    
                    if progress_data.get("type") == "done":
                        break
                    yield f"data: {json.dumps(progress_data)}\n\n"
                except Exception as e:
                    logger.error(f"[{stream_request_id}] SSE streaming error: {e}")
                    break
            
            # Wait for exploration to complete
            try:
                await exploration_task
            except Exception as e:
                logger.error(f"[{stream_request_id}] Exploration task error: {e}", exc_info=True)
                result_container["error"] = str(e)
                result_container["done"] = True
            
            # Ensure we always send a final event
            if not result_container["done"]:
                # Wait a bit more for completion
                await asyncio.sleep(0.1)
            
            # Send final result - ALWAYS send something
            if result_container["error"]:
                yield f"data: {json.dumps({'type': 'error', 'message': result_container['error']})}\n\n"
            elif result_container["result"]:
                result = result_container["result"]
                # Convert code references
                code_refs = [
                    {
                        "file": ref["file"],
                        "lines": ref.get("lines"),
                        "snippet": ref.get("snippet", "")
                    }
                    for ref in result.get("code_references", [])
                ]
                
                final_response = {
                    "type": "response",
                    "response": result["response"],
                    "code_references": code_refs,
                    "model_used": result.get("model_used", "fallback"),
                    "ollama_available": result.get("ollama_available", False),
                    "error": result.get("error"),
                    "requires_ollama": result.get("requires_ollama", False),
                    "retryable": result.get("retryable", False),
                    "exploration_mode": result.get("exploration_mode", False),
                    "exploration_metadata": result.get("exploration_metadata")
                }
                yield f"data: {json.dumps(final_response)}\n\n"
            else:
                # No result and no error - this shouldn't happen, but handle it
                logger.error(f"[{stream_request_id}] Stream completed but no result or error in container")
                yield f"data: {json.dumps({'type': 'error', 'message': 'Request completed but no response received. Please try again.'})}\n\n"
            
        except Exception as e:
            logger.error(f"[{stream_request_id}] SSE stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get("/history")
async def get_history(
    limit: int = 20,
    offset: int = 0,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get exploration history.
    
    Args:
        limit: Maximum number of sessions to return
        offset: Offset for pagination
        search: Optional search query to filter by user message
        
    Returns:
        Dictionary with sessions and total count
    """
    try:
        sessions = get_exploration_sessions(limit=limit, offset=offset, search_query=search)
        stats = get_exploration_stats()
        
        return {
            "sessions": sessions,
            "total": stats.get("total_sessions", 0),
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error retrieving exploration history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {str(e)}")


@router.get("/history/{session_id}")
async def get_history_session(session_id: str) -> Dict[str, Any]:
    """
    Get a specific exploration session with all details.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Session dictionary with findings
    """
    try:
        session = get_exploration_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving exploration session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve session: {str(e)}")


@router.delete("/history/{session_id}")
async def delete_history_session(session_id: str) -> Dict[str, Any]:
    """
    Delete an exploration session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Success status
    """
    try:
        success = delete_exploration_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"success": True, "message": "Session deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting exploration session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")


@router.get("/history/stats")
async def get_history_stats() -> Dict[str, Any]:
    """
    Get exploration history statistics.
    
    Returns:
        Dictionary with statistics
    """
    try:
        return get_exploration_stats()
    except Exception as e:
        logger.error(f"Error retrieving exploration stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve stats: {str(e)}")


@router.get("/status")
async def chat_status() -> Dict[str, Any]:
    """Get chat service status."""
    try:
        chat_service = _get_chat_service()
        from backend.config import AGENT_FORCE_ON
        
        return {
            "status": "ok",
            "ollama_available": chat_service.ollama_available,
            "ollama_url": chat_service.ollama_url,
            "primary_model": getattr(chat_service, 'model', 'unknown'),
            "available_models": getattr(chat_service, 'available_models', []),
            "all_configured_models": getattr(chat_service, 'models', []),
            "code_reader_available": True,
            "agent_force_on": AGENT_FORCE_ON
        }
        
    except Exception as e:
        logger.error(f"Chat status check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "ollama_available": False
        }


@router.get("/diagnose")
async def diagnose_ollama() -> Dict[str, Any]:
    """Diagnostic endpoint to check Ollama connection details."""
    import requests
    
    chat_service = _get_chat_service()
    
    diagnostics = {
        "ollama_url": chat_service.ollama_url,
        "model": chat_service.model,
        "currently_available": chat_service.ollama_available,
        "checks": []
    }
    
    # Try each endpoint with detailed error capture
    endpoints = ["/api/tags", "/api/version", "/"]
    for endpoint in endpoints:
        url = f"{chat_service.ollama_url}{endpoint}"
        check_result = {
            "endpoint": endpoint,
            "url": url,
            "status": "unknown",
            "error": None,
            "status_code": None
        }
        
        try:
            response = requests.get(url, timeout=5)
            check_result["status_code"] = response.status_code
            check_result["status"] = "success" if response.status_code == 200 else "failed"
        except requests.exceptions.ConnectionError as e:
            check_result["status"] = "connection_refused"
            check_result["error"] = str(e)
        except requests.exceptions.Timeout as e:
            check_result["status"] = "timeout"
            check_result["error"] = str(e)
        except Exception as e:
            check_result["status"] = "error"
            check_result["error"] = str(e)
        
        diagnostics["checks"].append(check_result)
    
    return diagnostics


@router.get("/config")
async def get_config() -> Dict[str, Any]:
    """Get chat service configuration."""
    try:
        chat_service = _get_chat_service()
        model_stats = chat_service.model_registry.get_model_stats()
        
        return {
            "status": "ok",
            "models": {
                "primary": chat_service.model,
                "available": chat_service.available_models,
                "configured": chat_service.models,
                "registry_stats": model_stats
            },
            "ollama": {
                "url": chat_service.ollama_url,
                "available": chat_service.ollama_available
            },
            "features": {
                "code_reader": True,
                "auto_file_detection": True,
                "generic_response_rejection": True,
                "forced_code_analysis": True,
                "model_fallback_chain": True,
                "context_budgeting": True
            }
        }
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        return {"status": "error", "error": str(e)}


@router.get("/models")
async def list_models() -> Dict[str, Any]:
    """List all available models from Ollama."""
    try:
        chat_service = _get_chat_service()
        
        # Refresh model registry
        chat_service.model_registry.refresh()
        
        available_models = chat_service.model_registry.get_available_models()
        
        return {
            "status": "ok",
            "models": [
                {
                    "name": model.name,
                    "max_context": model.max_context,
                    "specialty": model.specialty,
                    "speed": model.speed,
                    "description": model.description,
                    "size_mb": round(model.size_bytes / (1024 * 1024), 1),
                    "available": model.available
                }
                for model in available_models
            ],
            "count": len(available_models),
            "registry_cache_age": chat_service.model_registry._cache_time.isoformat() if chat_service.model_registry._cache_time else None
        }
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        return {"status": "error", "error": str(e)}


@router.get("/metrics")
async def get_chat_metrics() -> Dict[str, Any]:
    """Get chat service quality metrics."""
    try:
        metrics = get_metrics()
        return {
            "status": "ok",
            "metrics": metrics.get_session_stats()
        }
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        return {"status": "error", "error": str(e)}


@router.get("/quality")
async def get_quality_report() -> Dict[str, Any]:
    """Get quality report with pass/fail indicators."""
    try:
        metrics = get_metrics()
        return {
            "status": "ok",
            **metrics.get_quality_report()
        }
    except Exception as e:
        logger.error(f"Failed to get quality report: {e}")
        return {"status": "error", "error": str(e)}



