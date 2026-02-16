import React, { useState, useEffect, useContext } from 'react';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter
} from '../components/ui/dialog';
import { toast } from 'sonner';
import {
  Users, Target, Star, TrendingUp, Calendar, Award,
  CheckCircle, Clock, BarChart3, ChevronRight, Edit, Eye
} from 'lucide-react';

const SalesTeamPerformance = () => {
  const { user } = useContext(AuthContext);
  const [team, setTeam] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedMember, setSelectedMember] = useState(null);
  const [showTargetModal, setShowTargetModal] = useState(false);
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [targetForm, setTargetForm] = useState({
    meeting_target: 0,
    conversion_target: 0,
    deal_value_target: 0
  });
  const [reviewForm, setReviewForm] = useState({
    meeting_quality_score: 3,
    conversion_rate_score: 3,
    response_time_score: 3,
    mom_quality_score: 3,
    target_achievement_score: 3,
    comments: ''
  });

  useEffect(() => {
    fetchTeam();
  }, []);

  const fetchTeam = async () => {
    try {
      const response = await fetch(`${API}/my-team`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (response.ok) {
        const data = await response.json();
        setTeam(data.members || []);
      }
    } catch (error) {
      console.error('Failed to fetch team:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSetTarget = async () => {
    const now = new Date();
    try {
      const response = await fetch(`${API}/sales-targets`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          user_id: selectedMember.id,
          month: now.getMonth() + 1,
          year: now.getFullYear(),
          ...targetForm
        })
      });
      
      if (response.ok) {
        toast.success('Target set successfully! Pending approval.');
        setShowTargetModal(false);
        fetchTeam();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to set target');
      }
    } catch (error) {
      toast.error('Failed to set target');
    }
  };

  const handleSubmitReview = async () => {
    const now = new Date();
    try {
      const response = await fetch(`${API}/performance-reviews`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          user_id: selectedMember.id,
          month: now.getMonth() + 1,
          year: now.getFullYear(),
          ...reviewForm
        })
      });
      
      if (response.ok) {
        toast.success('Review submitted successfully!');
        setShowReviewModal(false);
        fetchTeam();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to submit review');
      }
    } catch (error) {
      toast.error('Failed to submit review');
    }
  };

  const getScoreColor = (score) => {
    if (score >= 4) return 'text-green-600 bg-green-50';
    if (score >= 3) return 'text-yellow-600 bg-yellow-50';
    return 'text-red-600 bg-red-50';
  };

  const renderStarRating = (value, onChange) => {
    return (
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onClick={() => onChange(star)}
            className={`p-1 rounded transition-colors ${
              star <= value ? 'text-yellow-400' : 'text-zinc-300'
            }`}
          >
            <Star className="w-5 h-5 fill-current" />
          </button>
        ))}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500"></div>
      </div>
    );
  }

  if (team.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Team Performance</h1>
          <p className="text-sm text-zinc-500">Manage your team's targets and reviews</p>
        </div>
        <Card className="border-zinc-200">
          <CardContent className="py-12 text-center">
            <Users className="w-12 h-12 mx-auto text-zinc-300 mb-4" />
            <p className="text-zinc-500">No team members assigned to you yet.</p>
            <p className="text-sm text-zinc-400 mt-1">Contact HR to set up your reporting structure.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="team-performance-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Team Performance</h1>
          <p className="text-sm text-zinc-500">Manage your team's targets and reviews</p>
        </div>
        <Badge className="bg-orange-100 text-orange-700 text-sm px-3 py-1">
          {team.length} Team Members
        </Badge>
      </div>

      {/* Team Overview Cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="border-zinc-200">
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">Team Size</p>
                <p className="text-2xl font-bold text-zinc-900">{team.length}</p>
              </div>
              <Users className="w-8 h-8 text-orange-500 opacity-70" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-200">
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">Total Leads</p>
                <p className="text-2xl font-bold text-zinc-900">
                  {team.reduce((sum, m) => sum + (m.stats?.leads_count || 0), 0)}
                </p>
              </div>
              <Target className="w-8 h-8 text-blue-500 opacity-70" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-200">
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">Closures (This Month)</p>
                <p className="text-2xl font-bold text-zinc-900">
                  {team.reduce((sum, m) => sum + (m.stats?.closures_this_month || 0), 0)}
                </p>
              </div>
              <CheckCircle className="w-8 h-8 text-green-500 opacity-70" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-200">
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">Meetings (This Month)</p>
                <p className="text-2xl font-bold text-zinc-900">
                  {team.reduce((sum, m) => sum + (m.stats?.meetings_this_month || 0), 0)}
                </p>
              </div>
              <Calendar className="w-8 h-8 text-purple-500 opacity-70" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Team Members List */}
      <Card className="border-zinc-200">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Users className="w-4 h-4" />
            Team Members
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {team.map((member) => (
              <div 
                key={member.id}
                className="flex items-center justify-between p-4 bg-zinc-50 rounded-lg border border-zinc-100"
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center text-orange-700 font-semibold">
                    {member.full_name?.charAt(0) || 'U'}
                  </div>
                  <div>
                    <p className="font-medium text-zinc-900">{member.full_name}</p>
                    <p className="text-sm text-zinc-500">{member.email}</p>
                  </div>
                </div>

                {/* Stats */}
                <div className="flex items-center gap-6">
                  <div className="text-center">
                    <p className="text-lg font-semibold text-zinc-900">{member.stats?.leads_count || 0}</p>
                    <p className="text-xs text-zinc-500">Leads</p>
                  </div>
                  <div className="text-center">
                    <p className="text-lg font-semibold text-zinc-900">{member.stats?.meetings_this_month || 0}</p>
                    <p className="text-xs text-zinc-500">Meetings</p>
                  </div>
                  <div className="text-center">
                    <p className="text-lg font-semibold text-green-600">{member.stats?.closures_this_month || 0}</p>
                    <p className="text-xs text-zinc-500">Closures</p>
                  </div>

                  {/* Target Progress */}
                  {member.current_target && (
                    <div className="w-32">
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-zinc-500">Target</span>
                        <span className="text-zinc-700">
                          {member.stats?.meetings_this_month || 0}/{member.current_target.meeting_target}
                        </span>
                      </div>
                      <Progress 
                        value={member.current_target.meeting_target > 0 
                          ? (member.stats?.meetings_this_month / member.current_target.meeting_target * 100) 
                          : 0
                        } 
                        className="h-2"
                      />
                    </div>
                  )}

                  {/* Latest Review Score */}
                  {member.latest_review && (
                    <div className={`px-3 py-1 rounded-full text-sm font-medium ${getScoreColor(member.latest_review.overall_score)}`}>
                      {member.latest_review.overall_score?.toFixed(1)} / 5
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setSelectedMember(member);
                      setShowTargetModal(true);
                    }}
                    className="text-xs"
                  >
                    <Target className="w-3 h-3 mr-1" />
                    Set Target
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setSelectedMember(member);
                      setShowReviewModal(true);
                    }}
                    className="text-xs"
                  >
                    <Star className="w-3 h-3 mr-1" />
                    Review
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Set Target Modal */}
      <Dialog open={showTargetModal} onOpenChange={setShowTargetModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Set Monthly Target for {selectedMember?.full_name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Meeting Target</Label>
              <Input
                type="number"
                value={targetForm.meeting_target}
                onChange={(e) => setTargetForm({...targetForm, meeting_target: parseInt(e.target.value) || 0})}
                placeholder="Number of meetings"
              />
            </div>
            <div className="space-y-2">
              <Label>Conversion Target</Label>
              <Input
                type="number"
                value={targetForm.conversion_target}
                onChange={(e) => setTargetForm({...targetForm, conversion_target: parseInt(e.target.value) || 0})}
                placeholder="Number of closures"
              />
            </div>
            <div className="space-y-2">
              <Label>Deal Value Target (₹)</Label>
              <Input
                type="number"
                value={targetForm.deal_value_target}
                onChange={(e) => setTargetForm({...targetForm, deal_value_target: parseFloat(e.target.value) || 0})}
                placeholder="Total deal value"
              />
            </div>
            <p className="text-xs text-zinc-500">
              * Targets require Principal Consultant approval before activation.
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowTargetModal(false)}>Cancel</Button>
            <Button onClick={handleSetTarget} className="bg-orange-600 hover:bg-orange-700">
              Set Target
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Review Modal */}
      <Dialog open={showReviewModal} onOpenChange={setShowReviewModal}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Monthly Review for {selectedMember?.full_name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Meeting Quality</Label>
              {renderStarRating(reviewForm.meeting_quality_score, (v) => setReviewForm({...reviewForm, meeting_quality_score: v}))}
            </div>
            <div className="space-y-2">
              <Label>Conversion Rate</Label>
              {renderStarRating(reviewForm.conversion_rate_score, (v) => setReviewForm({...reviewForm, conversion_rate_score: v}))}
            </div>
            <div className="space-y-2">
              <Label>Response Time</Label>
              {renderStarRating(reviewForm.response_time_score, (v) => setReviewForm({...reviewForm, response_time_score: v}))}
            </div>
            <div className="space-y-2">
              <Label>MOM Quality & Timeliness</Label>
              {renderStarRating(reviewForm.mom_quality_score, (v) => setReviewForm({...reviewForm, mom_quality_score: v}))}
            </div>
            <div className="space-y-2">
              <Label>Target Achievement</Label>
              {renderStarRating(reviewForm.target_achievement_score, (v) => setReviewForm({...reviewForm, target_achievement_score: v}))}
            </div>
            <div className="space-y-2">
              <Label>Comments</Label>
              <Textarea
                value={reviewForm.comments}
                onChange={(e) => setReviewForm({...reviewForm, comments: e.target.value})}
                placeholder="Additional feedback..."
                rows={3}
              />
            </div>
            <p className="text-xs text-zinc-500">
              * Reviews are due on or before the 5th of each month.
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowReviewModal(false)}>Cancel</Button>
            <Button onClick={handleSubmitReview} className="bg-orange-600 hover:bg-orange-700">
              Submit Review
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SalesTeamPerformance;
