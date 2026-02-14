import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { 
  User, Mail, Phone, Building, Briefcase, Shield, 
  Check, X, Edit2, Save, Eye, EyeOff
} from 'lucide-react';
import { toast } from 'sonner';

const UserProfile = () => {
  const { user, setUser } = useContext(AuthContext);
  const [profile, setProfile] = useState(null);
  const [permissions, setPermissions] = useState({});
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [showPermissions, setShowPermissions] = useState(false);
  
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    phone: '',
    department: '',
    designation: '',
    bio: ''
  });

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const [profileRes, permissionsRes] = await Promise.all([
        axios.get(`${API}/users/me`),
        axios.get(`${API}/users/me/permissions`)
      ]);
      
      setProfile(profileRes.data);
      setPermissions(permissionsRes.data);
      setFormData({
        full_name: profileRes.data.full_name || '',
        email: profileRes.data.email || '',
        phone: profileRes.data.phone || '',
        department: profileRes.data.department || '',
        designation: profileRes.data.designation || '',
        bio: profileRes.data.bio || ''
      });
    } catch (error) {
      toast.error('Failed to load profile');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      await axios.patch(`${API}/users/me`, formData);
      toast.success('Profile updated successfully');
      setEditing(false);
      fetchProfile();
      
      // Update context if name changed
      if (formData.full_name !== user.full_name) {
        setUser({ ...user, full_name: formData.full_name });
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update profile');
    }
  };

  const getRoleBadgeColor = (role) => {
    const colors = {
      admin: 'bg-red-100 text-red-700',
      manager: 'bg-blue-100 text-blue-700',
      executive: 'bg-emerald-100 text-emerald-700',
      consultant: 'bg-purple-100 text-purple-700',
      principal_consultant: 'bg-amber-100 text-amber-700',
      project_manager: 'bg-cyan-100 text-cyan-700'
    };
    return colors[role] || 'bg-zinc-100 text-zinc-700';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-zinc-500">Loading...</div>
      </div>
    );
  }

  return (
    <div data-testid="user-profile-page">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
          My Profile
        </h1>
        <p className="text-zinc-500">Manage your account settings and permissions</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Profile Card */}
        <div className="lg:col-span-2">
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-4">
              <CardTitle className="text-lg font-semibold uppercase tracking-tight text-zinc-950">
                Profile Information
              </CardTitle>
              <Button
                onClick={() => editing ? handleSave() : setEditing(true)}
                variant={editing ? "default" : "outline"}
                size="sm"
                className={editing ? "bg-zinc-950 text-white" : ""}
              >
                {editing ? (
                  <>
                    <Save className="w-4 h-4 mr-2" />
                    Save
                  </>
                ) : (
                  <>
                    <Edit2 className="w-4 h-4 mr-2" />
                    Edit
                  </>
                )}
              </Button>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Avatar and Role */}
              <div className="flex items-center gap-4 pb-6 border-b border-zinc-200">
                <div className="w-20 h-20 rounded-full bg-zinc-200 flex items-center justify-center">
                  <User className="w-10 h-10 text-zinc-400" strokeWidth={1.5} />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-zinc-950">{profile?.full_name}</h2>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`px-2 py-1 text-xs font-medium rounded-sm capitalize ${getRoleBadgeColor(profile?.role)}`}>
                      {profile?.role?.replace('_', ' ')}
                    </span>
                    {profile?.department && (
                      <span className="text-sm text-zinc-500">{profile.department}</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Form Fields */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <User className="w-4 h-4 text-zinc-400" />
                    Full Name
                  </Label>
                  {editing ? (
                    <Input
                      value={formData.full_name}
                      onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                      className="rounded-sm"
                    />
                  ) : (
                    <p className="text-zinc-700 py-2">{profile?.full_name || '-'}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Mail className="w-4 h-4 text-zinc-400" />
                    Email
                  </Label>
                  {editing ? (
                    <Input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      className="rounded-sm"
                    />
                  ) : (
                    <p className="text-zinc-700 py-2">{profile?.email || '-'}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Phone className="w-4 h-4 text-zinc-400" />
                    Phone
                  </Label>
                  {editing ? (
                    <Input
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      placeholder="+91 XXXXX XXXXX"
                      className="rounded-sm"
                    />
                  ) : (
                    <p className="text-zinc-700 py-2">{profile?.phone || '-'}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Building className="w-4 h-4 text-zinc-400" />
                    Department
                  </Label>
                  {editing ? (
                    <Input
                      value={formData.department}
                      onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                      className="rounded-sm"
                    />
                  ) : (
                    <p className="text-zinc-700 py-2">{profile?.department || '-'}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Briefcase className="w-4 h-4 text-zinc-400" />
                    Designation
                  </Label>
                  {editing ? (
                    <Input
                      value={formData.designation}
                      onChange={(e) => setFormData({ ...formData, designation: e.target.value })}
                      className="rounded-sm"
                    />
                  ) : (
                    <p className="text-zinc-700 py-2">{profile?.designation || '-'}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-zinc-400" />
                    Role
                  </Label>
                  <p className="text-zinc-700 py-2 capitalize">{profile?.role?.replace('_', ' ') || '-'}</p>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Bio</Label>
                {editing ? (
                  <textarea
                    value={formData.bio}
                    onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                    rows={3}
                    placeholder="A brief description about yourself..."
                    className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950"
                  />
                ) : (
                  <p className="text-zinc-700 py-2">{profile?.bio || 'No bio added'}</p>
                )}
              </div>

              {editing && (
                <div className="flex justify-end gap-3 pt-4 border-t border-zinc-200">
                  <Button
                    onClick={() => {
                      setEditing(false);
                      setFormData({
                        full_name: profile?.full_name || '',
                        email: profile?.email || '',
                        phone: profile?.phone || '',
                        department: profile?.department || '',
                        designation: profile?.designation || '',
                        bio: profile?.bio || ''
                      });
                    }}
                    variant="outline"
                    className="rounded-sm"
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleSave}
                    className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
                  >
                    Save Changes
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Permissions Card */}
        <div className="lg:col-span-1">
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-4">
              <CardTitle className="text-lg font-semibold uppercase tracking-tight text-zinc-950">
                My Permissions
              </CardTitle>
              <Button
                onClick={() => setShowPermissions(!showPermissions)}
                variant="ghost"
                size="sm"
              >
                {showPermissions ? (
                  <EyeOff className="w-4 h-4" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
              </Button>
            </CardHeader>
            <CardContent>
              {showPermissions ? (
                <div className="space-y-4">
                  {Object.entries(permissions).map(([module, perms]) => (
                    <div key={module} className="pb-4 border-b border-zinc-100 last:border-0">
                      <h4 className="font-medium text-zinc-950 capitalize mb-2">
                        {module.replace('_', ' ')}
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(perms).map(([action, allowed]) => (
                          <div
                            key={action}
                            className={`flex items-center gap-1 text-xs px-2 py-1 rounded-sm ${
                              allowed ? 'bg-emerald-50 text-emerald-700' : 'bg-zinc-100 text-zinc-400'
                            }`}
                          >
                            {allowed ? (
                              <Check className="w-3 h-3" />
                            ) : (
                              <X className="w-3 h-3" />
                            )}
                            <span className="capitalize">{action}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-zinc-500">
                  <Shield className="w-12 h-12 mx-auto mb-4 text-zinc-300" strokeWidth={1} />
                  <p className="text-sm">Click the eye icon to view your permissions</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Account Info */}
          <Card className="border-zinc-200 shadow-none rounded-sm mt-6">
            <CardHeader className="pb-4">
              <CardTitle className="text-lg font-semibold uppercase tracking-tight text-zinc-950">
                Account Info
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-zinc-500">User ID</span>
                <span className="text-zinc-700 font-mono text-xs">{profile?.id?.substring(0, 8)}...</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">Status</span>
                <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded-sm text-xs">Active</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">Member Since</span>
                <span className="text-zinc-700">
                  {profile?.created_at ? new Date(profile.created_at).toLocaleDateString() : '-'}
                </span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default UserProfile;
