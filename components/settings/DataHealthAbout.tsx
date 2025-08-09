import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

const DataHealthAbout: React.FC = () => {
  const models = [
    {
      name: 'Qwen2.5-VL',
      license: 'Apache-2.0',
      description: 'Multimodal invoice parsing (images → JSON)',
      source: 'Alibaba Cloud'
    },
    {
      name: 'Llama 3.1 (Optional)',
      license: 'Llama Community License',
      description: 'Text-only invoice parsing (when used with Surya)',
      source: 'Meta AI'
    },
    {
      name: 'Surya (Optional)',
      license: 'Apache-2.0',
      description: 'Layout analysis and table extraction',
      source: 'VikParuchuri/surya'
    }
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>About Models</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Document parsing powered by local models: Qwen2.5-VL (Apache-2.0). 
            Optional adapter: Llama (Community License).
          </p>
          
          <div className="space-y-3">
            {models.map((model) => (
              <div key={model.name} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium">{model.name}</h4>
                  <Badge variant="secondary">{model.license}</Badge>
                </div>
                <p className="text-sm text-muted-foreground mb-2">
                  {model.description}
                </p>
                <p className="text-xs text-muted-foreground">
                  Source: {model.source}
                </p>
              </div>
            ))}
          </div>
          
          <div className="pt-4 border-t">
            <h4 className="font-medium mb-2">License Files</h4>
            <div className="space-y-2">
              <a href="/THIRD_PARTY_LICENSES/Qwen2.5-VL-LICENSE.txt" target="_blank" rel="noopener noreferrer">
                <Button variant="outline" size="sm">
                  Qwen2.5-VL License (Apache-2.0)
                </Button>
              </a>
              <a href="/THIRD_PARTY_LICENSES/Llama-Community-License.txt" target="_blank" rel="noopener noreferrer">
                <Button variant="outline" size="sm">
                  Llama Community License
                </Button>
              </a>
              <a href="/THIRD_PARTY_LICENSES/Surya-LICENSE.txt" target="_blank" rel="noopener noreferrer">
                <Button variant="outline" size="sm">
                  Surya License (Apache-2.0)
                </Button>
              </a>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default DataHealthAbout; 