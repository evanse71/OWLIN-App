import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

// Import icon components
import PairSuggestIcon from '../components/icons/svg/PairSuggest';
import PairConfirmIcon from '../components/icons/svg/PairConfirm';
import PairRejectIcon from '../components/icons/svg/PairReject';
import HealthOkIcon from '../components/icons/svg/HealthOk';
import HealthDegradedIcon from '../components/icons/svg/HealthDegraded';
import HealthCriticalIcon from '../components/icons/svg/HealthCritical';

describe('SVG Icons', () => {
  it('should have all SVG files in public/icons', () => {
    const iconDir = path.join(process.cwd(), 'public', 'icons');
    const svgFiles = fs.readdirSync(iconDir).filter(file => file.endsWith('.svg'));
    
    const expectedIcons = [
      'pair-suggest.svg',
      'pair-confirm.svg',
      'pair-reject.svg',
      'health-ok.svg',
      'health-degraded.svg',
      'health-critical.svg'
    ];
    
    expectedIcons.forEach(icon => {
      expect(svgFiles).toContain(icon);
    });
  });

  it('should have manifest.json with all icons', () => {
    const manifestPath = path.join(process.cwd(), 'components', 'icons', 'manifest.json');
    const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
    
    const expectedIcons = [
      'pair-suggest',
      'pair-confirm',
      'pair-reject',
      'health-ok',
      'health-degraded',
      'health-critical'
    ];
    
    expectedIcons.forEach(iconName => {
      expect(manifest.svg).toHaveProperty(iconName);
      expect(manifest.svg[iconName]).toHaveProperty('file');
      expect(manifest.svg[iconName]).toHaveProperty('component');
      expect(manifest.svg[iconName]).toHaveProperty('description');
    });
  });

  it('should have React wrapper components for all icons', () => {
    const wrapperDir = path.join(process.cwd(), 'components', 'icons', 'svg');
    const wrapperFiles = fs.readdirSync(wrapperDir).filter(file => file.endsWith('.tsx'));
    
    const expectedWrappers = [
      'PairSuggest.tsx',
      'PairConfirm.tsx',
      'PairReject.tsx',
      'HealthOk.tsx',
      'HealthDegraded.tsx',
      'HealthCritical.tsx'
    ];
    
    expectedWrappers.forEach(wrapper => {
      expect(wrapperFiles).toContain(wrapper);
    });
  });

  it('should have correct viewBox in SVG files', () => {
    const iconDir = path.join(process.cwd(), 'public', 'icons');
    const svgFiles = fs.readdirSync(iconDir).filter(file => file.endsWith('.svg'));
    
    svgFiles.forEach(file => {
      const svgPath = path.join(iconDir, file);
      const svgContent = fs.readFileSync(svgPath, 'utf-8');
      
      expect(svgContent).toContain('viewBox="0 0 24 24"');
      expect(svgContent).toContain('stroke="currentColor"');
    });
  });

  it('should have correct props in React wrappers', () => {
    const wrapperDir = path.join(process.cwd(), 'components', 'icons', 'svg');
    const wrapperFiles = fs.readdirSync(wrapperDir).filter(file => file.endsWith('.tsx'));
    
    wrapperFiles.forEach(file => {
      const wrapperPath = path.join(wrapperDir, file);
      const wrapperContent = fs.readFileSync(wrapperPath, 'utf-8');
      
      expect(wrapperContent).toContain('viewBox="0 0 24 24"');
      expect(wrapperContent).toContain('stroke="currentColor"');
      expect(wrapperContent).toContain('className?: string');
      expect(wrapperContent).toContain('size?: number');
    });
  });

  it('should have icons registered in main index', () => {
    const indexPath = path.join(process.cwd(), 'components', 'icons', 'index.tsx');
    const indexContent = fs.readFileSync(indexPath, 'utf-8');
    
    const expectedIcons = [
      'pair-suggest',
      'pair-confirm',
      'pair-reject',
      'health-ok',
      'health-degraded',
      'health-critical'
    ];
    
    expectedIcons.forEach(iconName => {
      expect(indexContent).toContain(`'${iconName}':`);
    });
  });

  it('should not have lucide-react imports in SVG wrappers', () => {
    const wrapperDir = path.join(process.cwd(), 'components', 'icons', 'svg');
    const wrapperFiles = fs.readdirSync(wrapperDir).filter(file => file.endsWith('.tsx'));
    
    wrapperFiles.forEach(file => {
      const wrapperPath = path.join(wrapperDir, file);
      const wrapperContent = fs.readFileSync(wrapperPath, 'utf-8');
      
      expect(wrapperContent).not.toContain('lucide-react');
    });
  });
}); 