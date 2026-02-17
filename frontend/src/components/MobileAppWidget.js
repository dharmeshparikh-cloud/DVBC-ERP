import React, { useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Smartphone, Download, Apple, X, QrCode, ExternalLink } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';

const MOBILE_APP_PATH = '/mobile';

const MobileAppWidget = ({ compact = false }) => {
  const [showQRDialog, setShowQRDialog] = useState(false);
  const mobileAppUrl = `${window.location.origin}${MOBILE_APP_PATH}`;

  if (compact) {
    return (
      <>
        <Button
          onClick={() => setShowQRDialog(true)}
          variant="outline"
          className="flex items-center gap-2"
          data-testid="mobile-app-qr-btn"
        >
          <QrCode className="w-4 h-4" />
          Mobile App
        </Button>
        
        <Dialog open={showQRDialog} onOpenChange={setShowQRDialog}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Smartphone className="w-5 h-5 text-emerald-600" />
                Download Mobile App
              </DialogTitle>
            </DialogHeader>
            <MobileAppContent mobileAppUrl={mobileAppUrl} />
          </DialogContent>
        </Dialog>
      </>
    );
  }

  return (
    <Card className="border-zinc-200 dark:border-zinc-700 shadow-none rounded-sm" data-testid="mobile-app-widget">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-950 dark:text-zinc-100 flex items-center gap-2">
          <Smartphone className="w-4 h-4 text-emerald-600" />
          Employee Mobile App
        </CardTitle>
      </CardHeader>
      <CardContent>
        <MobileAppContent mobileAppUrl={mobileAppUrl} showQR />
      </CardContent>
    </Card>
  );
};

const MobileAppContent = ({ mobileAppUrl, showQR = true }) => {
  return (
    <div className="space-y-4">
      {showQR && (
        <div className="flex justify-center p-4 bg-white rounded-lg border border-zinc-200">
          <QRCodeSVG 
            value={mobileAppUrl} 
            size={140}
            level="H"
            includeMargin={true}
          />
        </div>
      )}
      
      <div className="text-center">
        <p className="text-sm text-zinc-600 dark:text-zinc-400 mb-3">
          Scan QR code or click below to open the mobile app
        </p>
        <a
          href={MOBILE_APP_PATH}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors text-sm font-medium"
          data-testid="open-mobile-app-link"
        >
          <ExternalLink className="w-4 h-4" />
          Open Mobile App
        </a>
      </div>

      <div className="border-t border-zinc-200 dark:border-zinc-700 pt-4 mt-4">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-zinc-500 mb-3">
          Install on Your Phone
        </h4>
        
        <div className="space-y-3">
          {/* iOS Instructions */}
          <div className="p-3 bg-zinc-50 dark:bg-zinc-800 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <Apple className="w-4 h-4 text-zinc-700 dark:text-zinc-300" />
              <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">iPhone / iPad</span>
            </div>
            <ol className="text-xs text-zinc-600 dark:text-zinc-400 space-y-1 ml-6 list-decimal">
              <li>Open the link in <strong>Safari</strong></li>
              <li>Tap the <strong>Share</strong> button (square with arrow)</li>
              <li>Scroll down and tap <strong>"Add to Home Screen"</strong></li>
              <li>Tap <strong>"Add"</strong> to install</li>
            </ol>
          </div>

          {/* Android Instructions */}
          <div className="p-3 bg-zinc-50 dark:bg-zinc-800 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <Smartphone className="w-4 h-4 text-emerald-600" />
              <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">Android</span>
            </div>
            <ol className="text-xs text-zinc-600 dark:text-zinc-400 space-y-1 ml-6 list-decimal">
              <li>Open the link in <strong>Chrome</strong></li>
              <li>Tap the <strong>⋮</strong> menu (three dots)</li>
              <li>Tap <strong>"Add to Home screen"</strong></li>
              <li>Tap <strong>"Add"</strong> to install</li>
            </ol>
          </div>
        </div>
      </div>

      <div className="text-center pt-2">
        <p className="text-[10px] text-zinc-400">
          The app works offline and receives push notifications
        </p>
      </div>
    </div>
  );
};

export default MobileAppWidget;
