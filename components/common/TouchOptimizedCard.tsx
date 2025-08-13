import React, { useState, useRef, useCallback } from 'react';
import { cn } from '@/lib/utils';

interface TouchOptimizedCardProps {
  children: React.ReactNode;
  onSwipe?: (direction: 'left' | 'right' | 'up' | 'down') => void;
  onTap?: () => void;
  onLongPress?: () => void;
  className?: string;
  swipeThreshold?: number;
  longPressDelay?: number;
  disabled?: boolean;
}

const TouchOptimizedCard: React.FC<TouchOptimizedCardProps> = ({
  children,
  onSwipe,
  onTap,
  onLongPress,
  className,
  swipeThreshold = 50,
  longPressDelay = 500,
  disabled = false,
}) => {
  const [startX, setStartX] = useState(0);
  const [startY, setStartY] = useState(0);
  const [endX, setEndX] = useState(0);
  const [endY, setEndY] = useState(0);
  const [isPressed, setIsPressed] = useState(false);
  const [longPressTimer, setLongPressTimer] = useState<NodeJS.Timeout | null>(null);
  
  const touchRef = useRef<HTMLDivElement>(null);

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    if (disabled) return;
    
    const touch = e.touches[0];
    setStartX(touch.clientX);
    setStartY(touch.clientY);
    setEndX(touch.clientX);
    setEndY(touch.clientY);
    setIsPressed(true);

    // Start long press timer
    if (onLongPress) {
      const timer = setTimeout(() => {
        onLongPress();
      }, longPressDelay);
      setLongPressTimer(timer);
    }
  }, [disabled, onLongPress, longPressDelay]);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (disabled) return;
    
    const touch = e.touches[0];
    setEndX(touch.clientX);
    setEndY(touch.clientY);
    
    // Cancel long press if user moves finger
    if (longPressTimer) {
      clearTimeout(longPressTimer);
      setLongPressTimer(null);
    }
  }, [disabled, longPressTimer]);

  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    if (disabled) return;
    
    setIsPressed(false);
    
    // Cancel long press timer
    if (longPressTimer) {
      clearTimeout(longPressTimer);
      setLongPressTimer(null);
    }

    // Calculate swipe distance
    const deltaX = startX - endX;
    const deltaY = startY - endY;
    const absDeltaX = Math.abs(deltaX);
    const absDeltaY = Math.abs(deltaY);

    // Determine if it's a swipe or tap
    if (absDeltaX > swipeThreshold || absDeltaY > swipeThreshold) {
      // It's a swipe
      if (onSwipe) {
        if (absDeltaX > absDeltaY) {
          // Horizontal swipe
          onSwipe(deltaX > 0 ? 'left' : 'right');
        } else {
          // Vertical swipe
          onSwipe(deltaY > 0 ? 'up' : 'down');
        }
      }
    } else if (absDeltaX < 10 && absDeltaY < 10) {
      // It's a tap (minimal movement)
      if (onTap) {
        onTap();
      }
    }
  }, [disabled, startX, startY, endX, endY, swipeThreshold, onSwipe, onTap, longPressTimer]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (disabled) return;
    
    setStartX(e.clientX);
    setStartY(e.clientY);
    setEndX(e.clientX);
    setEndY(e.clientY);
    setIsPressed(true);

    // Start long press timer for mouse
    if (onLongPress) {
      const timer = setTimeout(() => {
        onLongPress();
      }, longPressDelay);
      setLongPressTimer(timer);
    }
  }, [disabled, onLongPress, longPressDelay]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (disabled || !isPressed) return;
    
    setEndX(e.clientX);
    setEndY(e.clientY);
    
    // Cancel long press if user moves mouse
    if (longPressTimer) {
      clearTimeout(longPressTimer);
      setLongPressTimer(null);
    }
  }, [disabled, isPressed, longPressTimer]);

  const handleMouseUp = useCallback((e: React.MouseEvent) => {
    if (disabled) return;
    
    setIsPressed(false);
    
    // Cancel long press timer
    if (longPressTimer) {
      clearTimeout(longPressTimer);
      setLongPressTimer(null);
    }

    // Calculate swipe distance for mouse
    const deltaX = startX - endX;
    const deltaY = startY - endY;
    const absDeltaX = Math.abs(deltaX);
    const absDeltaY = Math.abs(deltaY);

    // Determine if it's a swipe or click
    if (absDeltaX > swipeThreshold || absDeltaY > swipeThreshold) {
      // It's a swipe
      if (onSwipe) {
        if (absDeltaX > absDeltaY) {
          // Horizontal swipe
          onSwipe(deltaX > 0 ? 'left' : 'right');
        } else {
          // Vertical swipe
          onSwipe(deltaY > 0 ? 'up' : 'down');
        }
      }
    } else if (absDeltaX < 10 && absDeltaY < 10) {
      // It's a click (minimal movement)
      if (onTap) {
        onTap();
      }
    }
  }, [disabled, startX, startY, endX, endY, swipeThreshold, onSwipe, onTap, longPressTimer]);

  // Cleanup timer on unmount
  React.useEffect(() => {
    return () => {
      if (longPressTimer) {
        clearTimeout(longPressTimer);
      }
    };
  }, [longPressTimer]);

  return (
    <div
      ref={touchRef}
      className={cn(
        "touch-optimized transition-all duration-200",
        isPressed && "scale-95 opacity-90",
        disabled && "opacity-50 cursor-not-allowed",
        className
      )}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={() => {
        setIsPressed(false);
        if (longPressTimer) {
          clearTimeout(longPressTimer);
          setLongPressTimer(null);
        }
      }}
      style={{
        touchAction: 'manipulation',
        WebkitTapHighlightColor: 'transparent',
        userSelect: 'none',
      }}
    >
      {children}
    </div>
  );
};

export default TouchOptimizedCard; 