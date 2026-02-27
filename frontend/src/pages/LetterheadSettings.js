import React, { useState, useContext, useRef } from 'react';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { 
  Upload, Trash2, Save, Eye, Image, FileText, Settings,
  Check, AlertCircle, RefreshCw
} from 'lucide-react';
import { toast } from 'sonner';
import CompanyLetterhead, { HRSignatureBlock, LetterHeader } from '../components/CompanyLetterhead';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';

const LetterheadSettings = () => {
  const { user } = useContext(AuthContext);
  const queryClient = useQueryClient();
  const [saving, setSaving] = useState(false);
  const [localSettings, setLocalSettings] = useState(null);
  const [activeTab, setActiveTab] = useState('upload');
  
  const headerInputRef = useRef(null);
  const footerInputRef = useRef(null);

  const canEdit = user?.role === 'admin' || user?.role === 'hr_manager';

  // Query: Fetch settings
  const { data: fetchedSettings, isLoading: loading } = useQuery({
    queryKey: ['letterhead-settings'],
    queryFn: async () => {
      const res = await axios.get(`${API}/letters/letterhead-settings`);
      return res.data;
    },
    onSuccess: (data) => {
      if (!localSettings) {
        setLocalSettings(data);
      }
    }
  });

  // Use localSettings if available, otherwise use fetched settings
  const settings = localSettings || fetchedSettings || {
    header_image: null,
    footer_image: null,
    company_name: "D&V Business Consulting",
    company_address: "123, Business Park, Andheri East, Mumbai - 400069",
    company_phone: "+91 22 1234 5678",
    company_email: "contact@dvconsulting.co.in",
    company_cin: "U74999MH2020PTC123456"
  };

  const setSettings = (newSettings) => {
    if (typeof newSettings === 'function') {
      setLocalSettings(prev => newSettings(prev || settings));
    } else {
      setLocalSettings(newSettings);
    }
  };

  // Mutation: Upload image
  const uploadMutation = useMutation({
    mutationFn: async ({ type, file }) => {
      const formData = new FormData();
      formData.append('file', file);
      return axios.post(`${API}/letters/letterhead-settings/upload-${type}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    },
    onSuccess: (_, { type }) => {
      toast.success(`${type === 'header' ? 'Header' : 'Footer'} image uploaded successfully`);
      queryClient.invalidateQueries({ queryKey: ['letterhead-settings'] });
      setLocalSettings(null); // Reset to refetch
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to upload image');
    }
  });

  // Mutation: Delete image
  const deleteMutation = useMutation({
    mutationFn: async (type) => {
      return axios.delete(`${API}/letters/letterhead-settings/${type}`);
    },
    onSuccess: (_, type) => {
      toast.success(`${type === 'header' ? 'Header' : 'Footer'} image deleted`);
      queryClient.invalidateQueries({ queryKey: ['letterhead-settings'] });
      setLocalSettings(null);
    },
    onError: () => {
      toast.error('Error deleting image');
    }
  });

  // Mutation: Save settings
  const saveMutation = useMutation({
    mutationFn: async () => {
      return axios.put(`${API}/letters/letterhead-settings`, settings);
    },
    onSuccess: () => {
      toast.success('Settings saved successfully');
      queryClient.invalidateQueries({ queryKey: ['letterhead-settings'] });
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to save settings');
    },
    onSettled: () => {
      setSaving(false);
    }
  });

  const handleUpload = (type, file) => {
    if (!file) return;
    
    // Validate file type
    if (!file.type.startsWith('image/')) {
      toast.error('Please upload an image file (PNG, JPG, etc.)');
      return;
    }
    
    // Validate file size (5MB max)
    if (file.size > 5 * 1024 * 1024) {
      toast.error('File size must be less than 5MB');
      return;
    }
    
    uploadMutation.mutate({ type, file });
  };

  const handleDelete = (type) => {
    deleteMutation.mutate(type);
  };

  const handleSaveSettings = () => {
    setSaving(true);
    saveMutation.mutate();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="letterhead-settings-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Image className="w-6 h-6 text-orange-500" />
            Letterhead Settings
          </h1>
          <p className="text-muted-foreground mt-1">
            Upload custom header and footer images for company letters
          </p>
        </div>
        {canEdit && (
          <Button onClick={handleSaveSettings} disabled={saving}>
            {saving ? (
              <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Save className="w-4 h-4 mr-2" />
            )}
            Save Settings
          </Button>
        )}
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="upload" className="flex items-center gap-2">
            <Upload className="w-4 h-4" />
            Upload Images
          </TabsTrigger>
          <TabsTrigger value="preview" className="flex items-center gap-2">
            <Eye className="w-4 h-4" />
            Preview
          </TabsTrigger>
          <TabsTrigger value="company" className="flex items-center gap-2">
            <Settings className="w-4 h-4" />
            Company Info
          </TabsTrigger>
        </TabsList>

        {/* Upload Tab */}
        <TabsContent value="upload" className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Header Upload */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Header Image</CardTitle>
                <CardDescription>
                  Upload your company letterhead header (recommended: 800x150px)
                </CardDescription>
              </CardHeader>
              <CardContent>
                <input
                  type="file"
                  ref={headerInputRef}
                  className="hidden"
                  accept="image/*"
                  onChange={(e) => handleUpload('header', e.target.files?.[0])}
                />
                
                {settings.header_image ? (
                  <div className="space-y-4">
                    <div className="border rounded-lg overflow-hidden bg-gray-50">
                      <img 
                        src={settings.header_image} 
                        alt="Header Preview" 
                        className="w-full h-auto"
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-green-600 flex items-center gap-1">
                        <Check className="w-4 h-4" />
                        Header uploaded
                      </span>
                      <div className="flex gap-2">
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => headerInputRef.current?.click()}
                        >
                          <RefreshCw className="w-4 h-4 mr-1" />
                          Replace
                        </Button>
                        <Button 
                          variant="destructive" 
                          size="sm"
                          onClick={() => handleDelete('header')}
                        >
                          <Trash2 className="w-4 h-4 mr-1" />
                          Remove
                        </Button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div 
                    className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-orange-400 transition-colors"
                    onClick={() => headerInputRef.current?.click()}
                  >
                    <Upload className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                    <p className="text-sm text-gray-600">Click to upload header image</p>
                    <p className="text-xs text-gray-400 mt-1">PNG, JPG up to 5MB</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Footer Upload */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Footer Image</CardTitle>
                <CardDescription>
                  Upload your company letterhead footer (recommended: 800x100px)
                </CardDescription>
              </CardHeader>
              <CardContent>
                <input
                  type="file"
                  ref={footerInputRef}
                  className="hidden"
                  accept="image/*"
                  onChange={(e) => handleUpload('footer', e.target.files?.[0])}
                />
                
                {settings.footer_image ? (
                  <div className="space-y-4">
                    <div className="border rounded-lg overflow-hidden bg-gray-50">
                      <img 
                        src={settings.footer_image} 
                        alt="Footer Preview" 
                        className="w-full h-auto"
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-green-600 flex items-center gap-1">
                        <Check className="w-4 h-4" />
                        Footer uploaded
                      </span>
                      <div className="flex gap-2">
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => footerInputRef.current?.click()}
                        >
                          <RefreshCw className="w-4 h-4 mr-1" />
                          Replace
                        </Button>
                        <Button 
                          variant="destructive" 
                          size="sm"
                          onClick={() => handleDelete('footer')}
                        >
                          <Trash2 className="w-4 h-4 mr-1" />
                          Remove
                        </Button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div 
                    className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-orange-400 transition-colors"
                    onClick={() => footerInputRef.current?.click()}
                  >
                    <Upload className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                    <p className="text-sm text-gray-600">Click to upload footer image</p>
                    <p className="text-xs text-gray-400 mt-1">PNG, JPG up to 5MB</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <Card className="mt-6">
            <CardContent className="pt-6">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-blue-500 mt-0.5" />
                <div>
                  <h4 className="font-medium">Image Guidelines</h4>
                  <ul className="text-sm text-muted-foreground mt-2 space-y-1">
                    <li>• Header: Recommended size 800×150 pixels (or proportional)</li>
                    <li>• Footer: Recommended size 800×100 pixels (or proportional)</li>
                    <li>• Supported formats: PNG, JPG, JPEG</li>
                    <li>• Maximum file size: 5MB per image</li>
                    <li>• For best quality, use high-resolution images with transparent backgrounds (PNG)</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Preview Tab */}
        <TabsContent value="preview" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Letter Preview</CardTitle>
              <CardDescription>Preview how your letters will look with the current settings</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="border rounded-lg overflow-hidden bg-gray-100 p-4">
                <div className="transform scale-75 origin-top">
                  <CompanyLetterhead
                    headerImage={settings.header_image}
                    footerImage={settings.footer_image}
                    companyName={settings.company_name}
                    companyAddress={settings.company_address}
                    companyPhone={settings.company_phone}
                    companyEmail={settings.company_email}
                    companyCIN={settings.company_cin}
                  >
                    <LetterHeader 
                      date={new Date().toISOString()}
                      reference="DVBC/HR/2026/SAMPLE"
                      recipientName="John Doe"
                    />
                    
                    <div className="space-y-4">
                      <h2 className="text-xl font-bold text-center underline">
                        SAMPLE LETTER
                      </h2>
                      
                      <p>Dear John Doe,</p>
                      
                      <p>
                        This is a sample letter to preview how your company letterhead 
                        will appear on official documents such as offer letters and 
                        appointment letters.
                      </p>
                      
                      <p>
                        The header and footer images you upload will replace the default 
                        design shown here.
                      </p>
                      
                      <p className="mt-6">Warm regards,</p>
                      
                      <HRSignatureBlock 
                        signatureText="HR Manager"
                        hrName="Sample HR Manager"
                        hrDesignation="Human Resources"
                      />
                    </div>
                  </CompanyLetterhead>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Company Info Tab */}
        <TabsContent value="company" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Company Information</CardTitle>
              <CardDescription>
                This information appears on the default letterhead (when no custom images are uploaded)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Company Name</Label>
                  <Input 
                    value={settings.company_name || ''}
                    onChange={(e) => setSettings({...settings, company_name: e.target.value})}
                    disabled={!canEdit}
                  />
                </div>
                <div className="space-y-2">
                  <Label>CIN Number</Label>
                  <Input 
                    value={settings.company_cin || ''}
                    onChange={(e) => setSettings({...settings, company_cin: e.target.value})}
                    disabled={!canEdit}
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <Label>Registered Address</Label>
                <Input 
                  value={settings.company_address || ''}
                  onChange={(e) => setSettings({...settings, company_address: e.target.value})}
                  disabled={!canEdit}
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Phone Number</Label>
                  <Input 
                    value={settings.company_phone || ''}
                    onChange={(e) => setSettings({...settings, company_phone: e.target.value})}
                    disabled={!canEdit}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Email Address</Label>
                  <Input 
                    value={settings.company_email || ''}
                    onChange={(e) => setSettings({...settings, company_email: e.target.value})}
                    disabled={!canEdit}
                  />
                </div>
              </div>
              
              {canEdit && (
                <Button onClick={handleSaveSettings} disabled={saving} className="mt-4">
                  {saving ? 'Saving...' : 'Save Company Info'}
                </Button>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default LetterheadSettings;
