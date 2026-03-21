/**
 * ProfilePhotoUpload Component
 * 
 * Passport-size photo upload for:
 * - Print forms (offer letters, ID cards, official documents)
 * - UI avatar display
 * 
 * Reuses existing UI components:
 * - Avatar, AvatarImage, AvatarFallback
 * - Button
 * - Label
 */

import React, { useState, useRef } from 'react';
import { Avatar, AvatarImage, AvatarFallback } from './ui/avatar';
import { Button } from './ui/button';
import { Label } from './ui/label';
import { Camera, Upload, X, User, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

const ProfilePhotoUpload = ({ 
  employeeId,
  currentPhotoUrl,
  fallbackInitials = '?',
  onUploadSuccess,
  onRemoveSuccess,
  onPhotoChange, // Callback when photo URL changes (for onboarding form)
  uploadEndpoint, // Custom upload endpoint (for onboarding form)
  size = 'lg', // sm, md, lg, xl
  editable = true,
  showLabel = true,
  className = ''
}) => {
  const [isUploading, setIsUploading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(currentPhotoUrl);
  const fileInputRef = useRef(null);

  // Size configurations matching existing design tokens
  const sizeClasses = {
    sm: 'h-10 w-10',
    md: 'h-16 w-16',
    lg: 'h-24 w-24',
    xl: 'h-32 w-32'
  };

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Please upload a JPEG, PNG, or WebP image');
      return;
    }

    // Validate file size (5MB max for print quality)
    if (file.size > 5 * 1024 * 1024) {
      toast.error('File too large. Maximum size: 5MB');
      return;
    }

    // Show preview immediately
    const reader = new FileReader();
    reader.onload = (e) => setPreviewUrl(e.target.result);
    reader.readAsDataURL(file);

    // Upload to server
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      // Use custom endpoint if provided (for onboarding), otherwise use employee endpoint
      const endpoint = uploadEndpoint || `${API}/employees/${employeeId}/photo`;
      
      const response = await axios.post(
        endpoint,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );

      toast.success('Photo uploaded successfully');
      const photoUrl = response.data.profile_photo_url || response.data.photo_url;
      setPreviewUrl(photoUrl);
      
      // Call appropriate callback
      if (onPhotoChange) {
        onPhotoChange(photoUrl);
      }
      onUploadSuccess?.(response.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload photo');
      setPreviewUrl(currentPhotoUrl); // Revert preview
    } finally {
      setIsUploading(false);
    }
  };

  const handleRemove = async () => {
    if (!previewUrl) return;

    setIsUploading(true);
    try {
      await axios.delete(`${API}/employees/${employeeId}/photo`);
      toast.success('Photo removed');
      setPreviewUrl(null);
      onRemoveSuccess?.();
    } catch (error) {
      toast.error('Failed to remove photo');
    } finally {
      setIsUploading(false);
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className={`flex flex-col items-center gap-3 ${className}`}>
      {showLabel && (
        <Label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
          Passport Photo
        </Label>
      )}

      {/* Avatar with photo or fallback */}
      <div className="relative group">
        <Avatar className={`${sizeClasses[size]} border-2 border-zinc-200 dark:border-zinc-700`}>
          {previewUrl ? (
            <AvatarImage 
              src={previewUrl} 
              alt="Profile" 
              className="object-cover"
            />
          ) : (
            <AvatarFallback className="bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 text-lg font-medium">
              {fallbackInitials || <User className="h-6 w-6" />}
            </AvatarFallback>
          )}
        </Avatar>

        {/* Upload overlay on hover (if editable) */}
        {editable && !isUploading && (
          <div 
            onClick={triggerFileInput}
            className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-full opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
          >
            <Camera className="h-6 w-6 text-white" />
          </div>
        )}

        {/* Loading overlay */}
        {isUploading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-full">
            <Loader2 className="h-6 w-6 text-white animate-spin" />
          </div>
        )}
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* Action buttons (if editable) */}
      {editable && (
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={triggerFileInput}
            disabled={isUploading}
            className="text-xs"
          >
            <Upload className="h-3 w-3 mr-1" />
            {previewUrl ? 'Change' : 'Upload'}
          </Button>
          
          {previewUrl && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleRemove}
              disabled={isUploading}
              className="text-xs text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950"
            >
              <X className="h-3 w-3 mr-1" />
              Remove
            </Button>
          )}
        </div>
      )}

      {/* Helper text */}
      {editable && showLabel && (
        <p className="text-xs text-zinc-500 dark:text-zinc-400 text-center max-w-[200px]">
          Passport size photo (JPEG/PNG, max 5MB)
          <br />
          <span className="text-zinc-400 dark:text-zinc-500">Used in print forms & profile</span>
        </p>
      )}
    </div>
  );
};

export default ProfilePhotoUpload;
