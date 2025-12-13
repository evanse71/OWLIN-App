import React from 'react';

interface PairConfirmIconProps {
  className?: string;
  size?: number;
}

export const PairConfirmIcon: React.FC<PairConfirmIconProps> = ({ 
  className = '', 
  size = 24 
}) => {
  return (
    <svg 
      xmlns="http://www.w3.org/2000/svg" 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="2" 
      strokeLinecap="round" 
      strokeLinejoin="round"
      className={className}
      width={size}
      height={size}
    >
      <path d="M20 6L9 17l-5-5"/>
      <path d="M21 12c-1 0-2-1-2-2s1-2 2-2 2 1 2 2-1 2-2 2z"/>
      <path d="M3 12c1 0 2-1 2-2s-1-2-2-2-2 1-2 2 1 2 2 2z"/>
      <path d="M12 3c0 1-1 2-2 2s-2-1-2-2 1-2 2-2 2 1 2 2z"/>
      <path d="M12 21c0-1 1-2 2-2s2 1 2 2-1 2-2 2-2-1-2-2z"/>
    </svg>
  );
};

export default PairConfirmIcon; 