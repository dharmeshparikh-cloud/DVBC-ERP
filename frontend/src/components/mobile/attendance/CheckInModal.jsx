/**
 * CheckInModal - Check-in Modal with Selfie and Location Capture
 */

import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../ui/dialog';
import { Button } from '../../ui/button';
import { 
  Camera, MapPin, Loader2, X, RotateCcw, 
  Building2, Home, Briefcase, CheckCircle 
} from 'lucide-react';

const LocationOption = ({ id, icon: Icon, label, selected, onClick }) => (
  <button
    onClick={() => onClick(id)}
    className={`flex-1 p-3 rounded-lg border-2 transition-all ${
      selected 
        ? 'border-orange-500 bg-orange-50' 
        : 'border-zinc-200 hover:border-zinc-300'
    }`}
    data-testid={`location-${id}`}
  >
    <Icon className={`w-6 h-6 mx-auto mb-1 ${selected ? 'text-orange-500' : 'text-zinc-400'}`} />
    <p className={`text-xs ${selected ? 'text-orange-700 font-medium' : 'text-zinc-500'}`}>{label}</p>
  </button>
);

export const CheckInModal = ({
  open,
  onOpenChange,
  // Location
  location,
  locationLoading,
  onCaptureLocation,
  // Selfie
  selfieData,
  showCamera,
  videoRef,
  canvasRef,
  onStartCamera,
  onCaptureSelfie,
  onRetakeSelfie,
  // Work location
  selectedWorkLocation,
  onSelectWorkLocation,
  // Client selection for onsite
  assignedClients = [],
  selectedClient,
  onSelectClient,
  loadingClients,
  // Justification
  showJustification,
  justification,
  onJustificationChange,
  locationValidation,
  // Actions
  onCheckIn,
  loading
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-orange-500" />
            Check In
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Work Location Selection */}
          <div>
            <label className="text-sm font-medium text-zinc-700 mb-2 block">
              Work Location
            </label>
            <div className="flex gap-2">
              <LocationOption 
                id="in_office" 
                icon={Building2} 
                label="Office" 
                selected={selectedWorkLocation === 'in_office'}
                onClick={onSelectWorkLocation}
              />
              <LocationOption 
                id="work_from_home" 
                icon={Home} 
                label="WFH" 
                selected={selectedWorkLocation === 'work_from_home'}
                onClick={onSelectWorkLocation}
              />
              <LocationOption 
                id="onsite" 
                icon={Briefcase} 
                label="On-Site" 
                selected={selectedWorkLocation === 'onsite'}
                onClick={onSelectWorkLocation}
              />
            </div>
          </div>

          {/* Client Selection for Onsite */}
          {selectedWorkLocation === 'onsite' && (
            <div>
              <label className="text-sm font-medium text-zinc-700 mb-2 block">
                Select Client
              </label>
              {loadingClients ? (
                <div className="flex items-center justify-center p-4">
                  <Loader2 className="w-5 h-5 animate-spin text-zinc-400" />
                </div>
              ) : assignedClients.length > 0 ? (
                <select
                  value={selectedClient?.id || ''}
                  onChange={(e) => {
                    const client = assignedClients.find(c => c.id === e.target.value);
                    onSelectClient(client);
                  }}
                  className="w-full p-2 border rounded-lg text-sm"
                  data-testid="client-select"
                >
                  <option value="">Select a client...</option>
                  {assignedClients.map(client => (
                    <option key={client.id} value={client.id}>
                      {client.client_name} {client.project_name ? `- ${client.project_name}` : ''}
                    </option>
                  ))}
                </select>
              ) : (
                <p className="text-sm text-zinc-500 p-2 bg-zinc-50 rounded-lg">
                  No clients assigned. Contact your manager.
                </p>
              )}
            </div>
          )}

          {/* GPS Location */}
          <div>
            <label className="text-sm font-medium text-zinc-700 mb-2 block">
              GPS Location
            </label>
            {location ? (
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
                <div className="flex items-center gap-2 text-emerald-700">
                  <MapPin className="w-4 h-4" />
                  <span className="text-sm font-medium">Location Captured</span>
                </div>
                {location.address && (
                  <p className="text-xs text-emerald-600 mt-1 line-clamp-2">
                    {location.address}
                  </p>
                )}
              </div>
            ) : (
              <Button
                variant="outline"
                onClick={onCaptureLocation}
                disabled={locationLoading}
                className="w-full"
              >
                {locationLoading ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <MapPin className="w-4 h-4 mr-2" />
                )}
                {locationLoading ? 'Getting Location...' : 'Capture Location'}
              </Button>
            )}
          </div>

          {/* Selfie Capture */}
          <div>
            <label className="text-sm font-medium text-zinc-700 mb-2 block">
              Selfie Verification
            </label>
            {selfieData ? (
              <div className="relative">
                <img 
                  src={selfieData} 
                  alt="Selfie" 
                  className="w-full rounded-lg border"
                />
                <Button
                  size="sm"
                  variant="outline"
                  onClick={onRetakeSelfie}
                  className="absolute bottom-2 right-2 bg-white"
                >
                  <RotateCcw className="w-4 h-4 mr-1" /> Retake
                </Button>
              </div>
            ) : showCamera ? (
              <div className="relative">
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-full rounded-lg border bg-black"
                />
                <canvas ref={canvasRef} className="hidden" />
                <Button
                  onClick={onCaptureSelfie}
                  className="absolute bottom-2 left-1/2 transform -translate-x-1/2 bg-orange-500 hover:bg-orange-600"
                >
                  <Camera className="w-4 h-4 mr-1" /> Capture
                </Button>
              </div>
            ) : (
              <Button
                variant="outline"
                onClick={onStartCamera}
                className="w-full"
              >
                <Camera className="w-4 h-4 mr-2" /> Open Camera
              </Button>
            )}
          </div>

          {/* Location Justification */}
          {showJustification && (
            <div>
              <label className="text-sm font-medium text-amber-700 mb-2 block">
                Location Not Verified - Justification Required
              </label>
              {locationValidation?.reason && (
                <p className="text-xs text-amber-600 mb-2">{locationValidation.reason}</p>
              )}
              <textarea
                value={justification}
                onChange={(e) => onJustificationChange(e.target.value)}
                placeholder="Please explain why you're checking in from this location..."
                className="w-full p-2 border border-amber-300 rounded-lg text-sm resize-none"
                rows={3}
              />
            </div>
          )}

          {/* Submit Button */}
          <Button
            onClick={onCheckIn}
            disabled={!selfieData || !location || loading || (selectedWorkLocation === 'onsite' && !selectedClient)}
            className="w-full bg-orange-500 hover:bg-orange-600"
            data-testid="confirm-checkin-btn"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <CheckCircle className="w-4 h-4 mr-2" />
            )}
            {loading ? 'Checking In...' : 'Confirm Check In'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default CheckInModal;
