# Comments and Annotations System

## Overview

The comments and annotations system allows users to collaborate on analysis results by adding comments, replies, and visual annotations (highlights, notes, drawings).

## Features

### 1. Comment Thread
- **Nested Comments**: Support for threaded discussions with replies
- **Real-time Updates**: Comments appear instantly for all users
- **Edit & Delete**: Users can modify or remove their own comments
- **User Attribution**: Each comment shows author name and timestamp

### 2. Annotation Tool
- **Text Highlighting**: Select and highlight important text passages
- **Sticky Notes**: Add contextual notes at specific positions
- **Drawing**: Freehand drawing for visual markup
- **Color Coding**: Choose from multiple colors for organization
- **Position Tracking**: Annotations are anchored to specific content locations

## Backend API

### Comment Endpoints

#### Create Comment
```http
POST /api/comments
Content-Type: application/json

{
  "analysis_id": "ISSUE-123",
  "workspace_dir": "/path/to/workspace",
  "user_id": "user123",
  "user_name": "John Doe",
  "content": "This analysis is very thorough",
  "parent_id": null  // Optional, for replies
}
```

#### Get Comments
```http
GET /api/comments?analysis_id=ISSUE-123&workspace_dir=/path/to/workspace
```

Response:
```json
[
  {
    "id": "comment-1",
    "analysis_id": "ISSUE-123",
    "user_id": "user123",
    "user_name": "John Doe",
    "content": "This analysis is very thorough",
    "parent_id": null,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z",
    "replies": [
      {
        "id": "comment-2",
        "content": "I agree!",
        "user_name": "Jane Smith",
        ...
      }
    ]
  }
]
```

#### Update Comment
```http
PUT /api/comments/{comment_id}
Content-Type: application/json

{
  "content": "Updated comment text",
  "workspace_dir": "/path/to/workspace"
}
```

#### Delete Comment
```http
DELETE /api/comments/{comment_id}?workspace_dir=/path/to/workspace
```

### Annotation Endpoints

#### Add Annotation
```http
POST /api/comments/{comment_id}/annotations
Content-Type: application/json

{
  "type": "highlight",  // or "note", "drawing"
  "content": "Selected text or note content",
  "position": {
    "x": 100,
    "y": 200,
    "width": 300,
    "height": 50
  },
  "color": "#ffeb3b",
  "workspace_dir": "/path/to/workspace"
}
```

#### Get Annotations
```http
GET /api/annotations?analysis_id=ISSUE-123&workspace_dir=/path/to/workspace
```

Response:
```json
[
  {
    "id": "annotation-1",
    "type": "highlight",
    "content": "Important finding",
    "position": {"x": 100, "y": 200, "width": 300, "height": 50},
    "color": "#ffeb3b",
    "created_by": "user123",
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

## Frontend Components

### CommentThread Component

```tsx
import { CommentThread } from './CommentThread';

<CommentThread
  analysisId="ISSUE-123"
  workspaceDir="/path/to/workspace"
  userId="user123"
  userName="John Doe"
/>
```

**Props:**
- `analysisId`: The ID of the analysis being commented on
- `workspaceDir`: Current workspace directory
- `userId`: Current user's ID
- `userName`: Current user's display name

**Features:**
- Displays all comments in a threaded view
- Allows creating new top-level comments
- Supports replying to existing comments
- Edit and delete buttons for user's own comments
- Automatic timestamp formatting

### AnnotationTool Component

```tsx
import { AnnotationTool } from './AnnotationTool';

<AnnotationTool
  content={analysisContent}
  analysisId="ISSUE-123"
  workspaceDir="/path/to/workspace"
  userId="user123"
  userName="John Doe"
  onAnnotate={(annotation, comment) => {
    console.log('New annotation:', annotation);
  }}
/>
```

**Props:**
- `content`: The markdown content to annotate
- `analysisId`: The ID of the analysis
- `workspaceDir`: Current workspace directory
- `userId`: Current user's ID
- `userName`: Current user's display name
- `onAnnotate`: Callback when annotation is created

**Features:**
- Three annotation modes: Highlight, Note, Drawing
- Color picker for visual organization
- Position tracking for accurate placement
- Renders markdown content with ReactMarkdown
- Displays existing annotations as overlays

## Data Models

### Comment
```typescript
interface Comment {
  id: string;
  analysis_id: string;
  user_id: string;
  user_name: string;
  content: string;
  parent_id: string | null;
  created_at: string;
  updated_at: string;
  replies?: Comment[];
}
```

### Annotation
```typescript
interface Annotation {
  id: string;
  type: 'highlight' | 'note' | 'drawing';
  content: string;
  position: {
    x: number;
    y: number;
    width?: number;
    height?: number;
  };
  color: string;
  created_by: string;
  created_at: string;
}
```

## Usage Example

### In AnalysisResultsPage

```tsx
import { CommentThread } from './CommentThread';
import { AnnotationTool } from './AnnotationTool';

export function AnalysisResultsPage({ workspaceDir }: Props) {
  const [selectedIssue, setSelectedIssue] = useState<string | null>(null);
  const [analysisContent, setAnalysisContent] = useState<string>("");

  return (
    <div className="analysis-viewer">
      {selectedIssue && (
        <>
          <div className="analysis-content">
            <AnnotationTool
              content={analysisContent}
              analysisId={selectedIssue}
              workspaceDir={workspaceDir}
              userId="user123"
              userName="Current User"
              onAnnotate={(annotation, comment) => {
                console.log('Annotation created:', annotation);
              }}
            />
          </div>
          <CommentThread
            analysisId={selectedIssue}
            workspaceDir={workspaceDir}
            userId="user123"
            userName="Current User"
          />
        </>
      )}
    </div>
  );
}
```

## Styling

The system includes two CSS files:

### comment.css
- Comment thread layout and spacing
- Comment card styling with borders and shadows
- Reply indentation (20px per level)
- Form and button styles
- Hover and focus states

### annotation.css
- Annotation toolbar layout
- Tool button styles and active states
- Annotation overlay positioning
- Highlight, note, and drawing styles
- Color picker interface

## Storage

Comments and annotations are stored in JSON files within the workspace:
- Comments: `{workspace_dir}/.codex/comments/{analysis_id}.json`
- Annotations: `{workspace_dir}/.codex/annotations/{analysis_id}.json`

## Permissions

The comment and annotation system respects workspace permissions:
- **Read**: View comments and annotations
- **Write**: Create comments and annotations
- **Admin/Owner**: Delete any comment or annotation

## Future Enhancements

Potential improvements for future versions:
1. Real-time collaboration with WebSocket updates
2. Mention system (@username notifications)
3. Rich text formatting in comments
4. Annotation search and filtering
5. Export comments to PDF/Word
6. Annotation version history
7. Collaborative drawing tools
8. Comment reactions (like, upvote)
9. Email notifications for new comments
10. Integration with issue tracking systems
