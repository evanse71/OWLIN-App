import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { Settings, User, Bell, Shield, Palette, Database, Download, FileText, Key, Clock } from 'lucide-react'

export default function SettingsPage() {
  const [mounted, setMounted] = useState(false)
  const [settings, setSettings] = useState({
    notifications: {
      email: true,
      push: false,
      sms: false
    },
    appearance: {
      theme: 'light',
      compactMode: false
    },
    general: {
      language: 'en',
      timezone: 'UTC'
    }
  })
  
  const [systemInfo, setSystemInfo] = useState({
    role: 'GM',
    version: '1.0.0',
    dbPath: 'data/owlin.db',
    lastBackup: null as string | null
  })

  useEffect(() => {
    setMounted(true)
  }, [])

  const handleSettingChange = (category: string, key: string, value: any) => {
    setSettings(prev => ({
      ...prev,
      [category]: {
        ...prev[category as keyof typeof prev],
        [key]: value
      }
    }))
  }
  
  const handleBackup = async () => {
    // TODO: Implement backup functionality
    console.log('Creating backup...')
  }
  
  const handleExportAudit = async () => {
    // TODO: Implement audit log export
    console.log('Exporting audit log...')
  }
  
  const handleLicenseManager = async () => {
    // TODO: Implement license manager
    console.log('Opening license manager...')
  }

  if (!mounted) {
    return <div className="p-6">Loading...</div>
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
          <p className="text-muted-foreground">
            Manage your application preferences and system information
          </p>
        </div>
      </div>

      {/* System Information */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            System Information
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Role:</span>
              <Badge variant="outline">{systemInfo.role}</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">App Version:</span>
              <Badge variant="outline">{systemInfo.version}</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Database Path:</span>
              <span className="text-sm text-gray-600 font-mono">{systemInfo.dbPath}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Last Backup:</span>
              <span className="text-sm text-gray-600">
                {systemInfo.lastBackup ? (
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {systemInfo.lastBackup}
                  </span>
                ) : (
                  'Never'
                )}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        {/* General SettingsIcon */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              General
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="language">Language</Label>
              <select
                id="language"
                value={settings.general.language}
                onChange={(e) => handleSettingChange('general', 'language', e.target.value)}
                className="w-full p-2 border rounded-md"
                aria-label="Select language"
              >
                <option value="en">English</option>
                <option value="es">Spanish</option>
                <option value="fr">French</option>
                <option value="de">German</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="timezone">Timezone</Label>
              <select
                id="timezone"
                value={settings.general.timezone}
                onChange={(e) => handleSettingChange('general', 'timezone', e.target.value)}
                className="w-full p-2 border rounded-md"
                aria-label="Select timezone"
              >
                <option value="UTC">UTC</option>
                <option value="America/New_York">Eastern Time</option>
                <option value="America/Chicago">Central Time</option>
                <option value="America/Denver">Mountain Time</option>
                <option value="America/Los_Angeles">Pacific Time</option>
              </select>
            </div>
          </CardContent>
        </Card>

        {/* Notifications */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Notifications
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="email-notifications">Email Notifications</Label>
              <Switch
                id="email-notifications"
                checked={settings.notifications.email}
                onCheckedChange={(checked) => handleSettingChange('notifications', 'email', checked)}
              />
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="push-notifications">Push Notifications</Label>
              <Switch
                id="push-notifications"
                checked={settings.notifications.push}
                onCheckedChange={(checked) => handleSettingChange('notifications', 'push', checked)}
              />
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="sms-notifications">SMS Notifications</Label>
              <Switch
                id="sms-notifications"
                checked={settings.notifications.sms}
                onCheckedChange={(checked) => handleSettingChange('notifications', 'sms', checked)}
              />
            </div>
          </CardContent>
        </Card>

        {/* Appearance */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Palette className="h-5 w-5" />
              Appearance
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="theme">Theme</Label>
              <select
                id="theme"
                value={settings.appearance.theme}
                onChange={(e) => handleSettingChange('appearance', 'theme', e.target.value)}
                className="w-full p-2 border rounded-md"
                aria-label="Select theme"
              >
                <option value="light">Light</option>
                <option value="dark">Dark</option>
                <option value="system">System</option>
              </select>
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="compact-mode">Compact Mode</Label>
              <Switch
                id="compact-mode"
                checked={settings.appearance.compactMode}
                onCheckedChange={(checked) => handleSettingChange('appearance', 'compactMode', checked)}
              />
            </div>
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Quick Actions
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button 
              variant="outline" 
              className="w-full flex items-center gap-2"
              onClick={handleBackup}
            >
              <Download className="h-4 w-4" />
              Create Backup (ZIP)
            </Button>
            <Button 
              variant="outline" 
              className="w-full flex items-center gap-2"
              onClick={handleExportAudit}
            >
              <FileText className="h-4 w-4" />
              Export Audit Log
            </Button>
            <Button 
              variant="outline" 
              className="w-full flex items-center gap-2"
              onClick={handleLicenseManager}
            >
              <Key className="h-4 w-4" />
              Open License Manager
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            Data Management
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium">Export Data</h4>
              <p className="text-sm text-muted-foreground">
                Download your data in various formats
              </p>
            </div>
            <Button variant="outline">Export</Button>
          </div>
          <Separator />
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium">Import Data</h4>
              <p className="text-sm text-muted-foreground">
                Upload data from external sources
              </p>
            </div>
            <Button variant="outline">Import</Button>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button>Save Changes</Button>
      </div>
    </div>
  )
}
