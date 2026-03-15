import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Card, CardContent } from './ui/card';
import { Checkbox } from './ui/checkbox';
import { Badge } from './ui/badge';
import { 
  MapPin, Plus, Trash2, Navigation, RotateCcw, Car, 
  Bike, Train, Footprints, Route, Clock, Calculator
} from 'lucide-react';
import { toast } from 'sonner';

const GOOGLE_MAPS_API_KEY = process.env.REACT_APP_GOOGLE_MAPS_API_KEY;

// Travel modes for distance calculation
const TRAVEL_MODES = [
  { id: 'DRIVING', label: 'Car', icon: Car, color: 'text-blue-600' },
  { id: 'TWO_WHEELER', label: 'Bike', icon: Bike, color: 'text-green-600' },
  { id: 'TRANSIT', label: 'Transit', icon: Train, color: 'text-purple-600' },
  { id: 'WALKING', label: 'Walk', icon: Footprints, color: 'text-orange-600' }
];

// Load Google Maps script dynamically
const loadGoogleMapsScript = () => {
  return new Promise((resolve, reject) => {
    if (window.google && window.google.maps) {
      resolve(window.google.maps);
      return;
    }

    const existingScript = document.getElementById('google-maps-script');
    if (existingScript) {
      existingScript.addEventListener('load', () => resolve(window.google.maps));
      return;
    }

    const script = document.createElement('script');
    script.id = 'google-maps-script';
    script.src = `https://maps.googleapis.com/maps/api/js?key=${GOOGLE_MAPS_API_KEY}&libraries=places`;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve(window.google.maps);
    script.onerror = reject;
    document.head.appendChild(script);
  });
};

// Location input with Google Places autocomplete
const LocationInput = ({ value, onChange, placeholder, label, onPlaceSelect, inputRef }) => {
  const autocompleteRef = useRef(null);
  const localInputRef = useRef(null);
  const ref = inputRef || localInputRef;

  useEffect(() => {
    const initAutocomplete = async () => {
      try {
        await loadGoogleMapsScript();
        if (!ref.current || autocompleteRef.current) return;

        autocompleteRef.current = new window.google.maps.places.Autocomplete(ref.current, {
          componentRestrictions: { country: 'in' },
          fields: ['formatted_address', 'geometry', 'name', 'place_id']
        });

        autocompleteRef.current.addListener('place_changed', () => {
          const place = autocompleteRef.current.getPlace();
          if (place && place.geometry) {
            const locationData = {
              address: place.formatted_address || place.name,
              name: place.name,
              placeId: place.place_id,
              lat: place.geometry.location.lat(),
              lng: place.geometry.location.lng()
            };
            onChange(locationData.address);
            onPlaceSelect?.(locationData);
          }
        });
      } catch (error) {
        console.error('Failed to load Google Maps:', error);
      }
    };

    initAutocomplete();
  }, [onChange, onPlaceSelect, ref]);

  return (
    <div className="space-y-1">
      {label && <Label className="text-xs text-zinc-500">{label}</Label>}
      <div className="relative">
        <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
        <Input
          ref={ref}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="pl-9"
          data-testid="location-input"
        />
      </div>
    </div>
  );
};

