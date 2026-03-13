/**
 * TravelTab - Mobile Travel Claims Tab (Sales Team Only)
 * Shows travel reimbursement claims and rates
 * Extracted from EmployeeMobileApp.js for better maintainability
 */

import React, { memo } from 'react';
import { Car, Bike, Plus } from 'lucide-react';

export const TravelTab = memo(({
  travelClaims = [],
  onAddTravel
}) => {
  const totalAmount = travelClaims.reduce((sum, c) => sum + (c.final_amount || 0), 0);
  const totalKm = travelClaims.reduce((sum, c) => sum + (c.distance_km || 0), 0);
  const pendingCount = travelClaims.filter(c => c.status === 'pending').length;
  const approvedCount = travelClaims.filter(c => c.status === 'approved').length;

  return (
    <div className="space-y-4 pb-24">
      <div className="bg-gradient-to-br from-teal-500 to-cyan-600 rounded-3xl p-6 text-white shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-teal-100 text-sm">Travel Claims</p>
            <p className="text-3xl font-bold">₹{totalAmount.toLocaleString()}</p>
          </div>
          <Car className="w-12 h-12 opacity-50" />
        </div>
        <div className="grid grid-cols-3 gap-2 mt-4">
          <div className="bg-white/20 rounded-xl p-2 text-center">
            <p className="text-xl font-bold">{pendingCount}</p>
            <p className="text-xs opacity-80">Pending</p>
          </div>
          <div className="bg-white/20 rounded-xl p-2 text-center">
            <p className="text-xl font-bold">{approvedCount}</p>
            <p className="text-xs opacity-80">Approved</p>
          </div>
          <div className="bg-white/20 rounded-xl p-2 text-center">
            <p className="text-xl font-bold">{totalKm.toFixed(0)}</p>
            <p className="text-xs opacity-80">Total km</p>
          </div>
        </div>
      </div>

      <button 
        onClick={onAddTravel}
        onTouchEnd={(e) => { e.preventDefault(); onAddTravel(); }}
        className="w-full py-4 bg-gradient-to-r from-teal-500 to-cyan-500 text-white rounded-2xl font-semibold shadow-lg flex items-center justify-center gap-2 active:scale-95 transition touch-manipulation cursor-pointer"
        style={{ WebkitTapHighlightColor: 'transparent', touchAction: 'manipulation' }}
        data-testid="add-travel-btn"
      >
        <Plus className="w-5 h-5" />
        New Travel Claim
      </button>

      {/* Travel Rates Info */}
      <div className="bg-white rounded-2xl p-4 shadow-sm border border-zinc-100">
        <h3 className="font-semibold text-zinc-900 mb-3">Reimbursement Rates</h3>
        <div className="grid grid-cols-2 gap-3">
          <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-xl">
            <Car className="w-6 h-6 text-blue-600" />
            <div>
              <p className="font-semibold text-zinc-900">₹7/km</p>
              <p className="text-xs text-zinc-500">Car</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-emerald-50 rounded-xl">
            <Bike className="w-6 h-6 text-emerald-600" />
            <div>
              <p className="font-semibold text-zinc-900">₹3/km</p>
              <p className="text-xs text-zinc-500">Two Wheeler</p>
            </div>
          </div>
        </div>
        <p className="text-xs text-zinc-500 mt-3">
          Cab/Public transport: Submit actual receipt for reimbursement
        </p>
      </div>

      {/* Recent Travel Claims */}
      <div className="bg-white rounded-2xl shadow-sm border border-zinc-100 overflow-hidden">
        <div className="p-4 border-b border-zinc-100">
          <h3 className="font-semibold text-zinc-900">Recent Travel Claims</h3>
        </div>
        {travelClaims.length > 0 ? (
          <div className="divide-y divide-zinc-100">
            {travelClaims.slice(0, 5).map((claim, i) => (
              <div key={i} className="flex items-center gap-3 p-4">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                  claim.status === 'approved' ? 'bg-emerald-100 text-emerald-600' :
                  claim.status === 'pending' ? 'bg-amber-100 text-amber-600' :
                  'bg-red-100 text-red-600'
                }`}>
                  <Car className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <p className="font-medium text-zinc-900 text-sm truncate">
                    {claim.start_location?.name || 'Start'} → {claim.end_location?.name || 'End'}
                  </p>
                  <p className="text-xs text-zinc-500">{claim.travel_date} • {claim.distance_km} km</p>
                </div>
                <div className="text-right">
                  <p className="font-semibold text-zinc-900">₹{(claim.final_amount || 0).toLocaleString()}</p>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    claim.status === 'approved' ? 'bg-emerald-100 text-emerald-700' :
                    claim.status === 'pending' ? 'bg-amber-100 text-amber-700' :
                    'bg-red-100 text-red-700'
                  }`}>{claim.status}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-zinc-500">
            <Car className="w-12 h-12 mx-auto mb-3 text-zinc-300" />
            <p>No travel claims yet</p>
          </div>
        )}
      </div>
    </div>
  );
});

TravelTab.displayName = 'TravelTab';

export default TravelTab;
