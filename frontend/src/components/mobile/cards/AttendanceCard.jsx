/**
 * AttendanceCard - Today's Attendance Status Card
 * Shows check-in/out status with visual indicators
 */

import React from 'react';
import { Card, CardContent } from '../../ui/card';
import { Clock, LogIn, LogOut, MapPin, CheckCircle, AlertCircle } from 'lucide-react';

export const AttendanceCard = ({
  checkInStatus,
  isCheckedIn,
  isCheckedOut,
  onCheckIn,
  onCheckOut,
  loading = false
}) => {
  const getStatusColor = () => {
    if (isCheckedOut) return 'border-emerald-200 bg-emerald-50';
    if (isCheckedIn) return 'border-orange-200 bg-orange-50';
    return 'border-zinc-200 bg-white';
  };

  const getStatusIcon = () => {
    if (isCheckedOut) return <CheckCircle className="w-8 h-8 text-emerald-500" />;
    if (isCheckedIn) return <Clock className="w-8 h-8 text-orange-500 animate-pulse" />;
    return <AlertCircle className="w-8 h-8 text-zinc-400" />;
  };

  const getStatusText = () => {
    if (isCheckedOut) return 'Day Completed';
    if (isCheckedIn) return 'Working';
    return 'Not Checked In';
  };

  return (
    <Card className={`border-2 ${getStatusColor()} transition-colors`}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            {getStatusIcon()}
            <div>
              <h3 className="font-semibold text-zinc-900">Today's Attendance</h3>
              <p className="text-sm text-zinc-500">{getStatusText()}</p>
            </div>
          </div>
        </div>

        {/* Check-in details */}
        {checkInStatus && (
          <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
            <div className="flex items-center gap-2 p-2 bg-white rounded-lg border">
              <LogIn className="w-4 h-4 text-emerald-500" />
              <div>
                <p className="text-xs text-zinc-400">Check In</p>
                <p className="font-medium text-zinc-900">
                  {checkInStatus.check_in_time ? 
                    new Date(checkInStatus.check_in_time).toLocaleTimeString('en-IN', {
                      hour: '2-digit',
                      minute: '2-digit',
                      timeZone: 'Asia/Kolkata'
                    }) : '--:--'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 p-2 bg-white rounded-lg border">
              <LogOut className="w-4 h-4 text-red-500" />
              <div>
                <p className="text-xs text-zinc-400">Check Out</p>
                <p className="font-medium text-zinc-900">
                  {checkInStatus.check_out_time ? 
                    new Date(checkInStatus.check_out_time).toLocaleTimeString('en-IN', {
                      hour: '2-digit',
                      minute: '2-digit',
                      timeZone: 'Asia/Kolkata'
                    }) : '--:--'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Location info */}
        {checkInStatus?.work_location && (
          <div className="flex items-center gap-2 text-xs text-zinc-500 mb-4">
            <MapPin className="w-3 h-3" />
            <span className="capitalize">{checkInStatus.work_location.replace('_', ' ')}</span>
            {checkInStatus.client_name && <span>• {checkInStatus.client_name}</span>}
          </div>
        )}

        {/* Action buttons */}
        <div className="flex gap-2">
          {!isCheckedIn ? (
            <button
              onClick={onCheckIn}
              disabled={loading}
              className="flex-1 flex items-center justify-center gap-2 py-3 px-4 bg-orange-500 text-white rounded-xl font-medium hover:bg-orange-600 transition-colors disabled:opacity-50"
              data-testid="check-in-btn"
            >
              <LogIn className="w-5 h-5" />
              Check In
            </button>
          ) : !isCheckedOut ? (
            <button
              onClick={onCheckOut}
              disabled={loading}
              className="flex-1 flex items-center justify-center gap-2 py-3 px-4 bg-red-500 text-white rounded-xl font-medium hover:bg-red-600 transition-colors disabled:opacity-50"
              data-testid="check-out-btn"
            >
              <LogOut className="w-5 h-5" />
              Check Out
            </button>
          ) : (
            <div className="flex-1 flex items-center justify-center gap-2 py-3 px-4 bg-emerald-100 text-emerald-700 rounded-xl font-medium">
              <CheckCircle className="w-5 h-5" />
              Work Day Complete
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default AttendanceCard;
