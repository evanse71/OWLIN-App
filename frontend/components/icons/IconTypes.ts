export type IconProps = {
  size?: number;              // px; default 20
  stroke?: string;            // stroke color; default '#1C2A39'
  strokeWidth?: number;       // default 1.5
  className?: string;         // optional tailwind classes
  ariaLabel?: string;         // accessible label, falls back to component name
}; 