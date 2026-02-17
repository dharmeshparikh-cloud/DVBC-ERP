import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { 
  Building2, MapPin, Plus, Trash2, Edit2, Save, X, 
  Navigation, Loader2, CheckCircle, AlertCircle
} from 'lucide-react';
import { toast } from 'sonner';

const OfficeLocationsSettings = () => {
  const [locations, setLocations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [editingIndex, setEditingIndex] = useState(null);
  const [newLocation, setNewLocation] = useState({
    name: '',
    address: '',
    latitude: '',
    longitude: ''
  });
  const [detectingLocation, setDetectingLocation] = useState(false);

  useEffect(() => {
    fetchLocations();
  }, []);

  const fetchLocations = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/settings/office-locations`);
      setLocations(res.data.locations || []);
    } catch (error) {
      console.error('Failed to fetch locations');
    } finally {
      setLoading(false);
    }
  };

  const saveLocations = async () => {
    setSaving(true);
    try {
      await axios.post(`${API}/settings/office-locations`, { locations });
      toast.success('Office locations saved successfully');
    } catch (error) {
      toast.error('Failed to save locations');
    } finally {
      setSaving(false);
    }
  };

  const detectCurrentLocation = () => {
    setDetectingLocation(true);
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        
        // Reverse geocode for address
        try {
          const response = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`
          );
          const data = await response.json();
          setNewLocation(prev => ({
            ...prev,
            latitude: lat.toFixed(6),
            longitude: lon.toFixed(6),
            address: data.display_name || ''
          }));
        } catch (e) {
          setNewLocation(prev => ({
            ...prev,
            latitude: lat.toFixed(6),
            longitude: lon.toFixed(6)
          }));
        }
        setDetectingLocation(false);
      },
      (error) => {
        toast.error('Unable to detect location. Please enter manually.');
        setDetectingLocation(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const addLocation = () => {
    if (!newLocation.name || !newLocation.latitude || !newLocation.longitude) {
      toast.error('Please fill in all required fields');
      return;
    }
    
    const locationToAdd = {
      name: newLocation.name,
      address: newLocation.address,
      latitude: parseFloat(newLocation.latitude),
      longitude: parseFloat(newLocation.longitude)
    };
    
    if (editingIndex !== null) {
      const updated = [...locations];
      updated[editingIndex] = locationToAdd;
      setLocations(updated);
    } else {
      setLocations([...locations, locationToAdd]);
    }
    
    setShowAddDialog(false);
    setNewLocation({ name: '', address: '', latitude: '', longitude: '' });
    setEditingIndex(null);
  };

  const editLocation = (index) => {
    const loc = locations[index];
    setNewLocation({
      name: loc.name,
      address: loc.address || '',
      latitude: loc.latitude.toString(),
      longitude: loc.longitude.toString()
    });
    setEditingIndex(index);
    setShowAddDialog(true);
  };

  const deleteLocation = (index) => {
    const updated = locations.filter((_, i) => i !== index);
    setLocations(updated);
  };

  return (
    <div data-testid="office-locations-settings">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 dark:text-zinc-100 mb-2">
            Office Locations
          </h1>
          <p className="text-zinc-500 dark:text-zinc-400">
            Configure office locations for attendance geofencing (500m radius)
          </p>
        </div>
        <div className="flex gap-3">
          <Button 
            variant="outline" 
            onClick={() => setShowAddDialog(true)}
            className="rounded-sm"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Location
          </Button>
          <Button 
            onClick={saveLocations}
            disabled={saving}
            className="rounded-sm bg-emerald-600 hover:bg-emerald-700"
          >
            {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
            Save Changes
          </Button>
        </div>
      </div>

      {/* Info Card */}
      <Card className="border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20 shadow-none rounded-sm mb-6">
        <CardContent className="p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5" />
          <div>
            <p className="font-medium text-blue-900 dark:text-blue-100">Geofencing Enabled</p>
            <p className="text-sm text-blue-700 dark:text-blue-300">
              Employees checking in within 500 meters of these locations will be auto-approved. 
              Check-ins from other locations require HR approval with justification.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Locations List */}
      <Card className="border-zinc-200 dark:border-zinc-700 shadow-none rounded-sm">
        <CardHeader className="border-b border-zinc-200 dark:border-zinc-700 py-4">
          <CardTitle className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
            <Building2 className="w-5 h-5" />
            Configured Locations ({locations.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center h-40">
              <Loader2 className="w-6 h-6 animate-spin text-zinc-400" />
            </div>
          ) : locations.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 text-zinc-500">
              <MapPin className="w-12 h-12 text-zinc-300 mb-3" />
              <p>No office locations configured</p>
              <p className="text-sm">Add locations to enable geofencing</p>
            </div>
          ) : (
            <div className="divide-y divide-zinc-200 dark:divide-zinc-700">
              {locations.map((loc, index) => (
                <div key={index} className="flex items-center gap-4 p-4 hover:bg-zinc-50 dark:hover:bg-zinc-800/50">
                  <div className="w-12 h-12 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                    <Building2 className="w-6 h-6 text-blue-600" />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-zinc-900 dark:text-zinc-100">{loc.name}</p>
                    <p className="text-sm text-zinc-500 dark:text-zinc-400">{loc.address || 'No address'}</p>
                    <p className="text-xs text-zinc-400 mt-1">
                      {loc.latitude}, {loc.longitude}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="ghost" size="sm" onClick={() => editLocation(index)}>
                      <Edit2 className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="sm" className="text-red-600" onClick={() => deleteLocation(index)}>
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Add/Edit Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent className="max-w-md border-zinc-200 dark:border-zinc-700 rounded-lg">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
              {editingIndex !== null ? 'Edit Location' : 'Add Office Location'}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 mt-4">
            <div>
              <Label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Location Name *</Label>
              <Input
                value={newLocation.name}
                onChange={(e) => setNewLocation({ ...newLocation, name: e.target.value })}
                placeholder="e.g., Main Office, Bangalore HQ"
                className="rounded-sm border-zinc-200 dark:border-zinc-700 mt-1"
              />
            </div>

            <div>
              <Label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Address</Label>
              <Input
                value={newLocation.address}
                onChange={(e) => setNewLocation({ ...newLocation, address: e.target.value })}
                placeholder="Full address"
                className="rounded-sm border-zinc-200 dark:border-zinc-700 mt-1"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Latitude *</Label>
                <Input
                  type="number"
                  step="0.000001"
                  value={newLocation.latitude}
                  onChange={(e) => setNewLocation({ ...newLocation, latitude: e.target.value })}
                  placeholder="12.9716"
                  className="rounded-sm border-zinc-200 dark:border-zinc-700 mt-1"
                />
              </div>
              <div>
                <Label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Longitude *</Label>
                <Input
                  type="number"
                  step="0.000001"
                  value={newLocation.longitude}
                  onChange={(e) => setNewLocation({ ...newLocation, longitude: e.target.value })}
                  placeholder="77.5946"
                  className="rounded-sm border-zinc-200 dark:border-zinc-700 mt-1"
                />
              </div>
            </div>

            <Button
              variant="outline"
              onClick={detectCurrentLocation}
              disabled={detectingLocation}
              className="w-full rounded-sm"
            >
              {detectingLocation ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Detecting...</>
              ) : (
                <><Navigation className="w-4 h-4 mr-2" /> Use Current Location</>
              )}
            </Button>
          </div>

          <DialogFooter className="flex gap-3 mt-6">
            <Button 
              variant="outline" 
              onClick={() => { setShowAddDialog(false); setEditingIndex(null); setNewLocation({ name: '', address: '', latitude: '', longitude: '' }); }}
              className="rounded-sm"
            >
              Cancel
            </Button>
            <Button 
              onClick={addLocation}
              className="rounded-sm bg-zinc-900 hover:bg-zinc-800"
            >
              {editingIndex !== null ? 'Update' : 'Add'} Location
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default OfficeLocationsSettings;
