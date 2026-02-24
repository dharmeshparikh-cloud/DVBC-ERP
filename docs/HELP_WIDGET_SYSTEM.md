# In-App Help Widget System

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          HELP WIDGET SYSTEM                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐      │
│  │   Help Widget    │    │   Admin Panel    │    │   Backend API    │      │
│  │   (Frontend)     │◄──►│   (Frontend)     │◄──►│   (FastAPI)      │      │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘      │
│           │                       │                       │                 │
│           │                       │                       │                 │
│           └───────────────────────┴───────────────────────┘                 │
│                                   │                                         │
│                                   ▼                                         │
│                        ┌──────────────────┐                                 │
│                        │    MongoDB       │                                 │
│                        │  - help_topics   │                                 │
│                        │  - help_categories│                                │
│                        │  - help_user_progress                              │
│                        └──────────────────┘                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Models

### Help Topic Schema
```javascript
{
  title: String,           // "How to Send Onboarding Invite"
  slug: String,            // "send-onboarding-invite"
  type: String,            // guide | troubleshoot | video | faq | whatsnew
  category: String,        // Category slug (e.g., "onboarding")
  routes: [String],        // Context routes ["/onboarding-hub", "/onboarding"]
  roles: [String],         // Role-based visibility (empty = all)
  introduction: String,    // Brief description
  steps: [{
    title: String,
    description: String,
    imageUrl: String,
    tip: String
  }],
  troubleshooting: [{
    problem: String,
    solution: String
  }],
  videoUrl: String,
  notes: String,
  relatedTopicIds: [String],
  keywords: [String],
  featureVersion: String,  // Version tagging (e.g., "2.5.0")
  isNew: Boolean,          // Mark as new feature
  newUntil: Date,          // Auto-expire "new" badge
  requiresOnboarding: Boolean,  // First-time user tour
  onboardingSteps: [{
    target: String,        // CSS selector for element
    title: String,
    description: String
  }],
  priority: Number,        // Higher = shown first
  isActive: Boolean,
  viewCount: Number,
  helpfulCount: Number,
  notHelpfulCount: Number,
  createdAt: Date,
  updatedAt: Date
}
```

### Help Category Schema
```javascript
{
  name: String,            // "Getting Started"
  slug: String,            // "getting-started"
  icon: String,            // Emoji or icon name
  description: String,
  order: Number,           // Sort order
  roles: [String],         // Role-based visibility
  isActive: Boolean
}
```

### User Progress Schema (for First-Time Detection)
```javascript
{
  userId: String,
  featureId: String,
  completedOnboarding: Boolean,
  firstAccessAt: Date,
  onboardingCompletedAt: Date,
  viewCount: Number
}
```

## API Endpoints

### Public Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/help/context?route=&role=` | Context-aware topics for current page |
| GET | `/api/help/categories?role=` | All categories visible to role |
| GET | `/api/help/categories/{id}/topics?role=` | Topics in a category |
| GET | `/api/help/search?q=&role=` | Search topics |
| GET | `/api/help/topics/{id}?role=` | Single topic details |
| POST | `/api/help/topics/{id}/view` | Track view |
| POST | `/api/help/topics/{id}/feedback` | Submit helpful/not helpful |
| GET | `/api/help/whats-new?role=` | Recently added features |

### Onboarding Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/help/onboarding/check/{featureId}?user_id=` | Check if onboarding needed |
| POST | `/api/help/onboarding/complete/{featureId}` | Mark onboarding complete |
| GET | `/api/help/onboarding/steps/{featureId}?role=` | Get onboarding steps |

### Admin Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/help/admin/topics` | List all topics (with filters) |
| POST | `/api/help/admin/topics` | Create topic |
| PUT | `/api/help/admin/topics/{id}` | Update topic |
| DELETE | `/api/help/admin/topics/{id}` | Soft delete topic |
| GET | `/api/help/admin/categories` | List categories |
| POST | `/api/help/admin/categories` | Create category |
| PUT | `/api/help/admin/categories/{id}` | Update category |
| GET | `/api/help/admin/analytics` | View analytics |
| POST | `/api/help/admin/seed` | Seed default content |

## Features

### 1. Context-Aware Help
- Automatically shows relevant topics based on current page/route
- Smart matching using route patterns
- Role-based filtering

### 2. Search Functionality
- Full-text search across titles, descriptions, keywords
- Instant results with debounced input
- Highlighted excerpts

### 3. "What's New" Notifications
- Topics marked with `isNew: true` appear in What's New section
- Auto-expiry with `newUntil` date
- Visual badge on new content

### 4. First-Time Feature Detection
- Tracks user's first access to features
- Triggers guided onboarding tour
- Persists completion status

### 5. Role-Based Visibility
- Topics can be restricted to specific roles
- Empty roles array = visible to all
- Admin always sees everything

### 6. Admin Interface
- Create/Edit/Delete topics without code deployment
- Manage categories
- View analytics (views, feedback)
- Identify topics needing improvement

### 7. Feedback System
- Helpful/Not Helpful buttons on each topic
- Analytics dashboard shows feedback
- Identifies content needing updates

### 8. Performance Optimizations
- Lazy loading of help content
- Local caching of bookmarks/recent
- Minimal API calls with context-aware fetching

## Integration Steps

### 1. Backend Already Integrated
- Router: `/app/backend/routers/help.py`
- Included in: `/app/backend/server.py`

### 2. Existing GuidanceSystem
The existing `GuidanceSystem.js` provides:
- Floating help button
- Help panel with tabs
- AI assistance
- Smart suggestions

### 3. Admin Page Route
- Component: `/app/frontend/src/pages/admin/HelpContentAdmin.js`
- Route: `/help-admin` (accessible to admin role only)

### 4. Seed Initial Content
```bash
curl -X POST https://your-app.com/api/help/admin/seed
```

## UX Recommendations

1. **Floating Button Position**: Bottom-right, always visible
2. **Panel Size**: 400px width, 600px height (resizable)
3. **Context Priority**: Show page-specific help first
4. **Search**: Instant search with 300ms debounce
5. **Bookmarks**: Allow users to save frequently used topics
6. **Recent**: Show last 10 viewed topics
7. **Feedback**: Ask "Was this helpful?" at topic end
8. **Loading States**: Show skeleton while fetching

## Deployment Workflow

### Adding New Help Content
1. Admin logs into `/help-admin`
2. Creates new topic with routes, roles, steps
3. Marks as `isNew: true` if it's a new feature
4. Sets `priority` for ordering
5. Content immediately available (no redeployment)

### Automatic Feature Activation
1. Deploy new feature code
2. Help topic with matching routes auto-activates
3. Users see "New" badge on relevant help
4. First-time users get guided onboarding

## Files Created

| File | Description |
|------|-------------|
| `/app/backend/routers/help.py` | Backend API for help content |
| `/app/frontend/src/components/help/HelpWidget.js` | Standalone help widget component |
| `/app/frontend/src/pages/admin/HelpContentAdmin.js` | Admin interface for managing content |

## Existing Integration

The application already has a `GuidanceSystem.js` component that provides:
- `FloatingHelpButton` - Orange help button (bottom-right)
- `HelpPanel` - Expandable panel with Smart Suggestions, AI, Workflows, Tips
- `WorkflowOverlay` - Step-by-step guided workflows

The new backend API adds:
- Database-driven content management
- Admin interface without code changes
- Analytics and feedback tracking
- First-time use detection
