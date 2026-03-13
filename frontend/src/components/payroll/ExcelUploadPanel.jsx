/**
 * ExcelUploadPanel - Bulk Data Import via Excel
 * Supports employees, attendance, leave balance, and salary structure imports
 */

import React, { useState, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../../components/ui/dialog';
import { 
  Upload, Download, FileSpreadsheet, CheckCircle, XCircle, 
  AlertTriangle, RefreshCw, Users, Calendar, DollarSign, Briefcase
} from 'lucide-react';
import { toast } from 'sonner';
import { useQuery, useMutation } from '@tanstack/react-query';
import axios from 'axios';
import { API } from '../../App';

const TEMPLATE_ICONS = {
  employees: Users,
  attendance: Calendar,
  leave_balance: Briefcase,
  salary_structure: DollarSign
};

const TEMPLATE_COLORS = {
  employees: 'bg-blue-100 text-blue-600',
  attendance: 'bg-emerald-100 text-emerald-600',
  leave_balance: 'bg-purple-100 text-purple-600',
  salary_structure: 'bg-amber-100 text-amber-600'
};

const ExcelUploadPanel = ({ onSuccess }) => {
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [uploadDialog, setUploadDialog] = useState(false);
  const [resultsDialog, setResultsDialog] = useState(false);
  const [uploadResults, setUploadResults] = useState(null);
  const [isDryRun, setIsDryRun] = useState(true);
  const fileInputRef = useRef(null);

  // Fetch templates
  const { data: templatesData, isLoading } = useQuery({
    queryKey: ['excel-templates'],
    queryFn: async () => {
      const res = await axios.get(`${API}/excel-upload/templates`);
      return res.data;
    }
  });

  const templates = templatesData?.templates || [];

  // Download template
  const downloadTemplate = async (templateId) => {
    try {
      const res = await axios.get(`${API}/excel-upload/templates/${templateId}/download`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${templateId}_template.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Template downloaded');
    } catch (err) {
      toast.error('Failed to download template');
    }
  };

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: async ({ file, templateId, dryRun }) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('dry_run', dryRun);
      
      const res = await axios.post(
        `${API}/excel-upload/upload/${templateId}`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      return res.data;
    },
    onSuccess: (data) => {
      setUploadResults(data);
      setResultsDialog(true);
      setUploadDialog(false);
      
      if (!data.dry_run) {
        toast.success(data.message || 'Upload successful');
        onSuccess?.();
      }
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Upload failed');
    }
  });

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    if (!file.name.match(/\.(xlsx|xls)$/i)) {
      toast.error('Please select an Excel file (.xlsx or .xls)');
      return;
    }
    
    uploadMutation.mutate({
      file,
      templateId: selectedTemplate.id,
      dryRun: isDryRun
    });
    
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleImportConfirmed = () => {
    // Close results dialog and re-upload with dry_run=false
    setResultsDialog(false);
    setIsDryRun(false);
    
    // Trigger file select again
    fileInputRef.current?.click();
  };

  const openUploadDialog = (template) => {
    setSelectedTemplate(template);
    setIsDryRun(true);
    setUploadDialog(true);
  };

  return (
    <>
      <Card className="border-zinc-200 dark:border-zinc-700">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-emerald-500" />
            Excel Bulk Upload
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="w-6 h-6 animate-spin text-zinc-400" />
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {templates.map((template) => {
                const Icon = TEMPLATE_ICONS[template.id] || FileSpreadsheet;
                const colorClass = TEMPLATE_COLORS[template.id] || 'bg-zinc-100 text-zinc-600';
                
                return (
                  <div 
                    key={template.id}
                    className="bg-zinc-50 dark:bg-zinc-800 rounded-xl p-4 border border-zinc-200 dark:border-zinc-700"
                  >
                    <div className="flex items-start gap-3">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colorClass}`}>
                        <Icon className="w-5 h-5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-medium text-zinc-900 dark:text-zinc-100">
                          {template.name}
                        </h3>
                        <p className="text-xs text-zinc-500 mt-0.5">
                          {template.description}
                        </p>
                        <div className="flex flex-wrap gap-1 mt-2">
                          {template.required?.slice(0, 3).map((col) => (
                            <Badge key={col} variant="outline" className="text-xs">
                              {col}
                            </Badge>
                          ))}
                          {template.required?.length > 3 && (
                            <Badge variant="outline" className="text-xs">
                              +{template.required.length - 3} more
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-2 mt-4">
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => downloadTemplate(template.id)}
                        className="flex-1"
                      >
                        <Download className="w-4 h-4 mr-1" />
                        Template
                      </Button>
                      <Button 
                        size="sm"
                        onClick={() => openUploadDialog(template)}
                        className="flex-1 bg-emerald-600 hover:bg-emerald-700"
                      >
                        <Upload className="w-4 h-4 mr-1" />
                        Upload
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Upload Dialog */}
      <Dialog open={uploadDialog} onOpenChange={setUploadDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Upload className="w-5 h-5 text-emerald-500" />
              Upload {selectedTemplate?.name}
            </DialogTitle>
            <DialogDescription>
              Upload an Excel file to import data. The file will be validated first.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5" />
                <div className="text-sm text-amber-700 dark:text-amber-300">
                  <p className="font-medium">Required columns:</p>
                  <p className="text-xs mt-1">
                    {selectedTemplate?.required?.join(', ')}
                  </p>
                </div>
              </div>
            </div>
            
            <div 
              className="border-2 border-dashed border-zinc-300 dark:border-zinc-600 rounded-xl p-8 text-center cursor-pointer hover:border-emerald-400 transition-colors"
              onClick={() => fileInputRef.current?.click()}
            >
              {uploadMutation.isPending ? (
                <RefreshCw className="w-10 h-10 mx-auto mb-3 text-emerald-500 animate-spin" />
              ) : (
                <FileSpreadsheet className="w-10 h-10 mx-auto mb-3 text-zinc-400" />
              )}
              <p className="text-zinc-600 dark:text-zinc-400">
                {uploadMutation.isPending ? 'Processing...' : 'Click to select Excel file'}
              </p>
              <p className="text-xs text-zinc-400 mt-1">.xlsx or .xls files only</p>
            </div>
            
            <input 
              ref={fileInputRef}
              type="file" 
              accept=".xlsx,.xls"
              onChange={handleFileSelect}
              className="hidden"
            />
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setUploadDialog(false)}>
              Cancel
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Results Dialog */}
      <Dialog open={resultsDialog} onOpenChange={setResultsDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {uploadResults?.dry_run ? (
                <>
                  <AlertTriangle className="w-5 h-5 text-amber-500" />
                  Validation Results
                </>
              ) : (
                <>
                  <CheckCircle className="w-5 h-5 text-emerald-500" />
                  Import Complete
                </>
              )}
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            {/* Summary */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-emerald-50 dark:bg-emerald-900/20 rounded-lg p-4 text-center">
                <CheckCircle className="w-6 h-6 mx-auto mb-2 text-emerald-500" />
                <p className="text-2xl font-bold text-emerald-600">
                  {uploadResults?.valid_count || uploadResults?.created || 0}
                </p>
                <p className="text-sm text-zinc-500">Valid Records</p>
              </div>
              <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4 text-center">
                <XCircle className="w-6 h-6 mx-auto mb-2 text-red-500" />
                <p className="text-2xl font-bold text-red-600">
                  {uploadResults?.error_count || uploadResults?.errors || 0}
                </p>
                <p className="text-sm text-zinc-500">Errors</p>
              </div>
            </div>

            {/* Error Details */}
            {(uploadResults?.error_records?.length > 0 || uploadResults?.error_details?.length > 0) && (
              <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4 max-h-60 overflow-y-auto">
                <h4 className="font-medium text-red-700 dark:text-red-400 mb-2">Errors:</h4>
                <div className="space-y-2">
                  {(uploadResults?.error_records || uploadResults?.error_details || []).slice(0, 10).map((err, i) => (
                    <div key={i} className="text-sm bg-white dark:bg-zinc-800 rounded p-2">
                      <span className="font-medium text-red-600">Row {err.row}:</span>
                      <span className="text-zinc-600 dark:text-zinc-400 ml-2">
                        {err.errors?.join(', ')}
                      </span>
                    </div>
                  ))}
                  {(uploadResults?.error_records?.length || uploadResults?.error_details?.length || 0) > 10 && (
                    <p className="text-xs text-zinc-500 text-center">
                      ...and {(uploadResults?.error_records?.length || uploadResults?.error_details?.length) - 10} more errors
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Dry Run Message */}
            {uploadResults?.dry_run && uploadResults?.valid_count > 0 && (
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
                <p className="text-sm text-blue-700 dark:text-blue-300">
                  This was a validation run. Click "Confirm Import" to actually import the valid records.
                </p>
              </div>
            )}
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setResultsDialog(false)}>
              Close
            </Button>
            {uploadResults?.dry_run && uploadResults?.valid_count > 0 && (
              <Button 
                onClick={handleImportConfirmed}
                className="bg-emerald-600 hover:bg-emerald-700"
              >
                <CheckCircle className="w-4 h-4 mr-2" />
                Confirm Import ({uploadResults.valid_count} records)
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default ExcelUploadPanel;