const MeetingLocationPicker = ({ 
  value = {}, 
  onChange, 
  meetingType = 'Offline',
  disabled = false 
}) => {
  const [startLocation, setStartLocation] = useState(value.startLocation || '');
  const [startLocationData, setStartLocationData] = useState(value.startLocationData || null);
  const [endLocation, setEndLocation] = useState(value.endLocation || '');
  const [endLocationData, setEndLocationData] = useState(value.endLocationData || null);
  const [viaLocations, setViaLocations] = useState(value.viaLocations || []);
  const [isRoundTrip, setIsRoundTrip] = useState(value.isRoundTrip || false);
  const [travelMode, setTravelMode] = useState(value.travelMode || 'DRIVING');
  const [distance, setDistance] = useState(value.distance || null);
  const [duration, setDuration] = useState(value.duration || null);
  const [calculating, setCalculating] = useState(false);
  const [startTime, setStartTime] = useState(value.startTime || '');
  const [endTime, setEndTime] = useState(value.endTime || '');

  // Propagate changes to parent
  useEffect(() => {
    onChange?.({
      startLocation,
      startLocationData,
      endLocation,
      endLocationData,
      viaLocations,
      isRoundTrip,
      travelMode,
      distance,
      duration,
      startTime,
      endTime,
      totalKm: distance ? (isRoundTrip ? distance.value * 2 / 1000 : distance.value / 1000) : 0
    });
  }, [startLocation, startLocationData, endLocation, endLocationData, viaLocations, isRoundTrip, travelMode, distance, duration, startTime, endTime, onChange]);

  // Add via location
  const addViaLocation = () => {
    setViaLocations([...viaLocations, { address: '', data: null }]);
  };

  // Remove via location
  const removeViaLocation = (index) => {
    setViaLocations(viaLocations.filter((_, i) => i !== index));
  };

  // Update via location
  const updateViaLocation = (index, address, data = null) => {
    const updated = [...viaLocations];
    updated[index] = { address, data: data || updated[index].data };
    setViaLocations(updated);
  };

  // Calculate distance using Google Distance Matrix API
  const calculateDistance = useCallback(async () => {
    if (!startLocationData || !endLocationData) {
      toast.error('Please select valid start and end locations');
      return;
    }

    setCalculating(true);
    try {
      await loadGoogleMapsScript();
      const service = new window.google.maps.DistanceMatrixService();
      
      // Build waypoints
      const origin = new window.google.maps.LatLng(startLocationData.lat, startLocationData.lng);
      const destination = new window.google.maps.LatLng(endLocationData.lat, endLocationData.lng);
      
      // If there are via locations, calculate total distance through all points
      let waypoints = [];
      if (viaLocations.length > 0) {
        waypoints = viaLocations
          .filter(v => v.data)
          .map(v => new window.google.maps.LatLng(v.data.lat, v.data.lng));
      }

      // For simplicity with via points, we'll calculate direct distances and sum them
      if (waypoints.length > 0) {
        // Calculate route with waypoints using Directions API
        const directionsService = new window.google.maps.DirectionsService();
        const waypointsForDirections = waypoints.map(wp => ({ location: wp, stopover: true }));
        
        directionsService.route({
          origin: origin,
          destination: destination,
          waypoints: waypointsForDirections,
          travelMode: travelMode === 'TWO_WHEELER' ? 'DRIVING' : travelMode,
          optimizeWaypoints: false
        }, (result, status) => {
          if (status === 'OK') {
            let totalDistance = 0;
            let totalDuration = 0;
            result.routes[0].legs.forEach(leg => {
              totalDistance += leg.distance.value;
              totalDuration += leg.duration.value;
            });
            
            setDistance({
              value: totalDistance,
              text: `${(totalDistance / 1000).toFixed(1)} km`
            });
            setDuration({
              value: totalDuration,
              text: formatDuration(totalDuration)
            });
            toast.success(`Route calculated: ${(totalDistance / 1000).toFixed(1)} km`);
          } else {
            toast.error('Failed to calculate route');
          }
          setCalculating(false);
        });
      } else {
        // Simple origin to destination
        service.getDistanceMatrix({
          origins: [origin],
          destinations: [destination],
          travelMode: travelMode === 'TWO_WHEELER' ? 'DRIVING' : travelMode,
          unitSystem: window.google.maps.UnitSystem.METRIC
        }, (response, status) => {
          if (status === 'OK' && response.rows[0].elements[0].status === 'OK') {
            const element = response.rows[0].elements[0];
            setDistance(element.distance);
            setDuration(element.duration);
            toast.success(`Distance: ${element.distance.text}`);
          } else {
            toast.error('Failed to calculate distance');
          }
          setCalculating(false);
        });
      }
    } catch (error) {
      console.error('Distance calculation error:', error);
      toast.error('Failed to calculate distance');
      setCalculating(false);
    }
  }, [startLocationData, endLocationData, viaLocations, travelMode]);

  // Format duration in hours and minutes
  const formatDuration = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes} min`;
  };

  // Only show for offline meetings
  if (meetingType === 'Online') {
    return null;
  }

  return (
    <Card className="border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-950/20">
      <CardContent className="pt-4 space-y-4">
        <div className="flex items-center gap-2 mb-2">
          <Route className="w-4 h-4 text-blue-600" />
          <span className="text-sm font-medium text-blue-800 dark:text-blue-300">Meeting Travel Details</span>
          <Badge variant="outline" className="text-xs bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300">
            Offline Meeting
          </Badge>
        </div>

        {/* Travel Time */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label className="text-xs text-zinc-500">Start Time</Label>
            <Input
              type="time"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
              disabled={disabled}
              className="h-9"
            />
          </div>
          <div>
            <Label className="text-xs text-zinc-500">End Time</Label>
            <Input
              type="time"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
              disabled={disabled}
              className="h-9"
            />
          </div>
        </div>

        {/* Start Location */}
        <LocationInput
          label="Start Location (From)"
          value={startLocation}
          onChange={setStartLocation}
          onPlaceSelect={setStartLocationData}
          placeholder="Search start location..."
        />

        {/* Via Locations */}
        {viaLocations.map((via, index) => (
          <div key={index} className="flex items-end gap-2">
            <div className="flex-1">
              <LocationInput
                label={`Via Location ${index + 1}`}
                value={via.address}
                onChange={(addr) => updateViaLocation(index, addr)}
                onPlaceSelect={(data) => updateViaLocation(index, data.address, data)}
                placeholder="Search via location..."
              />
            </div>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => removeViaLocation(index)}
              className="text-red-500 hover:text-red-600 hover:bg-red-50 h-9 w-9"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        ))}

        {/* Add Via Location Button */}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={addViaLocation}
          disabled={disabled}
          className="w-full border-dashed text-blue-600 hover:text-blue-700 hover:bg-blue-50 dark:hover:bg-blue-950"
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Via Location
        </Button>

        {/* End Location */}
        <LocationInput
          label="End Location (To)"
          value={endLocation}
          onChange={setEndLocation}
          onPlaceSelect={setEndLocationData}
          placeholder="Search end location..."
        />

        {/* Travel Mode Selection */}
        <div>
          <Label className="text-xs text-zinc-500 mb-2 block">Mode of Travel</Label>
          <div className="flex gap-2 flex-wrap">
            {TRAVEL_MODES.map((mode) => {
              const Icon = mode.icon;
              const isSelected = travelMode === mode.id;
              return (
                <Button
                  key={mode.id}
                  type="button"
                  variant={isSelected ? "default" : "outline"}
                  size="sm"
                  onClick={() => setTravelMode(mode.id)}
                  disabled={disabled}
                  className={isSelected ? 'bg-blue-600 hover:bg-blue-700' : ''}
                >
                  <Icon className={`w-4 h-4 mr-1 ${isSelected ? 'text-white' : mode.color}`} />
                  {mode.label}
                </Button>
              );
            })}
          </div>
        </div>

        {/* Round Trip Toggle */}
        <div className="flex items-center gap-3 p-3 bg-white dark:bg-zinc-900 rounded-lg border">
          <Checkbox
            id="round-trip"
            checked={isRoundTrip}
            onCheckedChange={setIsRoundTrip}
            disabled={disabled}
          />
          <Label htmlFor="round-trip" className="flex items-center gap-2 cursor-pointer text-sm">
            <RotateCcw className="w-4 h-4 text-purple-600" />
            Round Trip (Return journey)
          </Label>
        </div>

        {/* Calculate Distance Button */}
        <Button
          type="button"
          onClick={calculateDistance}
          disabled={disabled || calculating || !startLocation || !endLocation}
          className="w-full bg-blue-600 hover:bg-blue-700"
        >
          {calculating ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2" />
              Calculating...
            </>
          ) : (
            <>
              <Calculator className="w-4 h-4 mr-2" />
              Calculate Distance
            </>
          )}
        </Button>

        {/* Distance Results */}
        {distance && (
          <div className="p-4 bg-green-50 dark:bg-green-950/30 rounded-lg border border-green-200 dark:border-green-800">
            <div className="grid grid-cols-2 gap-4 text-center">
              <div>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">One Way</p>
                <p className="text-lg font-bold text-green-700 dark:text-green-400">{distance.text}</p>
              </div>
              {isRoundTrip && (
                <div>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400">Round Trip</p>
                  <p className="text-lg font-bold text-purple-700 dark:text-purple-400">
                    {(distance.value * 2 / 1000).toFixed(1)} km
                  </p>
                </div>
              )}
            </div>
            {duration && (
              <div className="mt-3 pt-3 border-t border-green-200 dark:border-green-700 text-center">
                <p className="text-xs text-zinc-500 dark:text-zinc-400 flex items-center justify-center gap-1">
                  <Clock className="w-3 h-3" />
                  Estimated Travel Time
                </p>
                <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  {duration.text} {isRoundTrip && `(${formatDuration(duration.value * 2)} round trip)`}
                </p>
              </div>
            )}
            <div className="mt-3 pt-3 border-t border-green-200 dark:border-green-700">
              <p className="text-xs text-zinc-500 dark:text-zinc-400 text-center">
                Total KM for Expense Claim: <span className="font-bold text-green-700 dark:text-green-400">
                  {isRoundTrip ? (distance.value * 2 / 1000).toFixed(1) : (distance.value / 1000).toFixed(1)} km
                </span>
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default MeetingLocationPicker;
