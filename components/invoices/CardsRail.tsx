import React from 'react';

interface CardsRailProps {
  children: React.ReactNode;
}

export default function CardsRail({ children }: CardsRailProps) {
  return (
    <section className="w-full">
      <div className="max-w-[960px] ml-auto space-y-4 mt-5">
        {children}
      </div>
    </section>
  );
}; 