import express from 'express';
import cors from 'cors';

const JIRA_PORT = 8797;
const CONFLUENCE_PORT = 8798;

// Mock Jira Server
const jiraApp = express();
jiraApp.use(cors());
jiraApp.use(express.json());

// Mock Jira API endpoints
jiraApp.get('/rest/api/3/myself', (req, res) => {
  res.json({
    accountId: 'mock-account-id',
    emailAddress: 'test@example.com',
    displayName: 'Test User'
  });
});

jiraApp.get('/rest/api/3/search', (req, res) => {
  const jql = req.query.jql || '';
  res.json({
    issues: [
      {
        id: '10001',
        key: 'TEST-1',
        fields: {
          summary: 'Mock Jira Issue 1',
          description: 'This is a mock Jira issue for testing',
          status: { name: 'In Progress' },
          priority: { name: 'High' },
          created: '2024-01-01T00:00:00.000Z',
          updated: '2024-01-02T00:00:00.000Z'
        }
      },
      {
        id: '10002',
        key: 'TEST-2',
        fields: {
          summary: 'Mock Jira Issue 2',
          description: 'Another mock Jira issue',
          status: { name: 'To Do' },
          priority: { name: 'Medium' },
          created: '2024-01-03T00:00:00.000Z',
          updated: '2024-01-04T00:00:00.000Z'
        }
      }
    ],
    total: 2,
    maxResults: 50,
    startAt: 0
  });
});

jiraApp.get('/rest/api/3/project', (req, res) => {
  res.json([
    {
      id: '10000',
      key: 'TEST',
      name: 'Test Project'
    }
  ]);
});

// Mock Confluence Server
const confluenceApp = express();
confluenceApp.use(cors());
confluenceApp.use(express.json());

// Mock Confluence API endpoints
confluenceApp.get('/rest/api/user/current', (req, res) => {
  res.json({
    accountId: 'mock-account-id',
    email: 'test@example.com',
    displayName: 'Test User'
  });
});

confluenceApp.get('/rest/api/content', (req, res) => {
  const spaceKey = req.query.spaceKey || '';
  res.json({
    results: [
      {
        id: '123456',
        type: 'page',
        status: 'current',
        title: 'Mock Confluence Page 1',
        space: {
          key: spaceKey || 'TEST',
          name: 'Test Space'
        },
        body: {
          storage: {
            value: '<p>This is a mock Confluence page for testing</p>',
            representation: 'storage'
          }
        },
        version: {
          when: '2024-01-01T00:00:00.000Z',
          number: 1
        }
      },
      {
        id: '123457',
        type: 'page',
        status: 'current',
        title: 'Mock Confluence Page 2',
        space: {
          key: spaceKey || 'TEST',
          name: 'Test Space'
        },
        body: {
          storage: {
            value: '<p>Another mock Confluence page</p>',
            representation: 'storage'
          }
        },
        version: {
          when: '2024-01-02T00:00:00.000Z',
          number: 1
        }
      }
    ],
    size: 2,
    start: 0,
    limit: 25
  });
});

confluenceApp.get('/rest/api/space', (req, res) => {
  res.json({
    results: [
      {
        id: 98304,
        key: 'TEST',
        name: 'Test Space',
        type: 'global'
      }
    ],
    size: 1
  });
});

// Start servers
const startServers = () => {
  jiraApp.listen(JIRA_PORT, () => {
    console.log(`✓ Mock Jira server running on http://localhost:${JIRA_PORT}`);
  });

  confluenceApp.listen(CONFLUENCE_PORT, () => {
    console.log(`✓ Mock Confluence server running on http://localhost:${CONFLUENCE_PORT}`);
  });
};

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\nShutting down mock servers...');
  process.exit(0);
});

// Start servers immediately
startServers();

export { jiraApp, confluenceApp, startServers };
