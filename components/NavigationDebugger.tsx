import React, { useState, useEffect } from 'react';

const NavigationDebugger: React.FC = () => {
  const [isVisible, setIsVisible] = useState(false);
  const [debugInfo, setDebugInfo] = useState<any>({});

  useEffect(() => {
    const updateDebugInfo = () => {
      const nav = document.querySelector('nav');
      const navLinks = document.querySelectorAll('nav a');
      const fixedElements = document.querySelectorAll('.fixed');
      const absoluteElements = document.querySelectorAll('.absolute');
      
      setDebugInfo({
        navExists: !!nav,
        navZIndex: nav?.style.zIndex || getComputedStyle(nav!).zIndex,
        navPointerEvents: getComputedStyle(nav!).pointerEvents,
        navLinksCount: navLinks.length,
        navLinksClickable: Array.from(navLinks).map(link => ({
          href: link.getAttribute('href'),
          zIndex: getComputedStyle(link).zIndex,
          pointerEvents: getComputedStyle(link).pointerEvents,
          display: getComputedStyle(link).display,
          visibility: getComputedStyle(link).visibility,
        })),
        fixedElementsCount: fixedElements.length,
        absoluteElementsCount: absoluteElements.length,
        highZIndexElements: Array.from(document.querySelectorAll('*'))
          .filter(el => {
            const zIndex = parseInt(getComputedStyle(el).zIndex);
            return zIndex > 1000;
          })
          .map(el => ({
            tag: el.tagName,
            className: el.className,
            zIndex: getComputedStyle(el).zIndex,
            position: getComputedStyle(el).position,
          })),
      });
    };

    updateDebugInfo();
    const interval = setInterval(updateDebugInfo, 1000);
    
    return () => clearInterval(interval);
  }, []);

  if (!isVisible) {
    return (
      <button
        onClick={() => setIsVisible(true)}
        className="fixed bottom-4 left-4 bg-red-500 text-white px-3 py-2 rounded-lg z-[10001]"
      >
        Debug Nav
      </button>
    );
  }

  return (
    <div className="fixed bottom-4 left-4 bg-white border border-gray-300 rounded-lg p-4 max-w-md z-[10001] shadow-lg">
      <div className="flex justify-between items-center mb-3">
        <h3 className="font-semibold text-gray-900">Navigation Debugger</h3>
        <button
          onClick={() => setIsVisible(false)}
          className="text-gray-500 hover:text-gray-700"
        >
          ✕
        </button>
      </div>
      
      <div className="space-y-2 text-sm">
        <div>
          <strong>Nav Element:</strong>
          <div className="ml-2">
            <div>Exists: {debugInfo.navExists ? '✅' : '❌'}</div>
            <div>Z-Index: {debugInfo.navZIndex}</div>
            <div>Pointer Events: {debugInfo.navPointerEvents}</div>
          </div>
        </div>
        
        <div>
          <strong>Nav Links ({debugInfo.navLinksCount}):</strong>
          {debugInfo.navLinksClickable?.map((link: any, i: number) => (
            <div key={i} className="ml-2 text-xs">
              <div>{link.href} - Z: {link.zIndex}, PE: {link.pointerEvents}</div>
            </div>
          ))}
        </div>
        
        <div>
          <strong>High Z-Index Elements:</strong>
          {debugInfo.highZIndexElements?.map((el: any, i: number) => (
            <div key={i} className="ml-2 text-xs">
              <div>{el.tag}.{el.className} - Z: {el.zIndex}, Pos: {el.position}</div>
            </div>
          ))}
        </div>
        
        <div>
          <strong>Fixed Elements:</strong> {debugInfo.fixedElementsCount}
        </div>
        
        <div>
          <strong>Absolute Elements:</strong> {debugInfo.absoluteElementsCount}
        </div>
      </div>
    </div>
  );
};

export default NavigationDebugger; 