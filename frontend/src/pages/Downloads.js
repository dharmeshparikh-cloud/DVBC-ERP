import React, { useContext, useState } from 'react';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import { Download, FileText, FileCode, BookOpen, Shield, Loader2 } from 'lucide-react';

const ADMIN_ROLES = ['admin', 'manager'];

const Downloads = () => {
  const { user } = useContext(AuthContext);
  const [downloading, setDownloading] = useState(null);

  // Check if user has admin access
  if (!ADMIN_ROLES.includes(user?.role)) {
    return (
      <div className="flex flex-col items-center justify-center py-16" data-testid="downloads-unauthorized">
        <Shield className="w-16 h-16 text-zinc-300 mb-4" />
        <h2 className="text-xl font-semibold text-zinc-900 mb-2">Access Restricted</h2>
        <p className="text-zinc-500">You don't have permission to access this page.</p>
      </div>
    );
  }

  const downloadFile = async (endpoint, filename, type) => {
    setDownloading(type);
    try {
      const response = await fetch(`${API}${endpoint}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) {
        throw new Error('Download failed');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success(`${filename} downloaded successfully`);
    } catch (error) {
      console.error('Download error:', error);
      toast.error('Failed to download file. Please try again.');
    } finally {
      setDownloading(null);
    }
  };

  const downloadItems = [
    {
      id: 'api-docs',
      title: 'API Documentation',
      description: 'Complete API reference documentation in HTML format. Contains all endpoint details, request/response schemas, and authentication information.',
      icon: FileText,
      endpoint: '/api/downloads/api-documentation',
      filename: 'DV_Business_Consulting_API_Documentation.html',
      badge: 'HTML',
      badgeColor: 'bg-blue-100 text-blue-800',
    },
    {
      id: 'postman',
      title: 'Postman Collection',
      description: 'Pre-configured Postman collection with all API endpoints. Import directly into Postman for API testing and development.',
      icon: FileCode,
      endpoint: '/api/downloads/postman-collection',
      filename: 'DV_Business_Consulting_API.postman_collection.json',
      badge: 'JSON',
      badgeColor: 'bg-amber-100 text-amber-800',
    },
    {
      id: 'feature-index',
      title: 'Feature Index',
      description: 'Comprehensive feature index document covering all modules and functionalities available in the system.',
      icon: BookOpen,
      endpoint: '/api/downloads/feature-index',
      filename: 'Feature_Index_DVB_Consulting.docx',
      badge: 'DOCX',
      badgeColor: 'bg-emerald-100 text-emerald-800',
    },
  ];

  return (
    <div className="space-y-6" data-testid="downloads-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Developer Resources</h1>
          <p className="text-sm text-zinc-500 mt-1">Download API documentation and development tools</p>
        </div>
        <Badge className="bg-zinc-100 text-zinc-700 font-normal">Admin Only</Badge>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {downloadItems.map((item) => {
          const Icon = item.icon;
          const isDownloading = downloading === item.id;
          
          return (
            <Card key={item.id} className="border border-zinc-200 hover:border-zinc-300 transition-colors" data-testid={`download-card-${item.id}`}>
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="w-10 h-10 rounded-lg bg-zinc-100 flex items-center justify-center">
                    <Icon className="w-5 h-5 text-zinc-700" />
                  </div>
                  <Badge className={`${item.badgeColor} text-[10px] font-medium`}>{item.badge}</Badge>
                </div>
                <CardTitle className="text-base mt-3">{item.title}</CardTitle>
                <CardDescription className="text-xs leading-relaxed">
                  {item.description}
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-0">
                <Button
                  onClick={() => downloadFile(item.endpoint, item.filename, item.id)}
                  disabled={isDownloading}
                  className="w-full"
                  variant="outline"
                  size="sm"
                  data-testid={`download-btn-${item.id}`}
                >
                  {isDownloading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Downloading...
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4 mr-2" />
                      Download
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <Card className="border border-zinc-200 bg-zinc-50">
        <CardContent className="py-4">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-zinc-200 flex items-center justify-center flex-shrink-0">
              <Shield className="w-4 h-4 text-zinc-600" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-zinc-900">Security Notice</h3>
              <p className="text-xs text-zinc-500 mt-1">
                These resources contain sensitive API information and are restricted to administrators only. 
                Do not share these files outside your organization.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Downloads;
