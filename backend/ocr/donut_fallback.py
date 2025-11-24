"""
Phase 3 Donut Fallback

HuggingFace Donut model for low-confidence pages.
Lazy loading, fail-soft approach for offline-first deployment.
"""

from __future__ import annotations
from typing import Any, Dict
import logging
import os

LOGGER = logging.getLogger("owlin.ocr.donut")


class DonutRunner:
    """Lazy-loaded Donut model runner for document parsing."""
    
    _loaded = False
    
    def __init__(self) -> None:
        self.model = None
        self.processor = None
    
    def load(self) -> bool:
        """
        Load Donut model and processor.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        if self._loaded:
            return True
        
        try:
            from transformers import DonutProcessor, VisionEncoderDecoderModel  # type: ignore
            import torch  # type: ignore
            
            # Use a small community model for offline deployment
            model_id = "naver-clova-ix/donut-base-finetuned-docvqa"
            
            LOGGER.info("Loading Donut model: %s", model_id)
            self.processor = DonutProcessor.from_pretrained(model_id)
            self.model = VisionEncoderDecoderModel.from_pretrained(model_id)
            self.model.eval()
            
            self._loaded = True
            LOGGER.info("Donut model loaded successfully")
            return True
            
        except Exception as e:
            LOGGER.warning("Donut load failed (ok offline): %s", e)
            return False
    
    def parse_image(self, image_path: str) -> Dict[str, Any]:
        """
        Parse image using Donut model.
        
        Args:
            image_path: Path to the image file
        
        Returns:
            Dictionary with parsing results
        """
        if not self._loaded and not self.load():
            return {"status": "unavailable", "error": "Donut model not loaded"}
        
        try:
            from PIL import Image  # type: ignore
            import torch  # type: ignore
            
            # Load and preprocess image
            image = Image.open(image_path).convert("RGB")
            inputs = self.processor(images=image, return_tensors="pt")
            
            # Run inference on CPU for offline deployment
            device = "cpu"
            self.model.to(device)
            
            with torch.no_grad():
                output = self.model.generate(
                    **{k: v.to(device) for k, v in inputs.items()},
                    max_length=512,
                    num_beams=1,
                    early_stopping=True
                )
            
            # Decode output
            text = self.processor.batch_decode(output, skip_special_tokens=True)[0]
            
            return {
                "status": "ok",
                "text": text,
                "model": "donut-base-finetuned-docvqa"
            }
            
        except Exception as e:
            LOGGER.warning("Donut parse failed: %s", e)
            return {"status": "error", "error": str(e)}
    
    def is_available(self) -> bool:
        """
        Check if Donut model is available.
        
        Returns:
            True if model is loaded and ready
        """
        return self._loaded and self.model is not None and self.processor is not None


# Global instance for lazy loading
_donut_runner = None


def get_donut_runner() -> DonutRunner:
    """
    Get global Donut runner instance.
    
    Returns:
        DonutRunner instance
    """
    global _donut_runner
    if _donut_runner is None:
        _donut_runner = DonutRunner()
    return _donut_runner


def parse_with_donut(image_path: str) -> Dict[str, Any]:
    """
    Parse image using Donut model (convenience function).
    
    Args:
        image_path: Path to the image file
    
    Returns:
        Dictionary with parsing results
    """
    runner = get_donut_runner()
    return runner.parse_image(image_path)
