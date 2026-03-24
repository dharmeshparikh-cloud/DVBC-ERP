import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Checkbox } from '../components/ui/checkbox';
import { 
  FileCheck, Shield, Lock, CheckCircle2, AlertTriangle, 
  ChevronRight, FileText, Building2
} from 'lucide-react';
import { toast } from 'sonner';
import { useParams, useNavigate } from 'react-router-dom';

const API = process.env.REACT_APP_BACKEND_URL;

const ConsentPage = () => {
  const { token } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [consentData, setConsentData] = useState(null);
  const [acceptedDocs, setAcceptedDocs] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [currentDocIndex, setCurrentDocIndex] = useState(0);
  const [allComplete, setAllComplete] = useState(false);

  useEffect(() => {
    fetchConsentStatus();
  }, [token]);

  const fetchConsentStatus = async () => {
    try {
      const res = await axios.get(`${API}/api/consent/pending/${token}`);
      setConsentData(res.data);
      
      if (res.data.status === 'complete') {
        setAllComplete(true);
      } else {
        // Initialize accepted docs state
        const initial = {};
        res.data.completed_documents?.forEach(doc => {
          initial[doc] = true;
        });
        setAcceptedDocs(initial);
      }
    } catch (error) {
      toast.error('Invalid or expired consent link');
    } finally {
      setLoading(false);
    }
  };

  const handleAcceptDocument = async (docType) => {
    if (acceptedDocs[docType]) return;
    
    setSubmitting(true);
    try {
      const res = await axios.post(`${API}/api/consent/accept/${token}`, {
        document_type: docType
      });
      
      setAcceptedDocs(prev => ({ ...prev, [docType]: true }));
      toast.success(`${res.data.message}`);
      
      if (res.data.all_complete) {
        setAllComplete(true);
      } else {
        // Move to next document
        setCurrentDocIndex(prev => prev + 1);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to accept document');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-orange-500"></div>
      </div>
    );
  }

  if (allComplete) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-emerald-50 to-teal-50 flex items-center justify-center p-4">
        <Card className="max-w-lg w-full border-emerald-200 shadow-xl">
          <CardContent className="pt-12 pb-8 text-center">
            <div className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle2 className="h-10 w-10 text-emerald-600" />
            </div>
            <h2 className="text-2xl font-bold text-zinc-900 mb-2">All Set!</h2>
            <p className="text-zinc-600 mb-6">
              You have successfully accepted all required documents. 
              Your ERP access has been enabled.
            </p>
            <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 text-sm text-emerald-800 mb-6">
              <p className="font-medium">Welcome to D&V Business Consulting!</p>
              <p className="mt-1">You can now login to NETRA ERP using your Employee ID.</p>
            </div>
            <Button 
              onClick={() => navigate('/login')}
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
            >
              Go to Login
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const pendingDocs = consentData?.pending_documents || [];
  const currentDoc = pendingDocs[currentDocIndex];
  const progress = ((Object.keys(acceptedDocs || {}).length) / (pendingDocs.length + Object.keys(acceptedDocs || {}).length)) * 100;

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-amber-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-orange-500 to-amber-500 text-white py-8 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center gap-3 mb-4">
            <Building2 className="h-8 w-8" />
            <span className="text-xl font-semibold">D&V Business Consulting</span>
          </div>
          <h1 className="text-3xl font-bold mb-2">Employment Confirmation</h1>
          <p className="text-orange-100">
            Welcome, {consentData?.employee_name}! Please review and accept the following documents.
          </p>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="bg-white border-b border-zinc-200 px-4 py-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-zinc-700">Progress</span>
            <span className="text-sm text-zinc-500">
              {Object.keys(acceptedDocs || {}).length} of {pendingDocs.length + Object.keys(acceptedDocs || {}).length} documents accepted
            </span>
          </div>
          <div className="w-full bg-zinc-200 rounded-full h-2">
            <div 
              className="bg-orange-500 h-2 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto p-4 py-8">
        {/* Already Accepted Documents */}
        {Object.keys(acceptedDocs || {}).length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-medium text-zinc-500 mb-3">Accepted Documents</h3>
            <div className="flex flex-wrap gap-2">
              {Object.keys(acceptedDocs || {}).map(docType => (
                <div key={docType} className="flex items-center gap-2 bg-emerald-100 text-emerald-700 px-3 py-1.5 rounded-full text-sm">
                  <CheckCircle2 className="h-4 w-4" />
                  {docType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Current Document */}
        {currentDoc && (
          <Card className="border-zinc-200 shadow-lg">
            <CardHeader className="border-b border-zinc-100 bg-zinc-50">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                  <FileText className="h-6 w-6 text-orange-600" />
                </div>
                <div>
                  <CardTitle className="text-lg">{currentDoc.title}</CardTitle>
                  <p className="text-sm text-zinc-500">Version {currentDoc.version}</p>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-6">
              {/* Summary */}
              <div className="mb-6">
                <h4 className="font-medium text-zinc-900 mb-2">Summary</h4>
                <p className="text-zinc-600 text-sm leading-relaxed">
                  {currentDoc.content_summary}
                </p>
              </div>

              {/* Key Points */}
              {currentDoc.key_points?.length > 0 && (
                <div className="mb-6">
                  <h4 className="font-medium text-zinc-900 mb-3">Key Points</h4>
                  <div className="space-y-2">
                    {(currentDoc?.key_points || []).map((point, idx) => (
                      <div key={idx} className="flex items-start gap-3 bg-zinc-50 p-3 rounded-lg">
                        <ChevronRight className="h-5 w-5 text-orange-500 flex-shrink-0 mt-0.5" />
                        <p className="text-sm text-zinc-700">{point}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Legal Notice */}
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-amber-800">
                    <p className="font-medium">Important Notice</p>
                    <p className="mt-1">
                      By accepting this document, you acknowledge that you have read, understood, and agree to 
                      be bound by its terms. This acceptance is legally binding.
                    </p>
                  </div>
                </div>
              </div>

              {/* Accept Checkbox */}
              <div className="flex items-start gap-3 mb-6 p-4 border border-zinc-200 rounded-lg">
                <Checkbox 
                  id={`accept-${currentDoc.type}`}
                  className="mt-1"
                  checked={acceptedDocs[currentDoc.type] || false}
                  disabled={acceptedDocs[currentDoc.type]}
                />
                <label 
                  htmlFor={`accept-${currentDoc.type}`}
                  className="text-sm text-zinc-700 cursor-pointer"
                >
                  I have read, understood, and agree to the terms of the <strong>{currentDoc.title}</strong>. 
                  I understand that this is a legally binding agreement.
                </label>
              </div>

              {/* Accept Button */}
              <Button
                onClick={() => handleAcceptDocument(currentDoc.type)}
                disabled={submitting || acceptedDocs[currentDoc.type]}
                className="w-full bg-orange-500 hover:bg-orange-600 text-white py-6 text-lg"
              >
                {submitting ? (
                  <span className="flex items-center gap-2">
                    <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-b-2 border-white"></div>
                    Processing...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <FileCheck className="h-5 w-5" />
                    Accept & Continue
                  </span>
                )}
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Remaining Documents */}
        {pendingDocs.length > 1 && currentDocIndex < pendingDocs.length - 1 && (
          <div className="mt-6">
            <h3 className="text-sm font-medium text-zinc-500 mb-3">Remaining Documents</h3>
            <div className="space-y-2">
              {(pendingDocs || []).slice(currentDocIndex + 1).map((doc, idx) => (
                <div key={doc.type} className="flex items-center gap-3 bg-white p-3 rounded-lg border border-zinc-200">
                  <div className="w-8 h-8 bg-zinc-100 rounded flex items-center justify-center text-sm font-medium text-zinc-500">
                    {currentDocIndex + idx + 2}
                  </div>
                  <span className="text-sm text-zinc-700">{doc.title}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="bg-zinc-100 border-t border-zinc-200 py-6 px-4 mt-8">
        <div className="max-w-4xl mx-auto text-center text-sm text-zinc-500">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Shield className="h-4 w-4" />
            <span>Your consent is securely recorded with timestamp and IP address</span>
          </div>
          <p>D&V Business Consulting Pvt. Ltd. | NETRA ERP</p>
        </div>
      </div>
    </div>
  );
};

export default ConsentPage;
