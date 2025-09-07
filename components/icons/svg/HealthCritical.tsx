import React from 'react';

interface HealthCriticalIconProps {
  className?: string;
  size?: number;
}

export const HealthCriticalIcon: React.FC<HealthCriticalIconProps> = ({ 
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
      <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
      <circle cx="12" cy="12" r="3"/>
      <path d="M12 9v6"/>
      <path d="M9 12h6"/>
      <path d="M12 2v20"/>
      <path d="M2 12h20"/>
    </svg>
  );
};

export default HealthCriticalIcon; 