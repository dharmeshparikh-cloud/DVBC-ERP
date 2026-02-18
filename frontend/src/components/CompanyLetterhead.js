import React from 'react';

/**
 * DVBC Company Letterhead Component
 * Recreated based on company branding guidelines
 */
const CompanyLetterhead = ({ children, showFooter = true }) => {
  return (
    <div className="letterhead-container bg-white min-h-[297mm] w-full max-w-[210mm] mx-auto shadow-lg print:shadow-none">
      {/* Header Section */}
      <div className="letterhead-header border-b-4 border-orange-500 pb-4 px-8 pt-6">
        <div className="flex items-center justify-between">
          {/* Logo Section */}
          <div className="flex items-center gap-4">
            <div className="flex items-center">
              {/* D&V Logo */}
              <div className="flex flex-col">
                <div className="flex items-baseline">
                  <span className="text-3xl font-bold text-orange-600">D</span>
                  <span className="text-xl font-bold text-gray-600">&</span>
                  <span className="text-3xl font-bold text-orange-600">V</span>
                  <span className="text-xs text-gray-500 ml-1 align-top">®</span>
                </div>
                <span className="text-[10px] text-gray-500 tracking-wider -mt-1">BUSINESS CONSULTING</span>
              </div>
            </div>
            <div className="h-12 w-px bg-gray-300 mx-2"></div>
            <div className="flex flex-col">
              <span className="text-2xl font-bold text-gray-800 tracking-wide">DVBC</span>
              <span className="text-xs text-gray-500">NETRA</span>
            </div>
          </div>
          
          {/* Company Info */}
          <div className="text-right text-xs text-gray-600">
            <p className="font-semibold text-gray-800">D&V Business Consulting Pvt. Ltd.</p>
            <p>CIN: U74999MH2020PTC123456</p>
            <p>contact@dvconsulting.co.in</p>
            <p>+91 22 1234 5678</p>
          </div>
        </div>
      </div>

      {/* Content Area */}
      <div className="letterhead-content px-8 py-6 min-h-[200mm]">
        {children}
      </div>

      {/* Footer Section */}
      {showFooter && (
        <div className="letterhead-footer border-t-2 border-gray-200 px-8 py-4 mt-auto">
          <div className="flex justify-between items-center text-xs text-gray-500">
            <div>
              <p className="font-medium text-gray-700">Registered Office:</p>
              <p>123, Business Park, Andheri East</p>
              <p>Mumbai, Maharashtra - 400069</p>
            </div>
            <div className="text-right">
              <p>www.dvconsulting.co.in</p>
              <p className="text-[10px] mt-1">This is a computer generated document</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * HR Signature Block Component
 */
export const HRSignatureBlock = ({ signatureText, signatureImage, hrName, hrDesignation }) => {
  return (
    <div className="hr-signature mt-12 pt-4">
      <div className="flex flex-col items-start">
        {signatureImage && (
          <img 
            src={signatureImage} 
            alt="HR Signature" 
            className="h-16 mb-2"
          />
        )}
        {signatureText && !signatureImage && (
          <p className="font-script text-2xl text-gray-700 italic mb-2">{signatureText}</p>
        )}
        <div className="border-t border-gray-400 pt-2 min-w-[200px]">
          <p className="font-semibold text-gray-800">{hrName || 'HR Manager'}</p>
          <p className="text-sm text-gray-600">{hrDesignation || 'Human Resources'}</p>
          <p className="text-xs text-gray-500">D&V Business Consulting Pvt. Ltd.</p>
        </div>
      </div>
    </div>
  );
};

/**
 * Employee Acceptance Stamp Component
 */
export const AcceptanceStamp = ({ employeeName, acceptedAt, employeeId }) => {
  return (
    <div className="acceptance-stamp mt-8 p-4 border-2 border-green-500 rounded-lg bg-green-50 inline-block">
      <div className="flex items-center gap-2 mb-2">
        <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="font-bold text-green-700">ACCEPTED</span>
      </div>
      <p className="text-sm text-gray-700">
        Digitally signed by <strong>{employeeName}</strong>
      </p>
      {employeeId && (
        <p className="text-sm text-gray-600">Employee ID: {employeeId}</p>
      )}
      <p className="text-xs text-gray-500 mt-1">
        {acceptedAt ? new Date(acceptedAt).toLocaleString() : 'Date pending'}
      </p>
    </div>
  );
};

/**
 * Letter Date and Reference Component
 */
export const LetterHeader = ({ date, reference, recipientName, recipientAddress }) => {
  return (
    <div className="letter-header mb-8">
      <div className="flex justify-between mb-6">
        <div>
          <p className="text-sm text-gray-600">Ref: {reference}</p>
        </div>
        <div className="text-right">
          <p className="text-sm text-gray-600">
            Date: {date ? new Date(date).toLocaleDateString('en-IN', { 
              day: '2-digit', 
              month: 'long', 
              year: 'numeric' 
            }) : 'DD Month YYYY'}
          </p>
        </div>
      </div>
      
      <div className="recipient mt-4">
        <p className="font-medium">To,</p>
        <p className="font-semibold text-gray-800 mt-1">{recipientName}</p>
        {recipientAddress && (
          <p className="text-sm text-gray-600 whitespace-pre-line">{recipientAddress}</p>
        )}
      </div>
    </div>
  );
};

export default CompanyLetterhead;
