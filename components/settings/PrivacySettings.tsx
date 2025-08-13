import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';

interface PrivacySettingsProps {
  onSettingsChange?: (settings: PrivacySettingsData) => void;
}

interface PrivacySettingsData {
  useLocalAI: boolean;
}

const PrivacySettings: React.FC<PrivacySettingsProps> = ({ onSettingsChange }) => {
  const [settings, setSettings] = useState<PrivacySettingsData>({
    useLocalAI: true
  });

  useEffect(() => {
    // Load settings from localStorage or app_settings.json
    const savedSettings = localStorage.getItem('privacy_settings');
    if (savedSettings) {
      const parsed = JSON.parse(savedSettings);
      setSettings(parsed);
    }
  }, []);

  const handleSettingChange = (key: keyof PrivacySettingsData, value: boolean) => {
    const newSettings = { ...settings, [key]: value };
    setSettings(newSettings);
    
    // Save to localStorage
    localStorage.setItem('privacy_settings', JSON.stringify(newSettings));
    
    // Notify parent component
    if (onSettingsChange) {
      onSettingsChange(newSettings);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Privacy Settings</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label htmlFor="local-ai">Use Local AI for Parsing</Label>
            <p className="text-sm text-muted-foreground">
              Processing occurs locally; no data leaves this device. Disable if you prefer OCR-only.
            </p>
          </div>
          <Switch
            id="local-ai"
            checked={settings.useLocalAI}
            onCheckedChange={(checked) => handleSettingChange('useLocalAI', checked)}
          />
        </div>
      </CardContent>
    </Card>
  );
};

export default PrivacySettings; 