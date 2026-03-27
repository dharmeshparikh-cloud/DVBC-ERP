/**
 * ProfilePerformanceCard Component
 * 
 * Combines employee profile with quick performance stats.
 * Design: Option 6 (Profile Performance Hub) + Focus Stream elements
 * 
 * Reuses existing components:
 * - Card, CardContent, CardHeader
 * - Avatar, AvatarImage, AvatarFallback
 * - Badge
 * - Progress
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent } from './ui/card';
import { Avatar, AvatarImage, AvatarFallback } from './ui/avatar';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { 
  TrendingUp, TrendingDown, Target, DollarSign, 
  Users, Calendar, Award, Briefcase
} from 'lucide-react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

const ProfilePerformanceCard = ({
  user,
  employee,
  stats = {},
  showDetailedStats = true,
  variant = 'default', // default, compact, expanded
  className = ''
}) => {
  const [photoUrl, setPhotoUrl] = useState(null);
  
  // Fetch photo from API on mount
  useEffect(() => {
    const fetchPhoto = async () => {
      const employeeId = user?.employee_id || employee?.employee_id;
      if (!employeeId) return;
      
      try {
        const response = await axios.get(`${API}/api/employees/${employeeId}/photo`);
        if (response.data?.profile_photo_url) {
          setPhotoUrl(response.data.profile_photo_url);
        }
      } catch (error) {
        // Photo not found or error - use fallback
        console.debug('No profile photo found:', error.response?.status);
      }
    };
    
    // Check if photo already exists in props
    const existingPhoto = employee?.profile_photo_url || employee?.avatar_url || user?.profile_photo_url;
    if (existingPhoto) {
      setPhotoUrl(existingPhoto);
    } else {
      fetchPhoto();
    }
  }, [user?.employee_id, employee?.employee_id, employee?.profile_photo_url, employee?.avatar_url, user?.profile_photo_url]);

  // Extract user/employee data with fallbacks
  const name = user?.full_name || `${employee?.first_name || ''} ${employee?.last_name || ''}`.trim() || 'User';
  const role = employee?.designation || user?.role || 'Employee';
  const department = employee?.department || user?.department || '';
  const initials = name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);

  // Performance stats with defaults
  const {
    dealsWon = 0,
    dealsInProgress = 0,
    revenue = 0,
    conversionRate = 0,
    targetAchievement = 0,
    momCompliance = 0,
    trend = 'up', // up, down, stable
    followUps = { total: 0, open: 0, closed: 0, overdue: 0 },
    meetingsAchieved = 0
  } = stats;

  // Format currency
  const formatCurrency = (amount) => {
    if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(1)}Cr`;
    if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
    if (amount >= 1000) return `₹${(amount / 1000).toFixed(1)}K`;
    return `₹${amount}`;
  };

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Target;
  const trendColor = trend === 'up' ? 'text-green-500' : trend === 'down' ? 'text-red-500' : 'text-zinc-500';

  if (variant === 'compact') {
    return (
      <Card className={`bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800 ${className}`}>
        <CardContent className="p-4">
          <div className="flex items-center gap-4">
            {/* Avatar */}
            <Avatar className="h-12 w-12 border-2 border-zinc-200 dark:border-zinc-700">
              {photoUrl ? (
                <AvatarImage src={photoUrl} alt={name} className="object-cover" />
              ) : (
                <AvatarFallback className="bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 font-medium">
                  {initials}
                </AvatarFallback>
              )}
            </Avatar>

            {/* Name & Role */}
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-zinc-900 dark:text-zinc-100 truncate">{name}</h3>
              <p className="text-sm text-zinc-500 dark:text-zinc-400 truncate">{role}</p>
            </div>

            {/* Quick Stats */}
            <div className="flex gap-4 text-center">
              <div>
                <p className="text-lg font-bold text-zinc-900 dark:text-zinc-100">{dealsWon}</p>
                <p className="text-xs text-zinc-500">Won</p>
              </div>
              <div>
                <p className="text-lg font-bold text-zinc-900 dark:text-zinc-100">{formatCurrency(revenue)}</p>
                <p className="text-xs text-zinc-500">Revenue</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={`bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800 ${className}`}>
      <CardContent className="p-6">
        <div className="flex flex-col md:flex-row gap-6">
          {/* Left: Profile Section */}
          <div className="flex flex-col items-center md:items-start gap-3 md:min-w-[200px]">
            {/* Avatar with status */}
            <div className="relative">
              <Avatar className="h-20 w-20 border-3 border-zinc-200 dark:border-zinc-700">
                {photoUrl ? (
                  <AvatarImage src={photoUrl} alt={name} className="object-cover" />
                ) : (
                  <AvatarFallback className="bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 text-xl font-medium">
                    {initials}
                  </AvatarFallback>
                )}
              </Avatar>
              {/* Online indicator */}
              <span className="absolute bottom-1 right-1 h-4 w-4 rounded-full bg-green-500 border-2 border-white dark:border-zinc-900" />
            </div>

            {/* Name & Details */}
            <div className="text-center md:text-left">
              <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">{name}</h2>
              <p className="text-sm text-zinc-600 dark:text-zinc-400">{role}</p>
              {department && (
                <Badge variant="secondary" className="mt-1 text-xs">
                  {department}
                </Badge>
              )}
            </div>

            {/* Trend indicator */}
            <div className={`flex items-center gap-1 ${trendColor}`}>
              <TrendIcon className="h-4 w-4" />
              <span className="text-sm font-medium">
                {trend === 'up' ? 'Trending Up' : trend === 'down' ? 'Needs Attention' : 'Stable'}
              </span>
            </div>
          </div>

          {/* Right: Stats Section */}
          {showDetailedStats && (
            <div className="flex-1 grid grid-cols-3 md:grid-cols-6 gap-4">
              {/* Deals Won */}
              <div className="bg-zinc-50 dark:bg-zinc-800/50 rounded-lg p-4 text-center">
                <div className="flex items-center justify-center mb-2">
                  <Award className="h-5 w-5 text-amber-500" />
                </div>
                <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">{dealsWon}</p>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">Deals Won</p>
              </div>

              {/* Revenue */}
              <div className="bg-zinc-50 dark:bg-zinc-800/50 rounded-lg p-4 text-center">
                <div className="flex items-center justify-center mb-2">
                  <DollarSign className="h-5 w-5 text-green-500" />
                </div>
                <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">{formatCurrency(revenue)}</p>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">Revenue</p>
              </div>

              {/* Conversion Rate */}
              <div className="bg-zinc-50 dark:bg-zinc-800/50 rounded-lg p-4 text-center">
                <div className="flex items-center justify-center mb-2">
                  <Target className="h-5 w-5 text-blue-500" />
                </div>
                <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">{conversionRate}%</p>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">Conversion</p>
              </div>

              {/* In Progress */}
              <div className="bg-zinc-50 dark:bg-zinc-800/50 rounded-lg p-4 text-center">
                <div className="flex items-center justify-center mb-2">
                  <Briefcase className="h-5 w-5 text-purple-500" />
                </div>
                <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">{dealsInProgress}</p>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">In Progress</p>
              </div>

              {/* Meetings */}
              <div className="bg-zinc-50 dark:bg-zinc-800/50 rounded-lg p-4 text-center">
                <div className="flex items-center justify-center mb-2">
                  <Calendar className="h-5 w-5 text-cyan-500" />
                </div>
                <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">{meetingsAchieved}</p>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">Meetings</p>
              </div>

              {/* Follow-ups */}
              <div className="bg-zinc-50 dark:bg-zinc-800/50 rounded-lg p-4 text-center">
                <div className="flex items-center justify-center mb-2">
                  <Users className="h-5 w-5 text-orange-500" />
                </div>
                <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">{followUps.open}</p>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">
                  Open Follow-ups{followUps.overdue > 0 && <span className="text-red-500 ml-1">({followUps.overdue} overdue)</span>}
                </p>
              </div>

              {/* Target Achievement Progress */}
              <div className="col-span-3 md:col-span-6 bg-zinc-50 dark:bg-zinc-800/50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Target Achievement</span>
                  <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100">{targetAchievement}%</span>
                </div>
                <Progress value={targetAchievement} className="h-2" />
              </div>

              {/* MOM Compliance (if applicable) */}
              {momCompliance > 0 && (
                <div className="col-span-3 md:col-span-6 bg-zinc-50 dark:bg-zinc-800/50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">MOM Compliance</span>
                    <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100">{momCompliance}%</span>
                  </div>
                  <Progress 
                    value={momCompliance} 
                    className="h-2"
                    style={{ '--progress-background': momCompliance >= 80 ? '#22c55e' : momCompliance >= 50 ? '#f59e0b' : '#ef4444' }}
                  />
                </div>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default ProfilePerformanceCard;
