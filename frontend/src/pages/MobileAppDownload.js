import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { QRCodeSVG } from 'qrcode.react';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { 
  Smartphone, Apple, ExternalLink, CheckCircle, Users, 
  MapPin, Camera, Clock, Bell, Shield
} from 'lucide-react';

const MOBILE_APP_PATH = '/mobile';

const MobileAppDownload = () => {
  const { user } = useContext(AuthContext);
  const [stats, setStats] = useState(null);
  const mobileAppUrl = `${window.location.origin}${MOBILE_APP_PATH}`;

  useEffect(() => {
    fetchMobileStats();
  }, []);

  const fetchMobileStats = async () => {
    try {
      const response = await axios.get(`${API}/attendance/mobile-stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch mobile stats');
    }
  };

  const features = [
    { icon: Camera, title: 'Selfie Check-in', desc: 'Secure attendance with photo verification' },
    { icon: MapPin, title: 'GPS Location', desc: 'Automatic location capture for remote work' },
    { icon: Clock, title: 'Check-in/Out', desc: 'Track your work hours accurately' },
    { icon: Bell, title: 'Notifications', desc: 'Get alerts for approvals and updates' },
    { icon: Shield, title: 'Geofencing', desc: 'Auto-verify office/client locations' },
  ];

  return (
    <div className="max-w-4xl mx-auto" data-testid="mobile-app-download-page">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 dark:text-zinc-100 mb-2">
          Mobile App
        </h1>
        <p className="text-zinc-500 dark:text-zinc-400">Download and install the DVBC Employee Mobile App</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* QR Code Card */}
        <Card className="border-zinc-200 dark:border-zinc-700 shadow-none rounded-sm">
          <CardHeader>
            <CardTitle className="text-lg font-semibold text-zinc-950 dark:text-zinc-100 flex items-center gap-2">
              <Smartphone className="w-5 h-5 text-emerald-600" />
              Scan to Download
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex justify-center p-6 bg-white rounded-lg border border-zinc-200">
              <QRCodeSVG 
                value={mobileAppUrl} 
                size={200}
                level="H"
                includeMargin={true}
              />
            </div>
            
            <div className="text-center">
              <p className="text-sm text-zinc-600 dark:text-zinc-400 mb-4">
                Scan this QR code with your phone camera
              </p>
              <a
                href={MOBILE_APP_PATH}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-6 py-3 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors font-medium"
                data-testid="open-mobile-app-btn"
              >
                <ExternalLink className="w-5 h-5" />
                Open Mobile App
              </a>
            </div>

            <div className="text-center text-xs text-zinc-400 pt-4 border-t border-zinc-200 dark:border-zinc-700">
              App URL: <code className="bg-zinc-100 dark:bg-zinc-800 px-2 py-1 rounded">{mobileAppUrl}</code>
            </div>
          </CardContent>
        </Card>

        {/* Installation Instructions */}
        <Card className="border-zinc-200 dark:border-zinc-700 shadow-none rounded-sm">
          <CardHeader>
            <CardTitle className="text-lg font-semibold text-zinc-950 dark:text-zinc-100">
              Installation Guide
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* iOS */}
            <div className="p-4 bg-zinc-50 dark:bg-zinc-800 rounded-lg">
              <div className="flex items-center gap-2 mb-3">
                <Apple className="w-5 h-5 text-zinc-700 dark:text-zinc-300" />
                <span className="font-semibold text-zinc-900 dark:text-zinc-100">iPhone / iPad</span>
              </div>
              <ol className="text-sm text-zinc-600 dark:text-zinc-400 space-y-2 ml-4 list-decimal">
                <li>Open the QR code link in <strong>Safari</strong> browser</li>
                <li>Tap the <strong>Share</strong> button <span className="bg-zinc-200 dark:bg-zinc-700 px-1.5 py-0.5 rounded text-xs">⬆️</span></li>
                <li>Scroll down and tap <strong>"Add to Home Screen"</strong></li>
                <li>Name the app and tap <strong>"Add"</strong></li>
              </ol>
              <div className="mt-3 p-2 bg-blue-50 dark:bg-blue-900/20 rounded text-xs text-blue-700 dark:text-blue-300">
                💡 Must use Safari - Chrome doesn't support "Add to Home Screen" on iOS
              </div>
            </div>

            {/* Android */}
            <div className="p-4 bg-zinc-50 dark:bg-zinc-800 rounded-lg">
              <div className="flex items-center gap-2 mb-3">
                <Smartphone className="w-5 h-5 text-emerald-600" />
                <span className="font-semibold text-zinc-900 dark:text-zinc-100">Android</span>
              </div>
              <ol className="text-sm text-zinc-600 dark:text-zinc-400 space-y-2 ml-4 list-decimal">
                <li>Open the QR code link in <strong>Chrome</strong> browser</li>
                <li>Tap the <strong>menu</strong> button <span className="bg-zinc-200 dark:bg-zinc-700 px-1.5 py-0.5 rounded text-xs">⋮</span></li>
                <li>Tap <strong>"Install app"</strong> or <strong>"Add to Home screen"</strong></li>
                <li>Tap <strong>"Install"</strong> to confirm</li>
              </ol>
              <div className="mt-3 p-2 bg-emerald-50 dark:bg-emerald-900/20 rounded text-xs text-emerald-700 dark:text-emerald-300">
                ✨ Android may show an "Install" banner automatically
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Features */}
      <Card className="border-zinc-200 dark:border-zinc-700 shadow-none rounded-sm mt-6">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-zinc-950 dark:text-zinc-100">
            App Features
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {features.map((feature, idx) => (
              <div key={idx} className="text-center p-4 bg-zinc-50 dark:bg-zinc-800 rounded-lg">
                <feature.icon className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
                <h4 className="text-sm font-medium text-zinc-900 dark:text-zinc-100">{feature.title}</h4>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">{feature.desc}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Usage Stats (Admin/HR Only) */}
      {(user?.role === 'admin' || user?.role === 'hr_manager') && stats && (
        <Card className="border-zinc-200 dark:border-zinc-700 shadow-none rounded-sm mt-6" data-testid="mobile-usage-stats">
          <CardHeader>
            <CardTitle className="text-lg font-semibold text-zinc-950 dark:text-zinc-100 flex items-center gap-2">
              <Users className="w-5 h-5" />
              Mobile App Usage Stats
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-4 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg">
                <p className="text-3xl font-bold text-emerald-600">{stats.today_mobile_checkins || 0}</p>
                <p className="text-xs text-zinc-500 mt-1">Mobile Check-ins Today</p>
              </div>
              <div className="text-center p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <p className="text-3xl font-bold text-blue-600">{stats.today_desktop_checkins || 0}</p>
                <p className="text-xs text-zinc-500 mt-1">Desktop Check-ins Today</p>
              </div>
              <div className="text-center p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                <p className="text-3xl font-bold text-purple-600">{stats.total_mobile_users || 0}</p>
                <p className="text-xs text-zinc-500 mt-1">Total Mobile Users</p>
              </div>
              <div className="text-center p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
                <p className="text-3xl font-bold text-amber-600">{stats.pending_approvals || 0}</p>
                <p className="text-xs text-zinc-500 mt-1">Pending Approvals</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Help Section */}
      <div className="mt-6 p-4 bg-zinc-100 dark:bg-zinc-800 rounded-lg text-center">
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Need help? Contact HR at <strong>hr@dvconsulting.co.in</strong> or your manager.
        </p>
      </div>
    </div>
  );
};

export default MobileAppDownload;
