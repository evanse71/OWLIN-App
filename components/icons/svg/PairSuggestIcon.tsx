import React from 'react';

interface PairSuggestIconProps {
  className?: string;
  size?: number;
}

export const PairSuggestIcon: React.FC<PairSuggestIconProps> = ({ 
  className = '', 
  size = 24 
}) => {
  return (
    <svg 
      width={size} 
      height={size} 
      viewBox="0 0 24 24" 
      fill="none" 
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <path d="M12 2L13.09 8.26L20 9L13.09 9.74L12 16L10.91 9.74L4 9L10.91 8.26L12 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M19 15L20.09 21.26L27 22L20.09 22.74L19 29L17.91 22.74L11 22L17.91 21.26L19 15Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M5 15L6.09 21.26L13 22L6.09 22.74L5 29L3.91 22.74L-3 22L3.91 21.26L5 15Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
};

export default PairSuggestIcon; 