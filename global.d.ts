declare module "*.svg" {
  import * as React from "react";
  const Component: React.FC<React.SVGProps<SVGSVGElement>>;
  export default Component;
}
declare module "*.png" { const url: string; export default url; }
declare module "*.jpg" { const url: string; export default url; } 