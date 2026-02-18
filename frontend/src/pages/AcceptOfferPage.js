import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { CheckCircle, FileText, Building2, Calendar, DollarSign, AlertCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import CompanyLetterhead, { HRSignatureBlock, LetterHeader, AcceptanceStamp } from '../components/CompanyLetterhead';

const API = process.env.REACT_APP_BACKEND_URL;

const AcceptOfferPage = () => {
  const { token } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [accepting, setAccepting] = useState(false);
  const [letterData, setLetterData] = useState(null);
  const [error, setError] = useState(null);
  const [accepted, setAccepted] = useState(false);
  const [acceptanceResult, setAcceptanceResult] = useState(null);

  useEffect(() => {
    fetchLetter();
  }, [token]);

  const fetchLetter = async () => {
    try {
      const response = await fetch(`${API}/api/letters/view/offer/${token}`);
      if (response.ok) {
        const data = await response.json();
        setLetterData(data);
        if (!data.can_accept) {
          setAccepted(true);
        }
      } else {
        setError('This offer letter link is invalid or has expired.');
      }
    } catch (err) {
      setError('Failed to load offer letter. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleAccept = async () => {
    setAccepting(true);
    try {
      const response = await fetch(`${API}/api/letters/offer-letters/accept`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ acceptance_token: token })
      });

      if (response.ok) {
        const result = await response.json();
        setAcceptanceResult(result);
        setAccepted(true);
        toast.success('Offer accepted successfully!');
      } else {
        const err = await response.json();
        toast.error(err.detail || 'Failed to accept offer');
      }
    } catch (err) {
      toast.error('Error accepting offer. Please try again.');
    } finally {
      setAccepting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-orange-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading your offer letter...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
        <Card className="max-w-md w-full">
          <CardContent className="pt-6 text-center">
            <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-gray-800 mb-2">Link Invalid</h2>
            <p className="text-gray-600">{error}</p>
            <p className="text-sm text-gray-500 mt-4">
              Please contact HR if you believe this is an error.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const letter = letterData?.letter;
  const template = letterData?.template;

  return (
    <div className="min-h-screen bg-gray-100 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Success Banner */}
        {accepted && acceptanceResult && (
          <Card className="mb-6 border-green-500 bg-green-50">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <CheckCircle className="w-12 h-12 text-green-600" />
                <div>
                  <h2 className="text-xl font-bold text-green-800">Offer Accepted Successfully!</h2>
                  <p className="text-green-700">
                    Welcome aboard, <strong>{acceptanceResult.candidate_name}</strong>!
                  </p>
                  <p className="text-green-600 text-sm mt-1">
                    Your Employee ID: <strong className="text-lg">{acceptanceResult.employee_id}</strong>
                  </p>
                  <p className="text-xs text-green-600 mt-2">{acceptanceResult.acceptance_signature}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Letter Preview */}
        <div className="bg-white shadow-xl rounded-lg overflow-hidden">
          <CompanyLetterhead>
            <LetterHeader 
              date={letter?.created_at}
              reference={`DVBC/HR/${new Date().getFullYear()}/OFFER/${letter?.id?.slice(0,8).toUpperCase()}`}
              recipientName={letter?.candidate_name}
            />
            
            <div className="letter-body space-y-4">
              <h2 className="text-xl font-bold text-center mb-6 underline decoration-2">
                OFFER OF EMPLOYMENT
              </h2>
              
              <p>Dear <strong>{letter?.candidate_name}</strong>,</p>
              
              <p>
                We are pleased to offer you the position of <strong>{letter?.designation}</strong> in 
                our <strong>{letter?.department}</strong> department at D&V Business Consulting Pvt. Ltd.
              </p>
              
              <div className="bg-gray-50 p-4 rounded-lg my-6">
                <h3 className="font-semibold mb-3 flex items-center gap-2">
                  <FileText className="w-5 h-5 text-orange-500" />
                  Employment Details
                </h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-gray-500" />
                    <span className="text-gray-600">Position:</span>
                    <span className="font-medium">{letter?.designation}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-gray-500" />
                    <span className="text-gray-600">Department:</span>
                    <span className="font-medium">{letter?.department}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-gray-500" />
                    <span className="text-gray-600">Joining Date:</span>
                    <span className="font-medium">
                      {letter?.joining_date ? new Date(letter.joining_date).toLocaleDateString('en-IN', {
                        day: '2-digit',
                        month: 'long',
                        year: 'numeric'
                      }) : 'TBD'}
                    </span>
                  </div>
                  {letter?.salary_details?.gross_monthly && (
                    <div className="flex items-center gap-2">
                      <DollarSign className="w-4 h-4 text-gray-500" />
                      <span className="text-gray-600">Gross Monthly:</span>
                      <span className="font-medium">
                        ₹{Number(letter.salary_details.gross_monthly).toLocaleString('en-IN')}
                      </span>
                    </div>
                  )}
                </div>
              </div>
              
              <p>
                This offer is subject to successful completion of reference checks and 
                submission of all required documents. Please indicate your acceptance 
                of this offer by clicking the button below.
              </p>
              
              <p>
                We look forward to welcoming you to our team!
              </p>
              
              <p className="mt-6">Warm regards,</p>
              
              <HRSignatureBlock 
                signatureText={letter?.hr_signature_text}
                hrName={letter?.created_by_name}
                hrDesignation="HR Manager"
              />
              
              {/* Acceptance Section */}
              {accepted ? (
                <AcceptanceStamp 
                  employeeName={letter?.candidate_name || acceptanceResult?.candidate_name}
                  acceptedAt={letter?.accepted_at || new Date().toISOString()}
                  employeeId={letter?.employee_id_assigned || acceptanceResult?.employee_id}
                />
              ) : (
                <div className="mt-8 pt-6 border-t-2 border-dashed border-gray-300">
                  <div className="bg-orange-50 border border-orange-200 rounded-lg p-6 text-center">
                    <h3 className="font-bold text-lg mb-2">Accept This Offer</h3>
                    <p className="text-sm text-gray-600 mb-4">
                      By clicking "Accept Offer", you confirm that you have read and agree to the 
                      terms of this employment offer. Your acceptance will be digitally recorded.
                    </p>
                    <Button 
                      size="lg"
                      onClick={handleAccept}
                      disabled={accepting}
                      className="bg-green-600 hover:bg-green-700"
                      data-testid="accept-offer-btn"
                    >
                      {accepting ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Processing...
                        </>
                      ) : (
                        <>
                          <CheckCircle className="w-4 h-4 mr-2" />
                          Accept Offer
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </CompanyLetterhead>
        </div>
        
        {/* Footer */}
        <p className="text-center text-xs text-gray-500 mt-6">
          This is an official document from D&V Business Consulting Pvt. Ltd.
          <br />
          For any queries, please contact hr@dvconsulting.co.in
        </p>
      </div>
    </div>
  );
};

export default AcceptOfferPage;
