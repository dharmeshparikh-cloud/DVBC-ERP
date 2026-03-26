/**
 * AttendanceTab - Mobile Attendance Tab
 * Shows check-in status, monthly stats, and attendance history
 * Extracted from EmployeeMobileApp.js for better maintainability
 */

import React, { memo } from 'react';
import { 
  CheckCircle, CheckCircle2, Clock, MapPin, Building2, 
  Calendar, Camera, XCircle 
} from 'lucide-react';
import { LazyImage } from '../../ui/lazy-image';

export const AttendanceTab = memo(({
  currentTime,
  formatTime,
  formatDate,
  checkInStatus,
  attendanceData,
  onCheckIn
}) => {
  return (
    <div className="space-y-4 pb-24">
      {/* Check-in Card */}
      <div className="bg-gradient-to-br from-indigo-600 to-purple-700 rounded-3xl p-6 text-white shadow-xl">
        <div className="text-center">
          <p className="text-indigo-200 text-sm mb-2">{formatDate(currentTime)}</p>
          <p className="text-5xl font-bold tracking-wider mb-4">{formatTime(currentTime)}</p>
          
          {checkInStatus ? (
            <div className="bg-white/10 rounded-2xl p-4 backdrop-blur">
              <div className={`flex items-center justify-center gap-2 mb-2 ${
                checkInStatus.approval_status === 'approved' ? 'text-emerald-300' :
                checkInStatus.approval_status === 'pending_approval' ? 'text-amber-300' : 'text-red-300'
              }`}>
                {checkInStatus.approval_status === 'approved' ? <CheckCircle className="w-5 h-5" /> :
                 checkInStatus.approval_status === 'pending_approval' ? <Clock className="w-5 h-5" /> :
                 <XCircle className="w-5 h-5" />}
                <span className="font-medium">
                  {checkInStatus.approval_status === 'approved' ? "You're Checked In" :
                   checkInStatus.approval_status === 'pending_approval' ? "Pending HR Approval" : "Check-in Rejected"}
                </span>
              </div>
              <p className="text-sm text-indigo-200">
                {checkInStatus.check_in_time ? 
                  `Since ${new Date(checkInStatus.check_in_time).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Kolkata' })}` :
                  'Today'}
              </p>
              {checkInStatus.geo_location?.address && (
                <p className="text-xs text-indigo-300 mt-2 flex items-center justify-center gap-1">
                  <MapPin className="w-3 h-3" />
                  {checkInStatus.geo_location.address.split(',').slice(0, 2).join(',')}
                </p>
              )}
              {checkInStatus.location_validation?.matched_location && (
                <p className="text-xs text-emerald-300 mt-1">
                  Verified: {checkInStatus.location_validation.matched_location}
                </p>
              )}
            </div>
          ) : (
            <button 
              onClick={onCheckIn}
              className="w-full py-4 bg-white text-indigo-700 rounded-2xl font-semibold text-lg shadow-lg hover:bg-indigo-50 transition flex items-center justify-center gap-2"
              data-testid="attendance-checkin-btn"
            >
              <Camera className="w-6 h-6" />
              Check In with Selfie
            </button>
          )}
        </div>
      </div>

      {/* Monthly Stats */}
      <div className="grid grid-cols-2 gap-3">
        {[
          { label: 'Office', value: (attendanceData?.records || []).filter(r => r.work_location === 'in_office' && r.approval_status === 'approved').length, icon: Building2, color: 'emerald' },
          { label: 'On-Site', value: (attendanceData?.records || []).filter(r => r.work_location === 'onsite' && r.approval_status === 'approved').length, icon: MapPin, color: 'blue' },
          { label: 'Pending', value: (attendanceData?.records || []).filter(r => r.approval_status === 'pending_approval').length, icon: Clock, color: 'amber' },
          { label: 'Leave', value: attendanceData?.summary?.on_leave || 0, icon: Calendar, color: 'purple' },
        ].map((item, i) => (
          <div key={i} className="bg-white rounded-2xl p-4 shadow-sm border border-zinc-100">
            <div className={`w-10 h-10 rounded-xl bg-${item.color}-100 text-${item.color}-600 flex items-center justify-center mb-2`}>
              <item.icon className="w-5 h-5" />
            </div>
            <p className="text-2xl font-bold text-zinc-900">{item.value}</p>
            <p className="text-xs text-zinc-500">{item.label}</p>
          </div>
        ))}
      </div>

      {/* Attendance History */}
      <div className="bg-white rounded-2xl shadow-sm border border-zinc-100 overflow-hidden">
        <div className="p-4 border-b border-zinc-100">
          <h3 className="font-semibold text-zinc-900">Attendance History</h3>
        </div>
        <div className="divide-y divide-zinc-100">
          {(attendanceData?.records || []).slice(0, 10).map((record, i) => (
            <div key={i} className="flex items-center gap-3 p-4">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                record.approval_status === 'approved' ? 'bg-emerald-100 text-emerald-600' :
                record.approval_status === 'pending_approval' ? 'bg-amber-100 text-amber-600' :
                record.approval_status === 'rejected' ? 'bg-red-100 text-red-600' :
                'bg-blue-100 text-blue-600'
              }`}>
                {record.approval_status === 'approved' && <CheckCircle2 className="w-5 h-5" />}
                {record.approval_status === 'pending_approval' && <Clock className="w-5 h-5" />}
                {record.approval_status === 'rejected' && <XCircle className="w-5 h-5" />}
                {!record.approval_status && <CheckCircle2 className="w-5 h-5" />}
              </div>
              <div className="flex-1">
                <p className="font-medium text-zinc-900">{record.date}</p>
                <p className="text-xs text-zinc-500">
                  {record.work_location === 'in_office' ? 'Office' : 'On-Site'}
                  {record.approval_status === 'pending_approval' && ' - Pending'}
                  {record.approval_status === 'rejected' && ' - Rejected'}
                </p>
              </div>
              {record.selfie && (
                <LazyImage 
                  src={record.selfie} 
                  alt="selfie" 
                  width={32}
                  height={32}
                  className="rounded-full border-2 border-zinc-200"
                />
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
});

AttendanceTab.displayName = 'AttendanceTab';

export default AttendanceTab;
